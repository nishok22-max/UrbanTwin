"""Pydantic model: Scenario (budget + set of interventions)."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ScenarioCreate(BaseModel):
    """Request body for POST /scenarios."""
    budget: float = Field(..., description="Budget in INR", gt=0)
    intervention_ids: list[str] = Field(
        default_factory=list,
        description="Explicit intervention IDs; if empty, system auto-generates."
    )
    name: Optional[str] = None
    description: Optional[str] = None
    rainfall_mm: float = Field(
        default=120.0,
        description="Simulated rainfall in mm (driver for flood model)"
    )


class Scenario(BaseModel):
    id: str
    name: str
    description: str = ""
    budget: float
    intervention_ids: list[str]
    rainfall_mm: float = 120.0
    auto_generated: bool = False
