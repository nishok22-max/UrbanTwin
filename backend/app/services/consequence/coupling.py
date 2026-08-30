"""CouplingResolver — propagates domain impacts across dependency edges, bounded to max_hops.

Algorithm:
  1. Start from seed nodes (highest-severity flooded nodes).
  2. BFS up to max_hops hops through the directed graph.
  3. At each hop, attenuate severity by edge weight.
  4. Accumulate travel-time deltas for mobility coupling.
  5. Return ordered cascade path for visualisation.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from app.services.consequence.domains.base import DomainImpact

logger = logging.getLogger(__name__)

# Severity attenuation per hop (exponential decay)
HOP_ATTENUATION = 0.5
MIN_SEVERITY_TO_PROPAGATE = 0.05


@dataclass
class CascadeNode:
    node_id: int
    hop: int
    flood_depth_m: float
    travel_time_delta_min: float
    severity: float
    lat: float
    lon: float
    node_type: str


@dataclass
class CascadeResult:
    path: list[CascadeNode]
    total_severity: float
    max_hop: int
    affected_node_ids: set[int] = field(default_factory=set)


class CouplingResolver:
    """Propagates impact across edge dependencies using BFS with attenuation."""

    def __init__(self, max_hops: int = 3):
        self.max_hops = max_hops

    def propagate(
        self,
        G: nx.MultiDiGraph,
        flood_impacts: dict[int, DomainImpact],
        mobility_impacts: dict[int, DomainImpact],
        top_k_seeds: int = 10,
    ) -> CascadeResult:
        """
        Build cascade path starting from the most severely flooded nodes.

        Args:
            G: Infrastructure graph.
            flood_impacts: Per-node flood domain impacts.
            mobility_impacts: Per-node mobility domain impacts.
            top_k_seeds: How many seed nodes to start BFS from.

        Returns:
            CascadeResult with ordered cascade path.
        """
        # Rank nodes by severity and pick seeds
        ranked = sorted(
            flood_impacts.items(),
            key=lambda kv: kv[1].severity,
            reverse=True,
        )
        seed_ids = [nid for nid, imp in ranked[:top_k_seeds] if imp.severity > MIN_SEVERITY_TO_PROPAGATE]

        if not seed_ids:
            return CascadeResult(path=[], total_severity=0.0, max_hop=0)

        visited: dict[int, CascadeNode] = {}
        queue: deque[tuple[int, int, float]] = deque()  # (node_id, hop, severity)

        for seed in seed_ids:
            if seed in G.nodes:
                queue.append((seed, 0, flood_impacts[seed].severity))

        while queue:
            node_id, hop, severity = queue.popleft()

            if node_id in visited:
                continue
            if hop > self.max_hops:
                continue
            if severity < MIN_SEVERITY_TO_PROPAGATE:
                continue

            ndata = G.nodes.get(node_id, {})
            flood_imp = flood_impacts.get(node_id, DomainImpact(node_id=node_id))
            mob_imp = mobility_impacts.get(node_id, DomainImpact(node_id=node_id))

            visited[node_id] = CascadeNode(
                node_id=node_id,
                hop=hop,
                flood_depth_m=flood_imp.flood_depth_m,
                travel_time_delta_min=mob_imp.travel_time_delta_min,
                severity=severity,
                lat=ndata.get("lat", ndata.get("y", 0.0)),
                lon=ndata.get("lon", ndata.get("x", 0.0)),
                node_type=ndata.get("node_type", "road_junction"),
            )

            # Propagate to successors (directed downstream flow)
            for successor in G.successors(node_id):
                if successor not in visited:
                    edge_data = G.get_edge_data(node_id, successor, default={})
                    if isinstance(edge_data, dict) and 0 in edge_data:
                        edge_data = edge_data[0]
                    edge_weight = edge_data.get("weight", 1.0)
                    attenuated = severity * HOP_ATTENUATION * edge_weight
                    queue.append((successor, hop + 1, attenuated))

        # Sort path by hop then severity (for frontend animation)
        path = sorted(visited.values(), key=lambda cn: (cn.hop, -cn.severity))
        total_sev = sum(cn.severity for cn in path)

        logger.debug(
            "CouplingResolver: %d cascade nodes over %d hops",
            len(path),
            max((cn.hop for cn in path), default=0),
        )

        return CascadeResult(
            path=path,
            total_severity=total_sev,
            max_hop=max((cn.hop for cn in path), default=0),
            affected_node_ids={cn.node_id for cn in path},
        )
