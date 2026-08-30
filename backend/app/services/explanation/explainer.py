"""Explanation Service — numbers → plain-language recommendation.

Primary path: Jinja2 template (always deterministic, always fast).
Stretch path:  LLM narration (activated when LLM_API_KEY is set and
               llm_client is available).

Owner: R5
"""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).parent / "templates" / "recommendation.j2"


def _render_template(rec: "Recommendation") -> str:
    """Render the Jinja2 explanation template with recommendation data."""
    try:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_PATH.parent)),
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        tmpl = env.get_template(_TEMPLATE_PATH.name)
    except ImportError:
        logger.debug("jinja2 not installed — using f-string fallback")
        return _render_fstring(rec)
    except Exception as exc:
        logger.warning("Jinja2 template load error: %s — using f-string", exc)
        return _render_fstring(rec)

    if not rec.ranked:
        return "No strategies could be generated for the given budget."

    winner = rec.ranked[0]
    runner_up = rec.ranked[1] if len(rec.ranked) > 1 else None

    budget_cr = rec.budget / 1e7
    n_int = len(winner.intervention_ids)
    risk_pct = f"{winner.consequence.risk_reduction.value * 100:.1f}"
    pop_k = round(winner.consequence.population_protected.value / 1000)
    cost_cr = winner.total_cost / 1e7
    mob_min = winner.consequence.mobility_disruption_min.value

    try:
        text = tmpl.render(
            rec=rec,
            winner=winner,
            runner_up=runner_up,
            budget_cr=budget_cr,
            n_int=n_int,
            risk_pct=risk_pct,
            pop_k=pop_k,
            cost_cr=cost_cr,
            mob_min=mob_min,
        )
        return textwrap.dedent(text).strip()
    except Exception as exc:
        logger.warning("Jinja2 render error: %s — using f-string", exc)
        return _render_fstring(rec)


def _render_fstring(rec: "Recommendation") -> str:
    """Pure Python fallback explanation (no external dependencies)."""
    if not rec.ranked:
        return "No strategies could be generated for the given budget."

    winner = rec.ranked[0]
    runner_up = rec.ranked[1] if len(rec.ranked) > 1 else None

    budget_cr = rec.budget / 1e7
    n_int = len(winner.intervention_ids)
    risk_pct = winner.consequence.risk_reduction.value * 100
    pop_k = round(winner.consequence.population_protected.value / 1000)
    cost_cr = winner.total_cost / 1e7
    mob_min = winner.consequence.mobility_disruption_min.value
    strategy_name = winner.scenario_id.replace("bundle_", "Strategy ")

    mob_text = (
        f"Mobility impact is {mob_min:.1f} minutes of additional average travel time — "
        "a manageable disruption given the flood-risk gains."
        if mob_min > 0.5
        else "Mobility disruption is negligible across the network."
    )

    runner_up_text = ""
    if runner_up:
        diff = (winner.score - runner_up.score) * 100
        runner_name = runner_up.scenario_id.replace("bundle_", "Strategy ")
        runner_up_text = (
            f" Compared to {runner_name}, this recommendation scores {diff:.1f}% higher "
            "on the balanced multi-objective criterion."
        )

    return (
        f"For ₹{budget_cr:.1f} crore, {strategy_name} is the recommended approach. "
        f"It deploys {n_int} targeted intervention{'s' if n_int != 1 else ''} at a total "
        f"investment of ₹{cost_cr:.1f} Cr, reducing flood risk by {risk_pct:.1f}% and "
        f"protecting approximately {pop_k}K residents from flood exposure. "
        f"{mob_text}{runner_up_text} "
        f"This analysis is based on the UrbanTwin physics simulation of T.Nagar's "
        f"infrastructure graph with {rec.meta.get('mc_runs', 50)}-sample Monte Carlo "
        "uncertainty quantification."
    )


class Explainer:
    """Generates plain-language explanations for a Recommendation.

    Uses Jinja2 template as primary path; f-string as fallback.
    LLM path is a stretch feature gated on LLM_API_KEY.
    """

    def explain(self, rec: "Recommendation") -> tuple[str, str]:
        """Generate explanation text.

        Returns:
            (explanation_text, source) where source is "template" or "llm".
        """
        # Try LLM (stretch feature — only if key is set)
        llm_text = self._try_llm(rec)
        if llm_text:
            return llm_text, "llm"

        # Template path (always available)
        text = _render_template(rec)
        return text, "template"

    def _try_llm(self, rec: "Recommendation") -> Optional[str]:
        """Attempt LLM narration. Returns None if not configured or on error."""
        try:
            from app.config import get_settings
            settings = get_settings()
            if not settings.llm_api_key:
                return None
            from app.services.explanation.llm_client import narrate
            return narrate(rec)
        except Exception as exc:
            logger.debug("LLM explanation skipped: %s", exc)
            return None


# Module-level singleton
_explainer: Optional[Explainer] = None


def get_explainer() -> Explainer:
    global _explainer
    if _explainer is None:
        _explainer = Explainer()
    return _explainer
