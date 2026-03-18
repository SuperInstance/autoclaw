"""Researcher agent — gathers knowledge from external sources.

The researcher is the crew's eyes on the outside world. It:
  1. Takes research requests from the message bus (task_request messages)
  2. Searches the web (DuckDuckGo by default, no API key needed)
  3. Calls LLM APIs to extract structured insights from raw text
  4. Publishes results and knowledge entries back to the bus

The researcher works independently but can be guided with:
  - Specific URLs to read (source_urls in payload)
  - Depth of research (max_depth: 1=surface, 3=deep)
  - Target format (raw | structured | training_data | knowledge_entry)

Fallback chain:
  1. DuckDuckGo search (free, no API key)
  2. SerpAPI (needs SERPAPI_KEY env var)
  3. RSS feeds (always available if URL known)
  4. Direct URL fetch (just reads the page)
  5. Pure LLM reasoning (no search at all, last resort)
"""

import re
import json
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, List, Dict, Any

from crew.agents.base import BaseAgent
from crew.messaging.bus import Message

logger = logging.getLogger(__name__)

# Max characters to extract from a web page
MAX_PAGE_CHARS = 8000
# Max results per search query
MAX_SEARCH_RESULTS = 5


class ResearcherAgent(BaseAgent):
    """Agent that gathers knowledge from web and LLM APIs.

    Accepts task_request messages and publishes:
      - result message with findings
      - knowledge messages for high-confidence insights
    """

    ROLE = "researcher"
    DEFAULT_PRIORITY = 5

    def get_capabilities(self) -> List[str]:
        return ["web_search", "rss_fetch", "llm_query", "paper_fetch"]

    def process_message(self, message: Message) -> Optional[Message]:
        """Process a research request.

        Expected payload:
          description: str  (what to research)
          topic: str        (primary search query)
          context: str      (optional background)
          source_urls: list (optional starting URLs)
          max_depth: int    (1-3, default 1)
          target_format: str (raw|structured|knowledge_entry|training_data)
        """
        if message.type != "task_request":
            return None

        payload = message.payload
        topic = payload.get("topic", payload.get("description", ""))
        context = payload.get("context", "")
        source_urls = payload.get("source_urls", [])
        target_format = payload.get("target_format", "structured")

        self.logger.info(f"Researching: {topic}")

        # 1. Gather raw content
        raw_content = []

        if source_urls:
            for url in source_urls[:3]:
                text = self._fetch_url(url)
                if text:
                    raw_content.append({"url": url, "text": text})

        if not raw_content:
            # Try web search
            results = self._search_web(topic)
            for r in results:
                if r.get("url"):
                    text = self._fetch_url(r["url"])
                    raw_content.append({
                        "url": r["url"],
                        "title": r.get("title", ""),
                        "text": text or r.get("snippet", ""),
                    })

        if not raw_content:
            raw_content.append({
                "url": None,
                "text": f"No web results found for: {topic}",
            })

        # 2. Synthesize with LLM (or fallback)
        findings = self._synthesize(topic, context, raw_content, target_format)

        # 3. Create knowledge entries from high-confidence findings
        if findings.get("insights"):
            for insight in findings["insights"][:3]:  # Max 3 per research session
                if insight.get("confidence") in ("high", "very_high"):
                    self.submit_knowledge(
                        insight=insight["text"],
                        category=insight.get("category", "external"),
                        tags=insight.get("tags", [topic.replace(" ", "-")]),
                        confidence=insight.get("confidence", "medium"),
                        conditions=insight.get("conditions"),
                        evidence={"source": "researcher_agent", "topic": topic},
                    )

        # 4. Publish result back
        return Message(
            from_agent=self.agent_id,
            to_agent=message.from_agent,
            type="result",
            priority=message.priority,
            payload={
                "description": f"Research complete: {topic}",
                "summary": findings.get("summary", "Research complete"),
                "content": findings,
                "sources": [r.get("url") for r in raw_content if r.get("url")],
                "confidence": findings.get("overall_confidence", "medium"),
                "topic": topic,
            },
            tags=message.tags,
        )

    def idle_work(self):
        """When idle, scan configured RSS feeds for new content."""
        import time
        # Check for RSS trigger tasks from the bus before sleeping
        time.sleep(10)

    # ========================================================================
    # Web Search
    # ========================================================================

    def _search_web(self, query: str) -> List[Dict[str, str]]:
        """Search the web. Tries DuckDuckGo first, then SerpAPI.

        Args:
            query: Search query

        Returns: List of {title, url, snippet} dicts
        """
        if not self.check_rate_limit("web_search"):
            return []

        # Try DuckDuckGo (no API key, uses their HTML)
        results = self._search_duckduckgo(query)
        if results:
            self.consume_rate("web_search")
            return results

        # Fallback: try SerpAPI if key available
        import os
        serpapi_key = os.environ.get("SERPAPI_KEY")
        if serpapi_key:
            results = self._search_serpapi(query, serpapi_key)
            if results:
                self.consume_rate("web_search")
                return results

        return []

    def _search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        """Search using DuckDuckGo's instant answers API (no key needed)."""
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "AutoCrew/1.0 (autonomous research)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            results = []

            # Related topics
            for topic in data.get("RelatedTopics", [])[:MAX_SEARCH_RESULTS]:
                if isinstance(topic, dict) and topic.get("FirstURL"):
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "url": topic["FirstURL"],
                        "snippet": topic.get("Text", "")[:300],
                    })

            # Abstract result
            if data.get("AbstractURL"):
                results.insert(0, {
                    "title": data.get("Heading", ""),
                    "url": data["AbstractURL"],
                    "snippet": data.get("AbstractText", "")[:300],
                })

            return results[:MAX_SEARCH_RESULTS]

        except Exception as e:
            self.logger.debug(f"DuckDuckGo search failed: {e}")
            return []

    def _search_serpapi(self, query: str, api_key: str) -> List[Dict[str, str]]:
        """Search using SerpAPI (requires API key)."""
        try:
            params = urllib.parse.urlencode({
                "q": query,
                "api_key": api_key,
                "num": MAX_SEARCH_RESULTS,
            })
            url = f"https://serpapi.com/search.json?{params}"

            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            results = []
            for item in data.get("organic_results", [])[:MAX_SEARCH_RESULTS]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            return results

        except Exception as e:
            self.logger.debug(f"SerpAPI search failed: {e}")
            return []

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch a URL and extract readable text.

        Args:
            url: URL to fetch

        Returns: Extracted text, or None on error
        """
        if not url or not url.startswith(("http://", "https://")):
            return None

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "AutoCrew/1.0 (autonomous research agent)",
                    "Accept": "text/html,text/plain",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read(MAX_PAGE_CHARS * 2)  # Read a bit more for decoding

            # Decode
            text = content.decode("utf-8", errors="replace")

            # Strip HTML tags
            text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"&[a-z]+;", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            return text[:MAX_PAGE_CHARS]

        except Exception as e:
            self.logger.debug(f"Failed to fetch {url}: {e}")
            return None

    # ========================================================================
    # LLM Synthesis
    # ========================================================================

    def _synthesize(
        self,
        topic: str,
        context: str,
        raw_content: List[Dict],
        target_format: str,
    ) -> Dict[str, Any]:
        """Use LLM to synthesize raw content into structured findings.

        Falls back to basic extraction if LLM unavailable.
        """
        # Build source text
        source_text = "\n\n---\n\n".join(
            f"Source: {r.get('url', 'unknown')}\n{r.get('text', '')[:2000]}"
            for r in raw_content[:3]
        )

        if not source_text.strip():
            return {"summary": f"No content found for: {topic}", "insights": []}

        # Try LLM synthesis
        if self.check_rate_limit("llm_call"):
            llm_result = self._call_llm_synthesis(topic, context, source_text, target_format)
            if llm_result:
                self.consume_rate("llm_call")
                return llm_result

        # Fallback: basic extraction
        return self._basic_extraction(topic, source_text)

    def _call_llm_synthesis(
        self,
        topic: str,
        context: str,
        source_text: str,
        target_format: str,
    ) -> Optional[Dict[str, Any]]:
        """Call LLM to synthesize findings. Returns None if unavailable."""
        import os

        # Build prompt based on target format
        if target_format == "knowledge_entry":
            prompt = f"""You are a research assistant. Extract key insights from these sources about: {topic}

Context: {context or 'General research'}

Sources:
{source_text[:3000]}

Return JSON with this structure:
{{
  "summary": "2-3 sentence summary",
  "overall_confidence": "low|medium|high|very_high",
  "insights": [
    {{
      "text": "Specific, actionable insight",
      "category": "hyperparameter|architecture|training_dynamics|data|infrastructure|methodology|external",
      "tags": ["tag1", "tag2"],
      "confidence": "low|medium|high|very_high",
      "conditions": "When this applies (or null)"
    }}
  ]
}}"""
        else:
            prompt = f"""Research topic: {topic}
Context: {context or 'No additional context'}

Sources:
{source_text[:3000]}

Summarize the key findings in 3-5 bullet points. Be concise and factual.
Return JSON: {{"summary": "...", "bullets": ["...", "..."], "insights": [], "overall_confidence": "medium"}}"""

        # Try Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY") or self.config.get("llm", {}).get("api_key")
        if anthropic_key:
            try:
                import urllib.request as req
                data = json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode()

                request = req.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=data,
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                )
                with req.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode())
                    text = result["content"][0]["text"]

                    # Extract JSON from response
                    json_match = re.search(r"\{.*\}", text, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())

            except Exception as e:
                self.logger.debug(f"Anthropic synthesis failed: {e}")

        # Try OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            try:
                data = json.dumps({
                    "model": "gpt-4o-mini",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                }).encode()

                request = req.Request(
                    "https://api.openai.com/v1/chat/completions",
                    data=data,
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "content-type": "application/json",
                    },
                )
                with req.urlopen(request, timeout=30) as response:
                    result = json.loads(response.read().decode())
                    text = result["choices"][0]["message"]["content"]
                    return json.loads(text)

            except Exception as e:
                self.logger.debug(f"OpenAI synthesis failed: {e}")

        return None

    def _basic_extraction(self, topic: str, source_text: str) -> Dict[str, Any]:
        """Extract key sentences without LLM. Simple but works offline."""
        sentences = re.split(r"[.!?]+", source_text)
        topic_words = set(topic.lower().split())

        # Score sentences by relevance to topic
        scored = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 30:
                continue
            score = sum(1 for w in topic_words if w in sent.lower())
            if score > 0:
                scored.append((score, sent))

        scored.sort(reverse=True)
        top_sentences = [s[1] for s in scored[:5]]

        summary = " ".join(top_sentences[:2]) if top_sentences else f"Research on {topic} completed."

        return {
            "summary": summary[:500],
            "insights": [],
            "overall_confidence": "low",
            "note": "LLM unavailable, basic extraction used",
        }
