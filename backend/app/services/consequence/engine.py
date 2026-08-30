"""ConsequenceEngine — orchestrates domain modules + coupling + uncertainty.

Flow for POST /simulate:
  1. Load graph from GraphService (in-memory).
  2. Run FloodModule (baseline: no interventions).
  3. Run FloodModule (with interventions).
  4. Run MobilityModule (coupled to flood with interventions).
  5. Run CouplingResolver → cascade path.
  6. Run UncertaintyRunner → Monte-Carlo ranges.
  7. Assemble and return SimulationResult.

Conservation check:
  Total flood severity before ≥ total flood severity after (interventions only help).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import networkx as nx

from app.config import get_settings
from app.models.consequence import (
    CascadeHop,
    ConfidenceLevel,
    ConsequenceVector,
    SimulationRequest,
    SimulationResult,
    UncertaintyRange,
)
from app.services.consequence.coupling import CouplingResolver
from app.services.consequence.domains.base import DomainImpact
from app.services.consequence.domains.flood import FloodModule
from app.services.consequence.domains.mobility import MobilityModule
from app.services.consequence.gnn import GNNRefiner
from app.services.consequence.uncertainty import UncertaintyRunner
from app.services import graph_service

logger = logging.getLogger(__name__)


class ConsequenceEngine:
    """Orchestrates the full consequence simulation pipeline."""

    def __init__(self):
        self.flood_module = FloodModule()
        self.mobility_module = MobilityModule()
        self.coupling_resolver = CouplingResolver()
        self.uncertainty_runner = UncertaintyRunner()
        self.gnn_refiner = GNNRefiner()

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        t_start = time.perf_counter()
        settings = get_settings()

        G = graph_service.get_graph()
        catalog = graph_service.get_intervention_catalog()

        # Optional GNN weight refinement (no-op in M2)
        G = self.gnn_refiner.refine_edge_weights(G)

        seed = settings.random_seed

        # ----------------------------------------------------------------
        # Step 1: Flood — null baseline (no interventions)
        # ----------------------------------------------------------------
        flood_null = self.flood_module.compute_impact(
            G=G,
            intervention_ids=[],
            intervention_catalog=catalog,
            rainfall_mm=request.rainfall_mm,
            rng_seed=seed,
        )

        # ----------------------------------------------------------------
        # Step 2: Flood — with interventions
        # ----------------------------------------------------------------
        flood_with = self.flood_module.compute_impact(
            G=G,
            intervention_ids=request.intervention_ids,
            intervention_catalog=catalog,
            rainfall_mm=request.rainfall_mm,
            rng_seed=seed,
        )

        # ----------------------------------------------------------------
        # Step 3: Mobility — coupled to flood (with interventions)
        # ----------------------------------------------------------------
        mob_null = self.mobility_module.compute_impact(
            G=G,
            intervention_ids=[],
            intervention_catalog=catalog,
            rainfall_mm=request.rainfall_mm,
            rng_seed=seed,
            flood_impacts=flood_null,
        )

        mob_with = self.mobility_module.compute_impact(
            G=G,
            intervention_ids=request.intervention_ids,
            intervention_catalog=catalog,
            rainfall_mm=request.rainfall_mm,
            rng_seed=seed,
            flood_impacts=flood_with,
        )

        # ----------------------------------------------------------------
        # Step 4: CouplingResolver → cascade path
        # ----------------------------------------------------------------
        self.coupling_resolver.max_hops = request.max_cascade_hops
        cascade_result = self.coupling_resolver.propagate(
            G=G,
            flood_impacts=flood_with,
            mobility_impacts=mob_with,
            top_k_seeds=15,
        )

        # ----------------------------------------------------------------
        # Step 5: UncertaintyRunner → Monte-Carlo ranges
        # ----------------------------------------------------------------
        uncertainty = self.uncertainty_runner.run(
            flood_impacts_base=flood_with,
            mobility_impacts_base=mob_with,
            flood_impacts_null=flood_null,
            mobility_impacts_null=mob_null,
            rainfall_mm=request.rainfall_mm,
            n_trials=request.monte_carlo_runs,
            rng_seed=seed,
        )

        # ----------------------------------------------------------------
        # Step 6: Conservation check
        # ----------------------------------------------------------------
        sev_null = sum(i.severity for i in flood_null.values())
        sev_with = sum(i.severity for i in flood_with.values())
        conservation_ok = sev_with <= sev_null + 0.01  # tiny tolerance for rounding

        if not conservation_ok:
            logger.warning(
                "Conservation check failed: sev_null=%.2f sev_with=%.2f",
                sev_null, sev_with,
            )

        # ----------------------------------------------------------------
        # Step 7: Compute cost of interventions
        # ----------------------------------------------------------------
        total_cost = sum(
            item["cost"]
            for int_id in request.intervention_ids
            for item in catalog
            if item["id"] == int_id
        )

        # ----------------------------------------------------------------
        # Step 8: Assemble ConsequenceVector
        # ----------------------------------------------------------------
        n_flooded_null = sum(1 for i in flood_null.values() if i.flooded)
        n_flooded_with = sum(1 for i in flood_with.values() if i.flooded)
        n_blocked_null = sum(1 for i in mob_null.values() if not i.road_passable)
        n_blocked_with = sum(1 for i in mob_with.values() if not i.road_passable)

        service_availability = max(0.0, 1.0 - (n_blocked_with / max(len(mob_with), 1)))

        consequence = ConsequenceVector(
            cost=total_cost,
            risk_reduction=UncertaintyRange(
                value=uncertainty.risk_reduction_value,
                low=uncertainty.risk_reduction_low,
                high=uncertainty.risk_reduction_high,
            ),
            population_protected=UncertaintyRange(
                value=uncertainty.population_protected_value,
                low=uncertainty.population_protected_low,
                high=uncertainty.population_protected_high,
            ),
            mobility_disruption_min=UncertaintyRange(
                value=uncertainty.mobility_disruption_value,
                low=uncertainty.mobility_disruption_low,
                high=uncertainty.mobility_disruption_high,
            ),
            service_availability=service_availability,
            nodes_flooded_baseline=n_flooded_null,
            nodes_flooded_with_intervention=n_flooded_with,
            roads_blocked_baseline=n_blocked_null,
            roads_blocked_with_intervention=n_blocked_with,
        )

        # ----------------------------------------------------------------
        # Step 9: Assemble cascade path for frontend
        # ----------------------------------------------------------------
        cascade_hops = [
            CascadeHop(
                node_id=cn.node_id,
                node_type=cn.node_type,
                lat=cn.lat,
                lon=cn.lon,
                flood_depth_m=cn.flood_depth_m,
                travel_time_delta_min=cn.travel_time_delta_min,
                hop=cn.hop,
            )
            for cn in cascade_result.path[:50]  # limit to 50 hops for frontend
        ]

        t_end = time.perf_counter()
        elapsed_ms = (t_end - t_start) * 1000.0

        logger.info(
            "Simulation complete: scenario=%s interventions=%s elapsed=%.0fms flooded=%d→%d",
            request.scenario_id,
            request.intervention_ids,
            elapsed_ms,
            n_flooded_null,
            n_flooded_with,
        )

        return SimulationResult(
            scenario_id=request.scenario_id,
            consequence=consequence,
            cascade_path=cascade_hops,
            confidence=ConfidenceLevel(uncertainty.confidence),
            dominant_uncertainty=uncertainty.dominant_uncertainty,
            computation_time_ms=elapsed_ms,
            conservation_ok=conservation_ok,
            fallback_used=not self.gnn_refiner.available,
            meta={
                "n_flooded_null": n_flooded_null,
                "n_flooded_with": n_flooded_with,
                "n_cascade_nodes": len(cascade_result.path),
                "n_mc_trials": request.monte_carlo_runs,
            },
        )


# Module-level singleton
_engine: Optional[ConsequenceEngine] = None


def get_engine() -> ConsequenceEngine:
    global _engine
    if _engine is None:
        _engine = ConsequenceEngine()
    return _engine
