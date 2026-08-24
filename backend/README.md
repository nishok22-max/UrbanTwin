# UrbanTwin Backend (Python + FastAPI)

- `app/api/routers/`      - HTTP endpoints (frozen contract)
- `app/services/graph_service.py`   - Layer 1: digital twin (R1)
- `app/services/consequence/`       - Layer 2: physics + GNN + uncertainty (R2)
- `app/services/optimizer/`         - Layer 3: OR-Tools budget optimizer (R3)
- `app/services/explanation/`       - Layer 3: LLM narration + fallback (R5)
- `app/models/`           - Pydantic contract models
- `pipeline/`             - offline data prep -> prepared graph (R1)
- `tests/`                - unit + synthetic-twin validation
