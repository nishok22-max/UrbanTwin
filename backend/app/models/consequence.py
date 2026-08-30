"""Pydantic model: ConsequenceVector (values + uncertainty ranges + confidence)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class UncertaintyRange(BaseModel):
    """A point estimate with Monte-Carlo low/high bounds."""
    value: float
    low: float
    high: float

    @property
    def width(self) -> float:
        return self.high - self.low


class ConsequenceVector(BaseModel):
    """Multi-dimensional impact score for one scenario."""
    cost: float = Field(..., description="INR spent")
    risk_reduction: UncertaintyRange = Field(
        ..., description="Δ flood risk reduction (fraction, 0-1)"
    )
    population_protected: UncertaintyRange = Field(
        ..., description="Number of residents better protected"
    )
    mobility_disruption_min: UncertaintyRange = Field(
        ..., description="Added travel time per trip (minutes)"
    )
    service_availability: float = Field(
        ..., description="Fraction of key services remaining accessible (0-1)"
    )
    nodes_flooded_baseline: int = 0
    nodes_flooded_with_intervention: int = 0
    roads_blocked_baseline: int = 0
    roads_blocked_with_intervention: int = 0


class CascadeHop(BaseModel):
    node_id: int
    node_type: str = "road_junction"
    lat: float
    lon: float
    flood_depth_m: float = 0.0
    travel_time_delta_min: float = 0.0
    hop: int = 0


class SimulationRequest(BaseModel):
    scenario_id: str
    intervention_ids: list[str] = Field(default_factory=list)
    rainfall_mm: float = Field(default=160.0, ge=0)
    max_cascade_hops: int = Field(default=3, ge=1, le=5)
    monte_carlo_runs: int = Field(default=50, ge=10, le=500)


class SimulationResult(BaseModel):
    scenario_id: str
    consequence: ConsequenceVector
    cascade_path: list[CascadeHop]
    confidence: ConfidenceLevel
    dominant_uncertainty: str = "rainfall_intensity"
    computation_time_ms: float = 0.0
    conservation_ok: bool = True
    fallback_used: bool = False
    meta: dict[str, Any] = {}
