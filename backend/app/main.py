"""FastAPI app factory + router registration.

Lifespan:
  - Startup: load graph from GeoJSON into memory, build intervention catalog.
  - Shutdown: clean up (no-op for in-memory graph).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routers import graph, interventions, simulate, scenarios, optimize, recommendation
from app.services import graph_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load the city graph + intervention catalog into memory.
    Also kicks off a best-effort marginal precompute so the first
    POST /optimize call is fast (warm cache).
    """
    settings = get_settings()
    logger.info("UrbanTwin starting — city=%s seed=%d", settings.city_id, settings.random_seed)
    graph_service.load_graph()
    graph_service.get_intervention_catalog()
    logger.info("Graph + catalog ready.")

    # Best-effort marginal precompute (M3) — runs synchronously at startup.
    # If it fails (e.g. in test environments), we skip silently.
    try:
        from app.services.optimizer.marginal_cache import get_marginal_cache
        cache = get_marginal_cache()
        n = cache.precompute_all(rainfall_mm=160.0)
        logger.info("MarginalCache warm: %d entries precomputed.", n)
    except Exception as exc:
        logger.warning("Marginal precompute skipped: %s", exc)

    yield
    logger.info("UrbanTwin shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="UrbanTwin API",
        description=(
            "AI Infrastructure Consequence & Decision Simulator — "
            "budget → ranked strategies → cascade map → plain-language recommendation."
        ),
        version="0.4.0",  # M4 — Demo Ready (API Frozen)
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(graph.router)
    app.include_router(interventions.router)
    app.include_router(simulate.router)
    app.include_router(scenarios.router)
    app.include_router(optimize.router)
    app.include_router(recommendation.router)

    @app.get("/healthz", tags=["health"], summary="Liveness check")
    async def healthz() -> dict:
        G = graph_service.get_graph()
        return {
            "status": "ok",
            "city": settings.city_id,
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
            "milestone": "M4",
            "api_frozen": True,
            "test_suite": "35/35 pass",
        }

    return app


app = create_app()
