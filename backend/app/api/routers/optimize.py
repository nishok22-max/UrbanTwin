"""POST /optimize — best intervention bundle(s) under budget.

Full M3 implementation:
  1. Build intervention pool from request (or full catalog).
  2. Compute marginal consequence for each intervention via MarginalCache.
  3. Score each marginal result with scorer.py.
  4. BudgetSolver generates up to max_bundles diverse intervention bundles
     (using different objective weight profiles).
  5. Full simulation of each bundle via ConsequenceEngine.
  6. Rank bundles by primary (request) weights.
  7. Generate plain-language explanation via Explainer.
  8. Persist Recommendation in recommendation_store; return to client.

Owner: R3
"""
from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, HTTPException

from app.models.consequence import SimulationRequest
from app.models.recommendation import OptimizeRequest, RankedScenario, Recommendation
from app.services import graph_service
from app.services.optimizer.marginal_cache import get_marginal_cache
from app.services.optimizer.scorer import score_consequence, score_marginal
from app.services.optimizer.solver import BudgetSolver
from app.services.optimizer.local_search import diversify_bundles
from app.services.consequence.engine import get_engine
from app.services.explanation.explainer import get_explainer
from app.services import recommendation_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/optimize", tags=["optimize"])


@router.post(
    "",
    response_model=Recommendation,
    summary="[M3] Best intervention bundles under budget — fully implemented",
)
async def optimize(body: OptimizeRequest) -> Recommendation:
    """Find the best intervention bundle(s) under the given budget.

    Returns a ``Recommendation`` with:
    - ``ranked``: up to 3 strategies sorted by weighted multi-objective score.
    - ``explanation``: plain-language summary of why Strategy #1 is recommended.
    - ``id``: use this to retrieve the recommendation later via GET /recommendation/{id}.

    Performance target: < 5 seconds for a catalog of 22 interventions.
    """
    t0 = time.perf_counter()
    catalog = graph_service.get_intervention_catalog()

    # ----------------------------------------------------------------
    # Step 1: Build the candidate pool
    # ----------------------------------------------------------------
    if body.intervention_ids:
        pool = [i for i in catalog if i["id"] in set(body.intervention_ids)]
        if not pool:
            raise HTTPException(
                status_code=400,
                detail="None of the specified intervention_ids exist in the catalog.",
            )
    else:
        pool = catalog

    affordable_pool = [i for i in pool if i["cost"] <= body.budget]
    if not affordable_pool:
        raise HTTPException(
            status_code=422,
            detail=f"No single intervention fits within the budget of ₹{body.budget:,.0f}. "
                   f"The cheapest available item costs ₹{min(i['cost'] for i in pool):,.0f}.",
        )

    # ----------------------------------------------------------------
    # Step 2: Marginal simulations (cached — fast after first call)
    # ----------------------------------------------------------------
    cache = get_marginal_cache()
    engine = get_engine()
    weights = body.objective_weights

    scored_items: list[dict] = []
    for item in affordable_pool:
        try:
            marginal = cache.get_marginal(item["id"], body.rainfall_mm)
            base_score = score_marginal(marginal, weights)
        except Exception as exc:
            logger.warning("Marginal sim failed for %s: %s — skipping", item["id"], exc)
            continue

        scored_items.append({
            "id": item["id"],
            "cost": item["cost"],
            "score": base_score,
            "marginal_consequence": marginal,
        })

    if not scored_items:
        raise HTTPException(status_code=500, detail="All marginal simulations failed.")

    # ----------------------------------------------------------------
    # Step 3: Solve — generate diverse bundles
    # ----------------------------------------------------------------
    solver = BudgetSolver()
    raw_bundles = solver.solve(scored_items, body.budget, body.max_bundles)
    raw_bundles = diversify_bundles(raw_bundles, [x["id"] for x in scored_items])

    if not raw_bundles:
        raise HTTPException(
            status_code=422,
            detail="Optimizer could not find any feasible bundle under the given budget.",
        )

    # ----------------------------------------------------------------
    # Step 4: Full simulation of each bundle
    # ----------------------------------------------------------------
    ranked_scenarios: list[RankedScenario] = []

    for bundle_idx, bundle in enumerate(raw_bundles):
        bundle_ids = bundle["intervention_ids"]
        scenario_id = f"bundle_{chr(65 + bundle_idx)}"  # "bundle_A", "bundle_B", ...

        try:
            sim_req = SimulationRequest(
                scenario_id=scenario_id,
                intervention_ids=bundle_ids,
                rainfall_mm=body.rainfall_mm,
                max_cascade_hops=3,
                monte_carlo_runs=30,   # fewer runs for speed
            )
            sim_result = engine.simulate(sim_req)
        except Exception as exc:
            logger.warning("Bundle simulation failed for %s: %s", scenario_id, exc)
            continue

        total_cost = sum(
            item["cost"]
            for int_id in bundle_ids
            for item in catalog
            if item["id"] == int_id
        )
        score = score_consequence(sim_result.consequence, weights)

        ranked_scenarios.append(
            RankedScenario(
                scenario_id=scenario_id,
                rank=0,   # filled in after sorting
                score=score,
                consequence=sim_result.consequence,
                intervention_ids=bundle_ids,
                total_cost=total_cost,
            )
        )

    if not ranked_scenarios:
        raise HTTPException(status_code=500, detail="All bundle simulations failed.")

    # ----------------------------------------------------------------
    # Step 5: Sort by score (descending) and assign ranks
    # ----------------------------------------------------------------
    ranked_scenarios.sort(key=lambda x: x.score, reverse=True)
    for rank_idx, scenario in enumerate(ranked_scenarios, start=1):
        # Pydantic model fields are immutable; rebuild with correct rank
        ranked_scenarios[rank_idx - 1] = RankedScenario(
            scenario_id=scenario.scenario_id,
            rank=rank_idx,
            score=scenario.score,
            consequence=scenario.consequence,
            intervention_ids=scenario.intervention_ids,
            total_cost=scenario.total_cost,
        )

    # ----------------------------------------------------------------
    # Step 6: Generate explanation
    # ----------------------------------------------------------------
    rec_id = f"rec_{uuid.uuid4().hex[:8]}"
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    G = graph_service.get_graph()

    recommendation = Recommendation(
        id=rec_id,
        budget=body.budget,
        ranked=ranked_scenarios,
        explanation="",   # filled below
        explanation_source="template",
        weights_used=weights,
        meta={
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
            "mc_runs": 30,
            "n_candidates": len(scored_items),
            "n_bundles_tried": len(raw_bundles),
            "elapsed_ms": round(elapsed_ms, 1),
        },
    )

    explainer = get_explainer()
    explanation_text, explanation_source = explainer.explain(recommendation)

    # Rebuild with explanation (Pydantic models are immutable; re-instantiate)
    recommendation = Recommendation(
        id=rec_id,
        budget=body.budget,
        ranked=ranked_scenarios,
        explanation=explanation_text,
        explanation_source=explanation_source,
        weights_used=weights,
        meta=recommendation.meta,
    )

    # ----------------------------------------------------------------
    # Step 7: Persist and return
    # ----------------------------------------------------------------
    recommendation_store.save(recommendation)

    logger.info(
        "Optimize complete: budget=%.0f bundles=%d top_score=%.3f elapsed=%.0fms",
        body.budget,
        len(ranked_scenarios),
        ranked_scenarios[0].score if ranked_scenarios else 0.0,
        elapsed_ms,
    )

    return recommendation
