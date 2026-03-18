"""Knowledge lifecycle manager — GC, scoring, tier promotion/demotion.

Runs a daily GC cycle at 02:00 local time:
  1. Score all warm entries (confidence × recency × evidence × usage)
  2. Update hot cache (evict stale, promote high-score)
  3. Demote low-score warm entries to cold tier (compressed files)
  4. Archive very old cold entries (summary only)
  5. Generate weekly/monthly summaries if due
  6. Report stats

The scoring algorithm from schemas/knowledge_lifecycle.yaml:
  score = (0.40 × confidence_score)
        × (0.25 × recency_factor)    [exp decay, half-life 30d]
        × (0.20 × evidence_score)    [normalized experiments supporting]
        × (0.15 × usage_factor)      [queries in last 7 days]
"""

import gzip
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import math
import yaml

from crew.knowledge.store import KnowledgeStore, KnowledgeEntry

logger = logging.getLogger(__name__)


# ============================================================================
# GC Report
# ============================================================================

@dataclass
class GCReport:
    """Results of one GC cycle."""
    date: str = ""
    entries_scored: int = 0
    hot_cache_updated: int = 0
    warm_to_cold: int = 0
    cold_to_archive: int = 0
    new_embeddings_generated: int = 0
    space_freed_mb: float = 0.0
    duration_seconds: float = 0.0
    errors: int = 0
    weekly_summary_generated: bool = False
    monthly_summary_generated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "entries_scored": self.entries_scored,
            "hot_cache_updated": self.hot_cache_updated,
            "warm_to_cold": self.warm_to_cold,
            "cold_to_archive": self.cold_to_archive,
            "new_embeddings_generated": self.new_embeddings_generated,
            "space_freed_mb": round(self.space_freed_mb, 1),
            "duration_seconds": round(self.duration_seconds, 1),
            "errors": self.errors,
            "weekly_summary": self.weekly_summary_generated,
            "monthly_summary": self.monthly_summary_generated,
        }


# ============================================================================
# LifecycleManager
# ============================================================================

class LifecycleManager:
    """Manages knowledge lifecycle: scoring, tier promotion/demotion, GC.

    Usage:
        mgr = LifecycleManager(store)
        mgr.start_gc_scheduler()   # Background thread, runs at 02:00 daily
        # or:
        report = mgr.run_gc_pass() # Manual trigger
    """

    # Scoring weights
    WEIGHT_CONFIDENCE = 0.40
    WEIGHT_RECENCY    = 0.25
    WEIGHT_EVIDENCE   = 0.20
    WEIGHT_USAGE      = 0.15

    # Confidence score mapping
    CONFIDENCE_SCORES = {
        "low":       0.25,
        "medium":    0.50,
        "high":      0.80,
        "very_high": 1.00,
    }

    # Demotion thresholds
    WARM_TO_COLD_THRESHOLD = 0.30       # Score below this → demote to cold
    COLD_AGE_DAYS = 180                 # Days before cold → archive
    ARCHIVE_AGE_DAYS = 365             # Days before archive purge

    def __init__(
        self,
        store: KnowledgeStore,
        cold_dir: Optional[Path] = None,
        archive_db: Optional[Path] = None,
        summaries_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize lifecycle manager.

        Args:
            store: Knowledge store to manage
            cold_dir: Directory for cold tier files
            archive_db: SQLite DB for archive index
            summaries_dir: Directory for weekly/monthly summaries
            config: Knowledge config section
        """
        self.store = store
        self.cold_dir = cold_dir or Path("data/knowledge/cold")
        self.archive_db_path = archive_db or Path("data/knowledge/archive.db")
        self.summaries_dir = summaries_dir or Path("data/summaries")
        self.config = config or {}
        self._gc_thread: Optional[threading.Thread] = None
        self._shutdown = False

        # Create directories
        self.cold_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        (self.summaries_dir / "weekly").mkdir(exist_ok=True)
        (self.summaries_dir / "monthly").mkdir(exist_ok=True)

        # Archive DB
        self._init_archive_db()

    # ========================================================================
    # GC Scheduler
    # ========================================================================

    def start_gc_scheduler(self, gc_hour: int = 2):
        """Start background thread that runs GC daily at gc_hour local time.

        Args:
            gc_hour: Local hour (0-23) to run GC (default: 02:00)
        """
        def _scheduler():
            logger.info(f"GC scheduler started, runs at {gc_hour:02d}:00 daily")
            last_gc_date = None

            while not self._shutdown:
                now = datetime.now()
                today = now.date()

                # Check if it's time for GC
                if now.hour == gc_hour and last_gc_date != today:
                    try:
                        logger.info("Starting scheduled GC cycle...")
                        report = self.run_gc_pass()
                        last_gc_date = today
                        logger.info(
                            f"GC complete: {report.entries_scored} scored, "
                            f"{report.warm_to_cold} demoted, "
                            f"{report.space_freed_mb}MB freed in {report.duration_seconds}s"
                        )
                    except Exception as e:
                        logger.error(f"GC cycle failed: {e}", exc_info=True)

                time.sleep(60)  # Check every minute

        self._gc_thread = threading.Thread(
            target=_scheduler,
            name="knowledge-gc",
            daemon=True,
        )
        self._gc_thread.start()

    def stop(self):
        """Stop the GC scheduler."""
        self._shutdown = True

    # ========================================================================
    # Full GC Pass
    # ========================================================================

    def run_gc_pass(self) -> GCReport:
        """Run a complete GC cycle.

        Steps:
          1. Score all warm entries
          2. Update hot cache
          3. Demote cold candidates (warm → cold)
          4. Archive old cold entries (cold → archive)
          5. Generate summaries if due
          6. Report stats

        Returns: GCReport with statistics
        """
        start = time.monotonic()
        report = GCReport(date=str(datetime.now().date()))
        space_before = self._get_cold_size_mb()

        try:
            # Step 1: Score all warm entries
            scored = self._score_all_warm_entries()
            report.entries_scored = len(scored)

            # Step 2: Update warm DB with new scores
            self._update_scores(scored)

            # Step 3: Demote warm → cold
            demoted = self._demote_warm_to_cold(scored)
            report.warm_to_cold = len(demoted)

            # Step 4: Archive old cold entries
            archived = self._archive_old_cold()
            report.cold_to_archive = len(archived)

            # Step 5: Summaries
            now = datetime.now()
            if now.weekday() == 6:  # Sunday
                self._generate_weekly_summary(scored)
                report.weekly_summary_generated = True

            if now.day == 1:  # First of month
                self._generate_monthly_summary()
                report.monthly_summary_generated = True

        except Exception as e:
            report.errors += 1
            logger.error(f"GC error: {e}", exc_info=True)

        # Calculate space freed
        space_after = self._get_cold_size_mb()
        report.space_freed_mb = max(0, space_before - space_after)
        report.duration_seconds = time.monotonic() - start

        # Save report
        self._save_gc_report(report)

        return report

    # ========================================================================
    # Scoring
    # ========================================================================

    def score_entry(self, entry: KnowledgeEntry) -> float:
        """Calculate score for a single entry.

        Score = confidence_weight × confidence_score
              × recency_weight × recency_factor
              × evidence_weight × evidence_score
              × usage_weight × usage_factor

        Returns: Float 0.0-1.0
        """
        # Confidence component
        conf_score = self.CONFIDENCE_SCORES.get(entry.confidence, 0.25)
        confidence_component = self.WEIGHT_CONFIDENCE * conf_score

        # Recency component: exp(-age_days / 30)
        if entry.created_at:
            try:
                created = datetime.fromisoformat(
                    entry.created_at.replace("Z", "+00:00")
                )
                age_days = (datetime.now(timezone.utc) - created).days
                recency = math.exp(-age_days / 30.0)
            except Exception:
                recency = 0.5
        else:
            recency = 0.5
        recency_component = self.WEIGHT_RECENCY * recency

        # Evidence component: min(experiments / 20, 1.0)
        experiments = 0
        if entry.evidence:
            experiments = entry.evidence.get("experiments_supporting", 0)
        evidence = min(experiments / 20.0, 1.0)
        evidence_component = self.WEIGHT_EVIDENCE * evidence

        # Usage component: min(queries_7d / 10, 1.0)
        queries = entry.queries_last_7d or 0
        usage = min(queries / 10.0, 1.0)
        usage_component = self.WEIGHT_USAGE * usage

        total = confidence_component + recency_component + evidence_component + usage_component
        return min(1.0, max(0.0, total))

    def _score_all_warm_entries(self) -> List[Tuple[KnowledgeEntry, float]]:
        """Score all warm-tier entries. Returns list of (entry, score)."""
        with sqlite3.connect(str(self.store.db_path), timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge WHERE tier IN ('hot', 'warm') AND status = 'active'"
            ).fetchall()

        scored = []
        for row in rows:
            try:
                entry = self.store._row_to_entry(row)
                score = self.score_entry(entry)
                scored.append((entry, score))
            except Exception as e:
                logger.debug(f"Could not score entry {row['id']}: {e}")

        return scored

    def _update_scores(self, scored: List[Tuple[KnowledgeEntry, float]]):
        """Write updated scores back to warm DB."""
        with sqlite3.connect(str(self.store.db_path), timeout=10) as conn:
            conn.executemany(
                "UPDATE knowledge SET score=? WHERE id=?",
                [(score, entry.id) for entry, score in scored],
            )

    # ========================================================================
    # Tier Demotion
    # ========================================================================

    def _demote_warm_to_cold(
        self, scored: List[Tuple[KnowledgeEntry, float]]
    ) -> List[KnowledgeEntry]:
        """Move low-score warm entries to cold tier.

        Criteria: score < WARM_TO_COLD_THRESHOLD OR age > 30 days
        """
        now = datetime.now(timezone.utc)
        demoted = []

        for entry, score in scored:
            # Check age
            try:
                created = datetime.fromisoformat(
                    entry.created_at.replace("Z", "+00:00")
                )
                age_days = (now - created).days
            except Exception:
                age_days = 0

            should_demote = (
                score < self.WARM_TO_COLD_THRESHOLD
                or age_days > 30
            )

            if should_demote:
                try:
                    self._write_cold_file(entry)
                    # Mark as cold in warm DB
                    self.store.update(entry.id, tier="cold")
                    demoted.append(entry)
                except Exception as e:
                    logger.debug(f"Could not demote entry {entry.id}: {e}")

        return demoted

    def _write_cold_file(self, entry: KnowledgeEntry):
        """Write entry to cold tier as compressed JSON."""
        try:
            created = datetime.fromisoformat(
                entry.created_at.replace("Z", "+00:00")
            )
            year_month = created.strftime("%Y/%m")
        except Exception:
            year_month = datetime.now().strftime("%Y/%m")

        cold_path = self.cold_dir / year_month
        cold_path.mkdir(parents=True, exist_ok=True)
        file_path = cold_path / f"{entry.id}.json.gz"

        with gzip.open(file_path, "wt") as f:
            json.dump(entry.to_dict(), f)

    # ========================================================================
    # Archiving
    # ========================================================================

    def _archive_old_cold(self) -> List[int]:
        """Archive cold entries older than COLD_AGE_DAYS.

        Writes summary to archive DB, optionally deletes cold file.
        """
        cutoff = datetime.now() - timedelta(days=self.COLD_AGE_DAYS)
        archived_ids = []

        for gz_file in self.cold_dir.rglob("*.json.gz"):
            # Parse year/month from path
            try:
                with gzip.open(gz_file, "rt") as f:
                    entry_data = json.load(f)

                created_str = entry_data.get("created_at", "")
                if created_str:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    if created.replace(tzinfo=None) > cutoff:
                        continue  # Not old enough

                # Write archive summary
                entry_id = entry_data.get("id")
                if entry_id:
                    summary = self._build_archive_summary(entry_data)
                    self._write_archive_entry(entry_id, summary, entry_data)
                    archived_ids.append(entry_id)

                    # Delete cold file (data is summarized)
                    gz_file.unlink(missing_ok=True)

            except Exception as e:
                logger.debug(f"Could not archive {gz_file}: {e}")

        return archived_ids

    def _build_archive_summary(self, entry_data: Dict) -> str:
        """Build 100-char summary of an entry for archive index."""
        category = entry_data.get("category", "?")
        insight = entry_data.get("insight", "")[:50]
        confidence = entry_data.get("confidence", "?")
        evidence = entry_data.get("evidence", {})
        experiments = evidence.get("experiments_supporting", 0) if evidence else 0

        return f"{category}: {insight}... [conf={confidence}, exps={experiments}]"[:100]

    def _write_archive_entry(
        self, entry_id: int, summary: str, full_data: Dict
    ):
        """Write an entry to the archive SQLite index."""
        with sqlite3.connect(str(self.archive_db_path), timeout=10) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO archive
                   (entry_id, summary, category, created_at, archived_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entry_id,
                    summary,
                    full_data.get("category", ""),
                    full_data.get("created_at", ""),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    # ========================================================================
    # Summaries
    # ========================================================================

    def _generate_weekly_summary(self, scored: List[Tuple[KnowledgeEntry, float]]):
        """Generate weekly knowledge summary."""
        now = datetime.now()
        week = now.isocalendar()[1]
        year = now.year

        # Find top insights from this week
        top_entries = sorted(scored, key=lambda x: x[1], reverse=True)[:5]

        lines = [
            f"# Weekly Knowledge Summary: {year}-W{week:02d}",
            f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"## Stats",
            f"- Entries scored: {len(scored)}",
            "",
            "## Top Insights This Week",
        ]

        for entry, score in top_entries:
            lines.append(f"\n**{entry.category}** (score={score:.2f}, conf={entry.confidence})")
            lines.append(f"> {entry.insight[:200]}")
            if entry.conditions:
                lines.append(f"*Conditions: {entry.conditions}*")

        content = "\n".join(lines)
        summary_path = self.summaries_dir / "weekly" / f"{year}-W{week:02d}.md"
        summary_path.write_text(content)
        logger.info(f"Weekly summary written to {summary_path}")

    def _generate_monthly_summary(self):
        """Generate monthly knowledge summary."""
        now = datetime.now()
        year_month = now.strftime("%Y-%m")

        # Count entries from warm store
        with sqlite3.connect(str(self.store.db_path), timeout=10) as conn:
            total = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            by_cat = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT category, COUNT(*) FROM knowledge GROUP BY category"
                ).fetchall()
            }
            by_conf = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT confidence, COUNT(*) FROM knowledge GROUP BY confidence"
                ).fetchall()
            }

        lines = [
            f"# Monthly Knowledge Summary: {year_month}",
            f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"## Total Entries: {total}",
            "",
            "## By Category",
        ]
        for cat, count in sorted(by_cat.items()):
            lines.append(f"- {cat}: {count}")

        lines.append("")
        lines.append("## By Confidence")
        for conf, count in sorted(by_conf.items()):
            lines.append(f"- {conf}: {count}")

        content = "\n".join(lines)
        summary_path = self.summaries_dir / "monthly" / f"{year_month}.md"
        summary_path.write_text(content)
        logger.info(f"Monthly summary written to {summary_path}")

    # ========================================================================
    # Helpers
    # ========================================================================

    def _init_archive_db(self):
        """Initialize archive SQLite schema."""
        with sqlite3.connect(str(self.archive_db_path), timeout=10) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archive (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id    INTEGER UNIQUE NOT NULL,
                    summary     TEXT NOT NULL,
                    category    TEXT,
                    created_at  TEXT,
                    archived_at TEXT NOT NULL
                )
            """)

    def _get_cold_size_mb(self) -> float:
        """Total size of cold storage in MB."""
        try:
            return sum(
                f.stat().st_size for f in self.cold_dir.rglob("*.json.gz")
            ) / (1024 * 1024)
        except Exception:
            return 0.0

    def _save_gc_report(self, report: GCReport):
        """Save GC report to disk."""
        reports_dir = Path("data/knowledge/gc_reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{report.date}.yaml"
        try:
            report_path.write_text(yaml.dump(report.to_dict(), default_flow_style=False))
        except Exception as e:
            logger.debug(f"Could not save GC report: {e}")
