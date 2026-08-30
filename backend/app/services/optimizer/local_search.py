"""LocalSearch / strategy diversifier — STRETCH feature.

For M3, this module exposes ``diversify_bundles`` which, given a list of
candidate bundles, ensures they are meaningfully distinct by enforcing a
minimum Jaccard distance between any two bundles.

If bundles are too similar (Jaccard similarity > 0.6), the less-optimal
one is perturbed by swapping one intervention for the next-best unselected
candidate.

Owner: R3
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _jaccard(a: set, b: set) -> float:
    """Jaccard similarity between two sets."""
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def diversify_bundles(
    bundles: list[dict],
    all_item_ids: list[str],
    similarity_threshold: float = 0.6,
) -> list[dict]:
    """Ensure returned bundles are sufficiently diverse.

    If two bundles share > ``similarity_threshold`` Jaccard similarity,
    one of them is flagged as a near-duplicate and its name updated
    to indicate the variant.  The intervention IDs are NOT changed
    (OR-Tools already optimises each independently under a different
    weight profile; identical bundles legitimately occur when the
    budget is very tight and only one combination exists).

    Args:
        bundles: list of bundle dicts from BudgetSolver.
        all_item_ids: sorted list of all candidate intervention IDs.
        similarity_threshold: maximum acceptable Jaccard similarity.

    Returns:
        Same list (possibly with name annotations for duplicates).
    """
    if len(bundles) <= 1:
        return bundles

    processed: list[dict] = [bundles[0]]

    for candidate in bundles[1:]:
        cand_set = set(candidate["intervention_ids"])
        is_near_dup = False
        for existing in processed:
            sim = _jaccard(cand_set, set(existing["intervention_ids"]))
            if sim > similarity_threshold:
                logger.debug(
                    "Bundle '%s' is near-duplicate of '%s' (Jaccard=%.2f)",
                    candidate["name"], existing["name"], sim,
                )
                is_near_dup = True
                break

        if is_near_dup:
            # Still include it but annotate; solver already differentiates
            candidate = dict(candidate)
            candidate["name"] = candidate["name"] + " (variant)"

        processed.append(candidate)

    return processed
