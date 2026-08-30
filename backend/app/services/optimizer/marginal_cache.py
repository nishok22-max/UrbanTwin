"""MarginalCache — precomputes and caches per-intervention marginal consequences.

In M2, this provides the cache data structure and precomputation interface
so that individual intervention impacts are simulated once and reused.
In M3, the Optimizer Service queries this cache to run fast knapsack/ILP searches.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from app.models.consequence import SimulationRequest, SimulationResult
from app.services.consequence.engine import get_engine
from app.services import graph_service

logger = logging.getLogger(__name__)


class MarginalCache:
    """In-memory cache of single-intervention simulation results."""

    def __init__(self):
        # Key: (intervention_id, rainfall_mm) -> SimulationResult
        self._cache: dict[tuple[str, float], SimulationResult] = {}
        self._baseline_cache: dict[float, SimulationResult] = {}

    def get_baseline(self, rainfall_mm: float = 160.0) -> SimulationResult:
        """Get or compute baseline (null) simulation result."""
        if rainfall_mm in self._baseline_cache:
            return self._baseline_cache[rainfall_mm]

        engine = get_engine()
        req = SimulationRequest(
            scenario_id=f"null_base_{rainfall_mm}",
            intervention_ids=[],
            rainfall_mm=rainfall_mm,
            max_cascade_hops=3,
            monte_carlo_runs=30,
        )
        res = engine.simulate(req)
        self._baseline_cache[rainfall_mm] = res
        return res

    def get_marginal(self, intervention_id: str, rainfall_mm: float = 160.0) -> SimulationResult:
        """Get or compute simulation result for a single intervention."""
        key = (intervention_id, rainfall_mm)
        if key in self._cache:
            return self._cache[key]

        engine = get_engine()
        req = SimulationRequest(
            scenario_id=f"marginal_{intervention_id}_{rainfall_mm}",
            intervention_ids=[intervention_id],
            rainfall_mm=rainfall_mm,
            max_cascade_hops=3,
            monte_carlo_runs=30,
        )
        res = engine.simulate(req)
        self._cache[key] = res
        return res

    def precompute_all(self, rainfall_mm: float = 160.0) -> int:
        """Precompute marginal impacts for all interventions in catalog."""
        catalog = graph_service.get_intervention_catalog()
        t0 = time.perf_counter()
        logger.info("Precomputing marginal impacts for %d interventions at %.0fmm rain...", len(catalog), rainfall_mm)

        self.get_baseline(rainfall_mm)
        for item in catalog:
            self.get_marginal(item["id"], rainfall_mm)

        elapsed = time.perf_counter() - t0
        logger.info("Marginal precompute done in %.2fs (cached %d items)", elapsed, len(self._cache))
        return len(self._cache)

    def clear(self):
        self._cache.clear()
        self._baseline_cache.clear()


# Module-level singleton
_cache_instance: Optional[MarginalCache] = None


def get_marginal_cache() -> MarginalCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MarginalCache()
    return _cache_instance
