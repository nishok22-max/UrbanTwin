"""DomainModule ABC — base interface every domain must implement."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import networkx as nx


@dataclass
class DomainImpact:
    """Per-node impact computed by one domain module."""
    node_id: int
    # Flood domain
    flood_depth_m: float = 0.0
    flooded: bool = False
    # Mobility domain
    travel_time_delta_min: float = 0.0      # positive = worse
    road_passable: bool = True
    # Population
    population_at_risk: float = 0.0
    # Generic scalar for coupling
    severity: float = 0.0                   # 0 (none) → 1 (severe)
    extra: dict[str, Any] = field(default_factory=dict)


class DomainModule(ABC):
    """Every domain (flood, mobility, …) must implement this interface."""

    name: str = "base"

    @abstractmethod
    def compute_impact(
        self,
        G: nx.MultiDiGraph,
        intervention_ids: list[str],
        intervention_catalog: list[dict],
        rainfall_mm: float,
        rng_seed: int,
    ) -> dict[int, DomainImpact]:
        """Compute per-node impact given the graph and active interventions.

        Args:
            G: In-memory infrastructure graph.
            intervention_ids: Active intervention IDs for this scenario.
            intervention_catalog: Full catalog for lookup.
            rainfall_mm: Rainfall intensity driver.
            rng_seed: Seed for reproducible randomness.

        Returns:
            Mapping node_id -> DomainImpact.
        """
        ...
