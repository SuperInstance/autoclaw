"""Knowledge subsystem for the crew.

Provides persistent learning and memory for the autonomous research system.
"""

from crew.knowledge.store import KnowledgeStore, KnowledgeEntry, ConfidenceLevel, KnowledgeStatus

# Singleton instance
_store = None

def get_knowledge_store() -> KnowledgeStore:
    """Get or create the global knowledge store."""
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store

__all__ = ['KnowledgeStore', 'KnowledgeEntry', 'ConfidenceLevel', 'KnowledgeStatus', 'get_knowledge_store']
