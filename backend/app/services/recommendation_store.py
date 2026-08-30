"""Shared in-memory recommendation store.

Used by POST /optimize to persist results and by GET /recommendation/{id}
to retrieve them. Avoids circular imports between routers.
"""
from __future__ import annotations

from typing import Optional

from app.models.recommendation import Recommendation

# In-memory store: recommendation_id → Recommendation
_store: dict[str, Recommendation] = {}


def save(rec: Recommendation) -> None:
    """Persist a recommendation (replaces any existing entry with the same ID)."""
    _store[rec.id] = rec


def get(rec_id: str) -> Optional[Recommendation]:
    """Retrieve a recommendation by ID. Returns None if not found."""
    return _store.get(rec_id)


def list_all() -> list[Recommendation]:
    """Return all stored recommendations, newest first."""
    return list(reversed(list(_store.values())))


def clear() -> None:
    """Clear all stored recommendations (used in tests)."""
    _store.clear()
