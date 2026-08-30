"""Scorer — consequence vector → weighted multi-objective score (0–1).

Used by BudgetSolver to rank intervention bundles.
Owner: R3
"""
from __future__ import annotations

import logging

from app.models.consequence import ConsequenceVector

logger = logging.getLogger(__name__)

# Normalisation constants (calibrated to T.Nagar simulation outputs)
_POP_MAX = 80_000.0     # reasonable upper bound for population protected
_MOB_MAX = 30.0          # minutes of average extra travel time (severe scenario)


def score_consequence(
    consequence: ConsequenceVector,
    weights: dict[str, float],
) -> float:
    """Map a ConsequenceVector to a scalar score in [0, 1].

    Each dimension is individually normalised to [0, 1], then combined
    with caller-supplied weights. Weights need not sum to 1 (they are
    normalised internally so the score is always in [0, 1]).

    Args:
        consequence: full simulation consequence vector.
        weights: dict with optional keys:
            - "risk_reduction"          (default 0.40)
            - "population_protected"    (default 0.35)
            - "mobility_disruption_min" (default 0.15)
            - "service_availability"    (default 0.10)

    Returns:
        Scalar score in [0, 1]. Higher = better.
    """
    w_risk   = weights.get("risk_reduction", 0.40)
    w_pop    = weights.get("population_protected", 0.35)
    w_mob    = weights.get("mobility_disruption_min", 0.15)
    w_svc    = weights.get("service_availability", 0.10)

    total_w = w_risk + w_pop + w_mob + w_svc
    if total_w <= 0.0:
        return 0.0

    # Each dimension → [0, 1]
    risk_score = float(consequence.risk_reduction.value)                          # already fraction
    pop_score  = min(float(consequence.population_protected.value) / _POP_MAX, 1.0)
    # Lower mobility disruption → higher score
    mob_score  = max(0.0, 1.0 - float(consequence.mobility_disruption_min.value) / _MOB_MAX)
    svc_score  = float(consequence.service_availability)                          # already fraction

    # Clamp all to [0, 1]
    risk_score = max(0.0, min(1.0, risk_score))
    pop_score  = max(0.0, min(1.0, pop_score))
    mob_score  = max(0.0, min(1.0, mob_score))
    svc_score  = max(0.0, min(1.0, svc_score))

    raw = (w_risk * risk_score + w_pop * pop_score +
           w_mob * mob_score + w_svc * svc_score)

    return float(raw / total_w)


def score_marginal(
    marginal_result,   # SimulationResult (avoid circular import with string annotation)
    weights: dict[str, float],
) -> float:
    """Convenience wrapper: score a single-intervention SimulationResult."""
    return score_consequence(marginal_result.consequence, weights)
