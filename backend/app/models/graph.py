"""Pydantic models: Node, Edge (graph schema)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class NodeGeometry(BaseModel):
    type: str = "Point"
    coordinates: list[float]


class NodeProperties(BaseModel):
    osmid: int
    x: float
    y: float
    elevation_m: Optional[float] = None
    population: Optional[float] = None
    street_count: Optional[int] = None
    highway: Optional[str] = None
    # synthetic attrs added by graph service
    node_type: str = "road_junction"
    capacity: Optional[float] = None
    population_served: Optional[float] = None


class NodeFeature(BaseModel):
    type: str = "Feature"
    id: str
    properties: NodeProperties
    geometry: NodeGeometry


class EdgeGeometry(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]]


class EdgeProperties(BaseModel):
    u: int
    v: int
    key: int = 0
    osmid: Optional[str] = None
    highway: Optional[str] = None
    length: Optional[float] = None
    speed_kph: Optional[float] = None
    travel_time: Optional[float] = None
    oneway: Optional[bool] = None
    name: Optional[str] = None
    # dependency edge attributes
    edge_type: str = "road"
    weight: float = 1.0
    flooded: bool = False
    flood_depth_m: float = 0.0


class EdgeFeature(BaseModel):
    type: str = "Feature"
    properties: EdgeProperties
    geometry: EdgeGeometry


class GraphGeoJSON(BaseModel):
    type: str = "FeatureCollection"
    nodes: list[NodeFeature]
    edges: list[EdgeFeature]
    meta: dict[str, Any] = {}
