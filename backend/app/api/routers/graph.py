"""GET /graph — city infrastructure graph as GeoJSON. Owner: R1"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.services import graph_service

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", summary="City infrastructure graph as GeoJSON")
async def get_graph(
    max_nodes: int = Query(default=2296, ge=1, le=5000),
    max_edges: int = Query(default=5481, ge=1, le=20000),
) -> dict:
    """Return the city infrastructure graph (nodes + edges) as a GeoJSON-like dict.

    Used by the frontend to render the map layer.
    Optionally limit node/edge count for performance.
    """
    geojson = graph_service.graph_to_geojson(
        max_nodes=max_nodes,
        max_edges=max_edges,
    )
    return geojson
