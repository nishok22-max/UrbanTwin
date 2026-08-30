"""BudgetSolver — finds optimal/diverse intervention bundles under budget.

Uses OR-Tools 0-1 Knapsack solver (MULTIDIMENSION_BRANCH_AND_BOUND) with
a greedy fallback if OR-Tools cannot solve within time limits.

Owner: R3
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Scaling factor: float scores → int for OR-Tools (6 decimal precision)
_SCORE_SCALE = 1_000_000
# OR-Tools cost scaling: convert float INR to int (round to nearest 1000 INR)
_COST_UNIT = 1_000


def _greedy_knapsack(
    items: list[dict],
    budget: float,
) -> list[str]:
    """Greedy fallback: sort by score/cost ratio, pick while affordable."""
    sorted_items = sorted(
        items,
        key=lambda x: x["score"] / max(x["cost"], 1.0),
        reverse=True,
    )
    selected: list[str] = []
    spent = 0.0
    for item in sorted_items:
        if spent + item["cost"] <= budget:
            selected.append(item["id"])
            spent += item["cost"]
    return selected


def _ortools_knapsack(items: list[dict], budget: float) -> list[str]:
    """OR-Tools branch-and-bound 0-1 knapsack."""
    try:
        from ortools.algorithms.python import knapsack_solver as ks
    except ImportError:
        logger.warning("OR-Tools not available — using greedy fallback")
        return _greedy_knapsack(items, budget)

    n = len(items)
    if n == 0:
        return []

    # Scale to integers
    values = [max(1, int(item["score"] * _SCORE_SCALE)) for item in items]
    weights_list = [max(1, int(item["cost"] / _COST_UNIT)) for item in items]
    capacity = max(1, int(budget / _COST_UNIT))

    solver = ks.KnapsackSolver(
        ks.SolverType.KNAPSACK_MULTIDIMENSION_BRANCH_AND_BOUND_SOLVER,
        "UrbanTwinKnapsack",
    )
    solver.init(values, [weights_list], [capacity])
    try:
        solver.solve()
    except Exception as exc:
        logger.warning("OR-Tools solve error: %s — using greedy fallback", exc)
        return _greedy_knapsack(items, budget)

    return [items[i]["id"] for i in range(n) if solver.best_solution_contains(i)]


class BudgetSolver:
    """Generates up to ``max_bundles`` diverse intervention bundles under budget.

    Each bundle uses a different objective weight profile so the three
    returned strategies offer genuinely different trade-offs:

    - Profile A (flood-defence):   risk_reduction = 0.70
    - Profile B (balanced):        default weights  0.40 / 0.35 / 0.15 / 0.10
    - Profile C (population-first): population_protected = 0.70
    """

    PROFILES = [
        {
            "name": "Strategy A — Flood Defence",
            "weights": {
                "risk_reduction": 0.70,
                "population_protected": 0.15,
                "mobility_disruption_min": 0.10,
                "service_availability": 0.05,
            },
        },
        {
            "name": "Strategy B — Balanced Resilience",
            "weights": {
                "risk_reduction": 0.40,
                "population_protected": 0.35,
                "mobility_disruption_min": 0.15,
                "service_availability": 0.10,
            },
        },
        {
            "name": "Strategy C — Population Shield",
            "weights": {
                "risk_reduction": 0.15,
                "population_protected": 0.70,
                "mobility_disruption_min": 0.10,
                "service_availability": 0.05,
            },
        },
    ]

    def solve(
        self,
        scored_items: list[dict],
        budget: float,
        max_bundles: int = 3,
    ) -> list[dict]:
        """Return up to ``max_bundles`` distinct bundles.

        Args:
            scored_items: list of dicts with keys:
                - "id": intervention ID
                - "cost": float INR
                - "score": float [0,1] base score (used to seed profiles)
                - "marginal_consequence": SimulationResult for the intervention
            budget: maximum total cost in INR
            max_bundles: number of diverse bundles to produce

        Returns:
            list of dicts: {name, intervention_ids, weights}
        """
        from app.services.optimizer.scorer import score_consequence

        if not scored_items:
            return []

        profiles = self.PROFILES[:max_bundles]
        bundles: list[dict] = []
        seen: set[frozenset] = set()  # deduplication

        for profile in profiles:
            # Re-score items under this profile's weights
            profile_items = []
            for item in scored_items:
                marginal = item.get("marginal_consequence")
                if marginal is not None:
                    s = score_consequence(marginal.consequence, profile["weights"])
                else:
                    s = item.get("score", 0.0)
                profile_items.append({
                    "id": item["id"],
                    "cost": item["cost"],
                    "score": s,
                })

            # Filter to affordable items
            affordable = [x for x in profile_items if x["cost"] <= budget]
            if not affordable:
                continue

            selected_ids = _ortools_knapsack(affordable, budget)
            if not selected_ids:
                selected_ids = _greedy_knapsack(affordable, budget)
            if not selected_ids:
                continue

            # Deduplicate bundles
            key = frozenset(selected_ids)
            if key in seen:
                # Try dropping the most expensive item to get a different bundle
                by_cost = sorted(
                    [x for x in affordable if x["id"] in selected_ids],
                    key=lambda x: x["cost"], reverse=True,
                )
                alt = [x for x in selected_ids if x != by_cost[0]["id"]] if by_cost else []
                if alt:
                    key = frozenset(alt)
                    selected_ids = alt
                if key in seen:
                    continue

            seen.add(key)
            bundles.append({
                "name": profile["name"],
                "intervention_ids": selected_ids,
                "weights": profile["weights"],
            })

        return bundles
