# UrbanTwin - AI Infrastructure Consequence & Decision Simulator

Decision-support digital twin: for a given budget, compare infrastructure
interventions by their cascading consequences and get an explainable,
budget-optimized recommendation.

## Docs
- [PRD.md](PRD.md) - product requirements
- [ARCHITECTURE.md](ARCHITECTURE.md) - system architecture
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - 96h build plan
- [TEAM_ROLES.md](TEAM_ROLES.md) - 5-person roles

## Layout
- `backend/`  - Python + FastAPI (graph, consequence, optimizer, explanation)
- `frontend/` - React + MapLibre GL + Deck.gl
- `data/`     - prepared graph artifacts (gitignored)
- `docs/`     - additional docs/diagrams

## Quick start (once Hour-0 skeleton is filled)
    docker compose up

> This is a scaffold: files are placeholders to be implemented per the plan.
