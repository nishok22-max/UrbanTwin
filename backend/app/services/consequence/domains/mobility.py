"""MobilityModule — traffic-flow model: flooded roads → travel-time increase.

Physics model (BPR-inspired):
  travel_time_affected = base_travel_time * BPR(flow, effective_capacity)

Where:
  - effective_capacity drops on flooded edges (flood_depth_m drives capacity reduction)
  - Blocked roads (depth > threshold) contribute infinite delay → rerouted / inaccessible
  - Intervention road_capacity_mult improves effective capacity

Coupling input: flood impacts from FloodModule passed via `flood_impacts` kwarg.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import networkx as nx
import numpy as np

from app.services.consequence.domains.base import DomainImpact, DomainModule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BPR (Bureau of Public Roads) function parameters
# ---------------------------------------------------------------------------
BPR_ALPHA = 0.15
BPR_BETA = 4.0

# Flood depth thresholds
DEPTH_CAPACITY_THRESHOLD = 0.10   # m: depth at which capacity starts dropping
DEPTH_BLOCKED_THRESHOLD = 0.30    # m: depth at which road is effectively blocked
BLOCKED_PENALTY_MIN = 25.0        # extra minutes for a blocked road segment


class MobilityModule(DomainModule):
    """Traffic-flow mobility model coupling with flood impacts."""

    name = "mobility"

    def compute_impact(
        self,
        G: nx.MultiDiGraph,
        intervention_ids: list[str],
        intervention_catalog: list[dict],
        rainfall_mm: float,
        rng_seed: int,
        flood_impacts: Optional[dict[int, DomainImpact]] = None,
    ) -> dict[int, DomainImpact]:

        np_rng = np.random.default_rng(rng_seed)
        flood_impacts = flood_impacts or {}

        # Build road_capacity_mult from interventions
        capacity_boost: dict[int, float] = {}
        for int_id in intervention_ids:
            item = next((x for x in intervention_catalog if x["id"] == int_id), None)
            if item is None:
                continue
            node_id = item["target_node"]
            mult = item["effect"].get("road_capacity_mult", 1.0)
            capacity_boost[node_id] = capacity_boost.get(node_id, 1.0) * mult

        # ---------------------------------------------------------------------------
        # Compute per-edge effective capacity + travel time delta
        # ---------------------------------------------------------------------------
        edge_delay: dict[tuple, float] = {}  # (u,v) -> extra delay minutes

        for u, v, key, edata in G.edges(keys=True, data=True):
            base_tt = edata.get("travel_time", 30.0) / 60.0  # convert sec → min
            base_cap = edata.get("capacity", 600.0)

            # Flood depth on this edge = average depth of endpoint nodes
            u_depth = flood_impacts.get(u, DomainImpact(node_id=u)).flood_depth_m
            v_depth = flood_impacts.get(v, DomainImpact(node_id=v)).flood_depth_m
            edge_depth = (u_depth + v_depth) / 2.0

            # Capacity reduction from flooding
            if edge_depth <= DEPTH_CAPACITY_THRESHOLD:
                cap_factor = 1.0
            elif edge_depth >= DEPTH_BLOCKED_THRESHOLD:
                cap_factor = 0.05  # near-zero capacity → road effectively blocked
            else:
                # Linear interpolation
                t = (edge_depth - DEPTH_CAPACITY_THRESHOLD) / (
                    DEPTH_BLOCKED_THRESHOLD - DEPTH_CAPACITY_THRESHOLD
                )
                cap_factor = 1.0 - 0.95 * t

            # Boost from road elevation/road_capacity interventions
            u_boost = capacity_boost.get(u, 1.0)
            v_boost = capacity_boost.get(v, 1.0)
            combined_boost = (u_boost + v_boost) / 2.0

            effective_cap = base_cap * cap_factor * combined_boost

            # Assumed flow: proportional to population density in area
            # Use a heuristic: average population served by endpoints
            u_pop = G.nodes[u].get("population_served", 0.0) if u in G.nodes else 0.0
            v_pop = G.nodes[v].get("population_served", 0.0) if v in G.nodes else 0.0
            flow_demand = ((u_pop + v_pop) / 2.0) * 0.05  # 5% of residents travel at peak

            # BPR function: TT = TT_0 * (1 + alpha * (flow/cap)^beta)
            v_c_ratio = min(flow_demand / max(effective_cap, 1.0), 3.0)
            bpr_factor = 1.0 + BPR_ALPHA * (v_c_ratio ** BPR_BETA)

            if edge_depth >= DEPTH_BLOCKED_THRESHOLD:
                extra_delay = BLOCKED_PENALTY_MIN + base_tt * (bpr_factor - 1.0)
            else:
                extra_delay = base_tt * (bpr_factor - 1.0)

            edge_delay[(u, v)] = extra_delay

        # ---------------------------------------------------------------------------
        # Aggregate to node-level: average delay of adjacent edges
        # ---------------------------------------------------------------------------
        impacts: dict[int, DomainImpact] = {}
        for node_id in G.nodes:
            adj_delays = []
            for u, v in G.out_edges(node_id):
                adj_delays.append(edge_delay.get((u, v), 0.0))
            for u, v in G.in_edges(node_id):
                adj_delays.append(edge_delay.get((u, v), 0.0))

            avg_delay = float(np.mean(adj_delays)) if adj_delays else 0.0
            passable = all(
                edge_delay.get((u, v), 0.0) < BLOCKED_PENALTY_MIN
                for u, v in list(G.out_edges(node_id)) + list(G.in_edges(node_id))
            )

            flood_imp = flood_impacts.get(node_id, DomainImpact(node_id=node_id))
            severity = min(avg_delay / 20.0, 1.0)  # 20 min extra = max severity

            impacts[node_id] = DomainImpact(
                node_id=node_id,
                flood_depth_m=flood_imp.flood_depth_m,
                flooded=flood_imp.flooded,
                travel_time_delta_min=avg_delay,
                road_passable=passable,
                population_at_risk=flood_imp.population_at_risk,
                severity=severity,
            )

        blocked_count = sum(1 for i in impacts.values() if not i.road_passable)
        logger.debug(
            "MobilityModule: %d/%d nodes with blocked roads", blocked_count, len(impacts)
        )
        return impacts
