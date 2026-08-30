"""POST /scenarios — create/auto-generate alternative scenarios from a budget. Owner: R1/R3"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter

from app.models.scenario import Scenario, ScenarioCreate
from app.services import graph_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])

# In-memory scenario store (M2; persisted to DB in M3)
_scenarios: dict[str, Scenario] = {}


@router.post("", response_model=dict, summary="Create or auto-generate scenarios from a budget")
async def create_scenarios(body: ScenarioCreate) -> dict:
    """Create or auto-generate ≥3 alternative intervention strategies under budget.

    If intervention_ids is empty, auto-generates 3 strategies:
      - Strategy A: Maximum flood risk reduction
      - Strategy B: Balanced flood + mobility
      - Strategy C: Maximum population protection
    """
    catalog = graph_service.get_intervention_catalog()
    budget = body.budget

    scenarios = []

    if body.intervention_ids:
        # Explicit scenario
        scn = Scenario(
            id=f"scn_{uuid.uuid4().hex[:8]}",
            name=body.name or "Custom Scenario",
            description=body.description or "",
            budget=budget,
            intervention_ids=body.intervention_ids,
            rainfall_mm=body.rainfall_mm,
            auto_generated=False,
        )
        _scenarios[scn.id] = scn
        scenarios.append(scn)
    else:
        # Auto-generate 3 strategies
        affordable = [i for i in catalog if i["cost"] <= budget]

        # Strategy A: Drain upgrades (flood-focused) — top by drain_capacity_mult
        drain_items = sorted(
            [i for i in affordable if i["intervention_type"] == "drain_upgrade"],
            key=lambda x: x["effect"]["drain_capacity_mult"], reverse=True
        )
        scn_a = _make_scenario("scn_a", "Strategy A — Flood Defence", budget, drain_items[:3], body.rainfall_mm)

        # Strategy B: Balanced — mix of drain + road elevation
        elev_items = sorted(
            [i for i in affordable if i["intervention_type"] in ("road_elevation", "pump_install")],
            key=lambda x: x["cost"]
        )
        scn_b = _make_scenario("scn_b", "Strategy B — Balanced Resilience", budget,
                               drain_items[:2] + elev_items[:1], body.rainfall_mm)

        # Strategy C: Population protection (retention + permeable)
        pop_items = sorted(
            [i for i in affordable if i["intervention_type"] in ("retention_pond", "permeable_surface")],
            key=lambda x: -x.get("population_served", 0)
        )
        scn_c = _make_scenario("scn_c", "Strategy C — Population Shield", budget,
                               pop_items[:2] + drain_items[:1], body.rainfall_mm)

        for scn in [scn_a, scn_b, scn_c]:
            if scn:
                _scenarios[scn.id] = scn
                scenarios.append(scn)

    return {"count": len(scenarios), "scenarios": [s.model_dump() for s in scenarios]}


def _make_scenario(
    scn_id: str,
    name: str,
    budget: float,
    items: list[dict],
    rainfall_mm: float,
) -> Optional[Scenario]:
    """Build a scenario that fits within budget."""
    selected = []
    spent = 0.0
    for item in items:
        if spent + item["cost"] <= budget:
            selected.append(item["id"])
            spent += item["cost"]
    if not selected:
        return None
    return Scenario(
        id=scn_id,
        name=name,
        budget=budget,
        intervention_ids=selected,
        rainfall_mm=rainfall_mm,
        auto_generated=True,
    )


@router.get("/{scenario_id}", response_model=Scenario, summary="Get a saved scenario")
async def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in _scenarios:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id!r} not found")
    return _scenarios[scenario_id]


@router.get("", summary="List saved scenarios")
async def list_scenarios() -> dict:
    return {"count": len(_scenarios), "scenarios": list(_scenarios.values())}
