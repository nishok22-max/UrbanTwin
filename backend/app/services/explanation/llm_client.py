"""LLM client — optional stretch feature. Owner: R5

If LLM_API_KEY is not set, this module is never called.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


def narrate(rec: "Recommendation") -> str:
    """Call an LLM to narrate the recommendation (stretch / not on critical path)."""
    raise NotImplementedError("LLM narration not configured — use template explanation.")
