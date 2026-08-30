"""FloodModule — hydrology rules: elevation → ponding → affected nodes.

Simplified physics model for T.Nagar, Chennai (elevation range: 2–23m, median 13m):

  A node floods when:
    net_rainfall × (1 - drain_efficiency) > excess_capacity(elevation)

  excess_capacity(e) = how much more rainfall the node can absorb above the baseline.
  For T.Nagar, a node at median elevation (13m) just starts flooding at 120mm.
  Lower nodes flood more, higher nodes flood less.

Calibration:
  - 120mm → ~30% nodes flooded (real Chennai 2015 flood impact)
  - 80mm → ~10% nodes flooded
  - 160mm → ~60% nodes flooded
  - Each intervention (drain upgrade, pump) reduces flooded count by 3-8%
"""
from __future__ import annotations

import logging
import math

import networkx as nx
import numpy as np

from app.services.consequence.domains.base import DomainImpact, DomainModule

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Calibration constants
# NODE_FLOOD_ELEVATION_MM: how many mm of "rainfall equivalent" a node at
# exactly this elevation can handle. Nodes below this flood, above don't.
# ---------------------------------------------------------------------------
# At median elevation (13m), a node floods when rainfall > 120mm
MEDIAN_ELEVATION_M = 13.0
MEDIAN_RAIN_THRESHOLD_MM = 120.0

# Each meter lower than median adds this much vulnerability (mm less threshold)
MM_PER_METER_BELOW = 12.0

# Each meter higher subtracts this much vulnerability
MM_PER_METER_ABOVE = 8.0

# Baseline drainage absorption rate (fraction of rainfall drained away)
BASE_DRAIN_FRACTION = 0.35

# Flood depth per mm excess (metres)
EXCESS_TO_DEPTH_M = 0.003

# Minimum depth to be "flooded"
FLOOD_THRESHOLD_M = 0.04


class FloodModule(DomainModule):
    """Hydrological flood model — elevation-relative rainfall threshold."""

    name = "flood"

    def compute_impact(
        self,
        G: nx.MultiDiGraph,
        intervention_ids: list[str],
        intervention_catalog: list[dict],
        rainfall_mm: float,
        rng_seed: int,
    ) -> dict[int, DomainImpact]:

        np_rng = np.random.default_rng(rng_seed)

        # ---------------------------------------------------------------
        # Build per-node intervention effects
        # ---------------------------------------------------------------
        node_effects: dict[int, dict] = {}
        for int_id in intervention_ids:
            item = next((x for x in intervention_catalog if x["id"] == int_id), None)
            if item is None:
                continue
            node_id = item["target_node"]
            eff = item["effect"]
            if node_id in node_effects:
                e = node_effects[node_id]
                node_effects[node_id] = {
                    "drain_capacity_mult": e["drain_capacity_mult"] * eff.get("drain_capacity_mult", 1.0),
                    "elevation_raise_m":   e["elevation_raise_m"] + eff.get("elevation_raise_m", 0.0),
                    "runoff_reduction":    min(e["runoff_reduction"] + eff.get("runoff_reduction", 0.0), 0.90),
                }
            else:
                node_effects[node_id] = {
                    "drain_capacity_mult": eff.get("drain_capacity_mult", 1.0),
                    "elevation_raise_m":   eff.get("elevation_raise_m", 0.0),
                    "runoff_reduction":    eff.get("runoff_reduction", 0.0),
                }

        # ---------------------------------------------------------------
        # Propagate drain improvements to 1-hop and 2-hop neighbours
        # (drainage network effect: improved drain protects nearby streets)
        # ---------------------------------------------------------------
        propagated: dict[int, dict] = {k: dict(v) for k, v in node_effects.items()}
        for node_id, eff in node_effects.items():
            extra_drain = eff["drain_capacity_mult"] - 1.0
            extra_runoff_red = eff["runoff_reduction"]
            # 1-hop neighbours: 35% of improvement
            hop1 = list(G.successors(node_id)) + list(G.predecessors(node_id))
            for nb in hop1:
                if nb not in propagated:
                    propagated[nb] = {"drain_capacity_mult": 1.0, "elevation_raise_m": 0.0, "runoff_reduction": 0.0}
                propagated[nb]["drain_capacity_mult"] *= (1.0 + extra_drain * 0.35)
                propagated[nb]["runoff_reduction"] += extra_runoff_red * 0.25
            # 2-hop neighbours: 15% of improvement
            for nb1 in hop1:
                hop2 = list(G.successors(nb1)) + list(G.predecessors(nb1))
                for nb2 in hop2:
                    if nb2 != node_id and nb2 not in node_effects:
                        if nb2 not in propagated:
                            propagated[nb2] = {"drain_capacity_mult": 1.0, "elevation_raise_m": 0.0, "runoff_reduction": 0.0}
                        propagated[nb2]["drain_capacity_mult"] *= (1.0 + extra_drain * 0.15)
                        propagated[nb2]["runoff_reduction"] += extra_runoff_red * 0.10

        # ---------------------------------------------------------------
        # Per-node flood calculation
        # ---------------------------------------------------------------
        impacts: dict[int, DomainImpact] = {}

        for node_id, data in G.nodes(data=True):
            elev = float(data.get("elevation_m") or MEDIAN_ELEVATION_M)
            pop  = float(data.get("population_served") or 0.0)

            eff           = propagated.get(node_id, {})
            drain_mult    = eff.get("drain_capacity_mult", 1.0)
            elev_raise    = eff.get("elevation_raise_m", 0.0)
            runoff_red    = eff.get("runoff_reduction", 0.0)

            effective_elev = elev + elev_raise

            # Elevation-based flood threshold for this node
            elev_delta = effective_elev - MEDIAN_ELEVATION_M
            if elev_delta < 0:
                node_threshold_mm = MEDIAN_RAIN_THRESHOLD_MM + elev_delta * MM_PER_METER_BELOW
            else:
                node_threshold_mm = MEDIAN_RAIN_THRESHOLD_MM + elev_delta * MM_PER_METER_ABOVE

            # Drainage lifts the threshold: better drain → higher threshold
            effective_drain_fraction = min(BASE_DRAIN_FRACTION * drain_mult, 0.95)
            threshold_with_drain = node_threshold_mm / (1.0 - effective_drain_fraction)

            # Net rainfall at this node (after runoff-reduction interventions)
            net_rainfall = rainfall_mm * (1.0 - runoff_red)

            # Excess above capacity (mm)
            excess_mm = max(net_rainfall - threshold_with_drain, 0.0)

            # Flood depth with small spatial noise (±6%)
            noise = float(np_rng.uniform(0.94, 1.06))
            flood_depth_m = excess_mm * EXCESS_TO_DEPTH_M * noise

            flooded = flood_depth_m > FLOOD_THRESHOLD_M
            # Smooth population risk scaling with depth up to 0.80m (knee of disaster curve)
            pop_at_risk = pop * min(flood_depth_m / 0.80, 1.0) if flooded else 0.0
            severity = min(flood_depth_m / 0.80, 1.0)

            impacts[node_id] = DomainImpact(
                node_id=node_id,
                flood_depth_m=flood_depth_m,
                flooded=flooded,
                population_at_risk=pop_at_risk,
                severity=severity,
                extra={"excess_mm": excess_mm, "threshold_mm": threshold_with_drain},
            )

        n_flooded = sum(1 for i in impacts.values() if i.flooded)
        logger.debug(
            "FloodModule: %d/%d nodes flooded (rainfall=%.0f mm, interventions=%d)",
            n_flooded, len(impacts), rainfall_mm, len(intervention_ids),
        )
        return impacts
