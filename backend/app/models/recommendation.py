"""Pydantic model: Recommendation (ranked bundles + trade-off table + explanation)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.consequence import ConsequenceVector


class RankedScenario(BaseModel):
    scenario_id: str
    rank: int
    score: float = Field(..., description="Weighted multi-objective score (0-1)")
    consequence: ConsequenceVector
    intervention_ids: list[str]
    total_cost: float


class Recommendation(BaseModel):
    id: str
    budget: float
    ranked: list[RankedScenario]
    explanation: str
    explanation_source: str = "template"  # "llm" | "template"
    weights_used: dict[str, float] = {}
    meta: dict[str, Any] = {}


class OptimizeRequest(BaseModel):
    budget: float = Field(..., gt=0, description="Budget in INR")
    intervention_ids: list[str] = Field(
        default_factory=list,
        description="Pool of candidate interventions to select from"
    )
    rainfall_mm: float = 120.0
    objective_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "risk_reduction": 0.40,
            "population_protected": 0.35,
            "mobility_disruption_min": 0.15,
            "service_availability": 0.10,
        }
    )
    max_bundles: int = Field(default=3, ge=1, le=10)
