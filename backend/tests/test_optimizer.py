"""Comprehensive tests for Optimizer Service (M3).

Covers:
  - scorer.py: score ordering, weight sensitivity
  - BudgetSolver: budget constraint respected, bundle diversity
  - POST /optimize API: structure, cost constraint, ranking order, explanation
  - GET /recommendation/{id}: retrieval
  - Performance: POST /optimize < 5 seconds
"""
from __future__ import annotations

import time

import pytest

from app.models.consequence import ConsequenceVector, UncertaintyRange, ConfidenceLevel
from app.models.recommendation import OptimizeRequest
from app.services.optimizer.scorer import score_consequence
from app.services.optimizer.solver import BudgetSolver, _greedy_knapsack
from app.services.optimizer.local_search import diversify_bundles
from app.services import recommendation_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_consequence(
    risk_reduction: float = 0.3,
    population_protected: float = 10000.0,
    mobility_disruption: float = 5.0,
    service_availability: float = 0.85,
    cost: float = 1_000_000.0,
) -> ConsequenceVector:
    """Build a synthetic ConsequenceVector for unit testing."""
    return ConsequenceVector(
        cost=cost,
        risk_reduction=UncertaintyRange(value=risk_reduction, low=risk_reduction * 0.8, high=risk_reduction * 1.2),
        population_protected=UncertaintyRange(value=population_protected, low=population_protected * 0.8, high=population_protected * 1.2),
        mobility_disruption_min=UncertaintyRange(value=mobility_disruption, low=mobility_disruption * 0.8, high=mobility_disruption * 1.3),
        service_availability=service_availability,
        nodes_flooded_baseline=100,
        nodes_flooded_with_intervention=60,
        roads_blocked_baseline=20,
        roads_blocked_with_intervention=10,
    )


DEFAULT_WEIGHTS = {
    "risk_reduction": 0.40,
    "population_protected": 0.35,
    "mobility_disruption_min": 0.15,
    "service_availability": 0.10,
}


# ---------------------------------------------------------------------------
# scorer.py tests
# ---------------------------------------------------------------------------

class TestScorer:
    def test_score_is_in_unit_interval(self):
        """Score must always be in [0, 1]."""
        c = _make_consequence()
        s = score_consequence(c, DEFAULT_WEIGHTS)
        assert 0.0 <= s <= 1.0

    def test_better_consequence_gives_higher_score(self):
        """Higher risk reduction → higher score under identical weights."""
        c_good = _make_consequence(risk_reduction=0.6, population_protected=30000.0)
        c_poor = _make_consequence(risk_reduction=0.1, population_protected=5000.0)
        s_good = score_consequence(c_good, DEFAULT_WEIGHTS)
        s_poor = score_consequence(c_poor, DEFAULT_WEIGHTS)
        assert s_good > s_poor

    def test_flood_focused_weights_reward_risk_reduction(self):
        """With flood-focused weights, high risk reduction dominates."""
        flood_weights = {"risk_reduction": 0.80, "population_protected": 0.10,
                         "mobility_disruption_min": 0.05, "service_availability": 0.05}
        c_flood = _make_consequence(risk_reduction=0.7, population_protected=2000.0)
        c_pop   = _make_consequence(risk_reduction=0.1, population_protected=50000.0)
        s_flood = score_consequence(c_flood, flood_weights)
        s_pop   = score_consequence(c_pop, flood_weights)
        assert s_flood > s_pop

    def test_population_focused_weights_reward_large_pop(self):
        """With pop-focused weights, high population count dominates."""
        pop_weights = {"risk_reduction": 0.10, "population_protected": 0.80,
                       "mobility_disruption_min": 0.05, "service_availability": 0.05}
        c_flood = _make_consequence(risk_reduction=0.8, population_protected=100.0)
        c_pop   = _make_consequence(risk_reduction=0.05, population_protected=70000.0)
        s_flood = score_consequence(c_flood, pop_weights)
        s_pop   = score_consequence(c_pop, pop_weights)
        assert s_pop > s_flood

    def test_score_zero_weights_returns_zero(self):
        """All-zero weight VALUES (not missing keys) → score is zero."""
        c = _make_consequence()
        zero_weights = {
            "risk_reduction": 0.0,
            "population_protected": 0.0,
            "mobility_disruption_min": 0.0,
            "service_availability": 0.0,
        }
        s = score_consequence(c, zero_weights)
        assert s == 0.0

    def test_higher_mobility_disruption_lowers_score(self):
        c_low  = _make_consequence(mobility_disruption=1.0)
        c_high = _make_consequence(mobility_disruption=25.0)
        s_low  = score_consequence(c_low, DEFAULT_WEIGHTS)
        s_high = score_consequence(c_high, DEFAULT_WEIGHTS)
        assert s_low > s_high


# ---------------------------------------------------------------------------
# solver.py tests
# ---------------------------------------------------------------------------

class TestBudgetSolver:
    def _make_items(self, n: int = 10, base_cost: float = 1_000_000.0) -> list[dict]:
        """Create synthetic scored items for solver tests."""
        from app.models.consequence import SimulationResult, CascadeHop
        items = []
        for i in range(n):
            cost = base_cost * (0.5 + i * 0.3)
            risk = 0.05 + i * 0.04
            pop  = 2000.0 + i * 1500.0
            c = _make_consequence(risk_reduction=min(risk, 0.95), population_protected=pop, cost=cost)
            # Build minimal SimulationResult for marginal_consequence
            sim = SimulationResult(
                scenario_id=f"marginal_int_{i+1:02d}_160.0",
                consequence=c,
                cascade_path=[],
                confidence=ConfidenceLevel.medium,
            )
            items.append({"id": f"int_{i+1:02d}", "cost": cost, "score": score_consequence(c, DEFAULT_WEIGHTS), "marginal_consequence": sim})
        return items

    def test_greedy_respects_budget(self):
        budget = 3_000_000.0
        items = [
            {"id": "a", "cost": 1_000_000.0, "score": 0.8},
            {"id": "b", "cost": 1_500_000.0, "score": 0.7},
            {"id": "c", "cost": 2_000_000.0, "score": 0.9},  # won't fit with a+b
        ]
        selected = _greedy_knapsack(items, budget)
        total = sum(i["cost"] for i in items if i["id"] in selected)
        assert total <= budget

    def test_solver_bundles_respect_budget(self):
        budget = 5_000_000.0
        items = self._make_items(8, base_cost=1_200_000.0)
        solver = BudgetSolver()
        bundles = solver.solve(items, budget, max_bundles=3)
        assert len(bundles) >= 1
        for bundle in bundles:
            total = sum(i["cost"] for i in items if i["id"] in bundle["intervention_ids"])
            assert total <= budget + 1.0, f"Bundle exceeds budget: {total:.0f} > {budget:.0f}"

    def test_solver_returns_up_to_max_bundles(self):
        items = self._make_items(12, base_cost=800_000.0)
        solver = BudgetSolver()
        bundles = solver.solve(items, budget=10_000_000.0, max_bundles=3)
        assert 1 <= len(bundles) <= 3

    def test_solver_handles_tight_budget(self):
        """If only one item fits, solver returns it."""
        items = [
            {"id": "int_01", "cost": 1_000_000.0, "score": 0.5, "marginal_consequence": None},
            {"id": "int_02", "cost": 5_000_000.0, "score": 0.9, "marginal_consequence": None},
        ]
        solver = BudgetSolver()
        bundles = solver.solve(items, budget=1_500_000.0, max_bundles=3)
        assert len(bundles) >= 1
        for bundle in bundles:
            assert "int_01" in bundle["intervention_ids"]
            assert "int_02" not in bundle["intervention_ids"]

    def test_diversify_bundles_annotates_duplicates(self):
        bundles = [
            {"name": "Strategy A", "intervention_ids": ["a", "b", "c"], "weights": {}},
            {"name": "Strategy B", "intervention_ids": ["a", "b", "c"], "weights": {}},  # identical
        ]
        result = diversify_bundles(bundles, ["a", "b", "c", "d"])
        # Second bundle should be annotated as a variant
        assert any("variant" in b["name"] for b in result[1:])


# ---------------------------------------------------------------------------
# API tests: POST /optimize
# ---------------------------------------------------------------------------

class TestOptimizeAPI:
    def test_optimize_returns_recommendation_structure(self, client):
        """POST /optimize returns Recommendation with ranked list."""
        payload = {
            "budget": 8_000_000,
            "rainfall_mm": 160.0,
            "max_bundles": 3,
        }
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "id" in data
        assert "ranked" in data
        assert "explanation" in data
        assert len(data["ranked"]) >= 1

    def test_optimize_ranked_by_score(self, client):
        """Ranked list must be sorted descending by score."""
        payload = {"budget": 10_000_000, "rainfall_mm": 160.0, "max_bundles": 3}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        ranked = res.json()["ranked"]
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True), f"Scores not sorted: {scores}"

    def test_optimize_bundles_respect_budget(self, client):
        """All bundles must cost <= the supplied budget."""
        budget = 8_000_000
        payload = {"budget": budget, "rainfall_mm": 160.0}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        for ranked_item in res.json()["ranked"]:
            assert ranked_item["total_cost"] <= budget + 1, (
                f"Bundle cost {ranked_item['total_cost']} exceeds budget {budget}"
            )

    def test_optimize_ranks_are_sequential(self, client):
        """Ranks must be 1, 2, 3, … with no gaps."""
        payload = {"budget": 10_000_000, "rainfall_mm": 160.0, "max_bundles": 3}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        ranks = [r["rank"] for r in res.json()["ranked"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_optimize_explanation_is_non_empty(self, client):
        """Explanation must be a non-trivial string."""
        payload = {"budget": 10_000_000, "rainfall_mm": 160.0}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        explanation = res.json()["explanation"]
        assert isinstance(explanation, str)
        assert len(explanation) > 50, f"Explanation too short: {explanation!r}"

    def test_optimize_consequence_fields_present(self, client):
        """Each ranked item must have a complete ConsequenceVector."""
        payload = {"budget": 10_000_000, "rainfall_mm": 160.0}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        winner = res.json()["ranked"][0]
        c = winner["consequence"]
        assert "risk_reduction" in c
        assert "population_protected" in c
        assert "mobility_disruption_min" in c
        assert "service_availability" in c

    def test_optimize_with_explicit_intervention_pool(self, client, intervention_catalog):
        """Optimizer works when a subset of interventions is given."""
        pool_ids = [i["id"] for i in intervention_catalog[:5]]
        payload = {
            "budget": 10_000_000,
            "intervention_ids": pool_ids,
            "rainfall_mm": 160.0,
        }
        res = client.post("/optimize", json=payload)
        assert res.status_code == 200
        for ranked_item in res.json()["ranked"]:
            for int_id in ranked_item["intervention_ids"]:
                assert int_id in pool_ids, f"Unexpected intervention {int_id} in result"

    def test_optimize_budget_too_small_returns_422(self, client):
        """Budget smaller than the cheapest intervention → 422."""
        payload = {"budget": 100, "rainfall_mm": 160.0}
        res = client.post("/optimize", json=payload)
        assert res.status_code == 422

    def test_optimize_stores_recommendation_retrievable(self, client):
        """POST /optimize stores result; GET /recommendation/{id} retrieves it."""
        payload = {"budget": 8_000_000, "rainfall_mm": 160.0}
        res_opt = client.post("/optimize", json=payload)
        assert res_opt.status_code == 200
        rec_id = res_opt.json()["id"]

        res_get = client.get(f"/recommendation/{rec_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == rec_id

    def test_recommendation_not_found_returns_404(self, client):
        """GET /recommendation/nonexistent → 404."""
        res = client.get("/recommendation/does_not_exist")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Performance test
# ---------------------------------------------------------------------------

class TestOptimizePerformance:
    def test_optimize_completes_within_5_seconds(self, client):
        """POST /optimize must complete in < 5 seconds (P0 requirement)."""
        payload = {"budget": 10_000_000, "rainfall_mm": 160.0, "max_bundles": 3}
        t0 = time.perf_counter()
        res = client.post("/optimize", json=payload)
        elapsed = time.perf_counter() - t0
        assert res.status_code == 200, f"Optimize failed: {res.text}"
        assert elapsed < 5.0, f"POST /optimize took {elapsed:.2f}s — exceeds 5s target"
