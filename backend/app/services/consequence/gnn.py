"""GNN refiner stub — PyTorch Geometric edge-weight refiner (stretch goal).

In M2 this is a pass-through: it returns the physics weights unchanged.
The interface is defined so the engine can call it without modification later.
"""
from __future__ import annotations

import logging

import networkx as nx

logger = logging.getLogger(__name__)


class GNNRefiner:
    """Stub GNN refiner. Currently a no-op; will refine edge weights in M3/M4."""

    available: bool = False

    def refine_edge_weights(self, G: nx.MultiDiGraph) -> nx.MultiDiGraph:
        """Return graph unchanged (physics weights stand alone for M2)."""
        logger.debug("GNNRefiner: physics-only mode (GNN not trained)")
        return G
