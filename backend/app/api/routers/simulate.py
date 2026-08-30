"""POST /simulate — run consequence engine for one scenario. Owner: R3 <- R2"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.models.consequence import SimulationRequest, SimulationResult
from app.services.consequence.engine import get_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.post("", response_model=SimulationResult, summary="Run consequence engine for a scenario")
async def simulate(request: SimulationRequest) -> SimulationResult:
    """Simulate cascading consequences of a scenario (intervention set + rainfall).

    Returns:
      - consequence vector (flood risk reduction, population protected,
        mobility disruption) with Monte-Carlo uncertainty ranges.
      - cascade path: ordered list of affected nodes for map animation.
      - confidence level and dominant uncertainty source.

    Physics model (FloodModule + MobilityModule) always runs.
    GNN refiner is a no-op in M2 (physics-only mode).
    """
    try:
        engine = get_engine()
        result = engine.simulate(request)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Simulation failed for scenario %s", request.scenario_id)
        raise HTTPException(status_code=500, detail=f"Simulation error: {e}")


@router.post("/what-if", response_model=SimulationResult, summary="Quick what-if: single intervention toggle")
async def what_if(intervention_id: str, rainfall_mm: float = 120.0) -> SimulationResult:
    """Convenience endpoint: toggle a single intervention and show the delta.

    Automatically creates a scenario ID and runs simulation.
    """
    request = SimulationRequest(
        scenario_id=f"whatif_{intervention_id}",
        intervention_ids=[intervention_id],
        rainfall_mm=rainfall_mm,
        max_cascade_hops=3,
        monte_carlo_runs=50,
    )
    return await simulate(request)
