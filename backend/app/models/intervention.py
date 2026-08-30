"""Pydantic model: Intervention (target, cost, effect, duration)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class InterventionType(str, Enum):
    drain_upgrade = "drain_upgrade"
    road_elevation = "road_elevation"
    pump_install = "pump_install"
    retention_pond = "retention_pond"
    permeable_surface = "permeable_surface"
    road_barrier = "road_barrier"
    channel_widen = "channel_widen"
    green_roof = "green_roof"


class InterventionEffect(BaseModel):
    """Physics parameters that change when an intervention is applied."""
    drain_capacity_mult: float = 1.0          # multiplier on drain capacity
    elevation_raise_m: float = 0.0            # raise node elevation by N metres
    road_capacity_mult: float = 1.0           # road flow-capacity multiplier
    runoff_reduction: float = 0.0             # fraction of runoff absorbed (0–1)
    travel_time_mult: float = 1.0             # baseline travel-time multiplier


class Intervention(BaseModel):
    id: str
    name: str
    description: str = ""
    target_node: int                          # OSM node id
    intervention_type: InterventionType
    cost: float = Field(..., description="Cost in INR")
    effect: InterventionEffect
    duration_weeks: int = 4
    priority_area: bool = False               # true if in a flood-prone ward

    class Config:
        use_enum_values = True
