"""GET /interventions — candidate interventions catalog. Owner: R1/R3"""
from __future__ import annotations

from fastapi import APIRouter

from app.services import graph_service

router = APIRouter(prefix="/interventions", tags=["interventions"])


@router.get("", summary="Candidate interventions catalog")
async def get_interventions() -> dict:
    """Return the full intervention catalog for the demo city.

    Each item includes id, name, type, cost (INR), target node,
    effect parameters, and location coordinates.
    """
    catalog = graph_service.get_intervention_catalog()
    return {
        "count": len(catalog),
        "interventions": catalog,
    }


@router.get("/{intervention_id}", summary="Get a single intervention by ID")
async def get_intervention(intervention_id: str) -> dict:
    """Return a single intervention by ID."""
    item = graph_service.get_intervention_by_id(intervention_id)
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Intervention {intervention_id!r} not found")
    return item
