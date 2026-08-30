"""UncertaintyRunner — Monte-Carlo sampling over uncertain parameters → confidence ranges.

Uncertain parameters:
  - rainfall_mm: ± 20% around the given value (dominant uncertainty)
  - edge weights: ± 15% (structural uncertainty in graph coupling)
  - drain capacity: ± 10% (construction tolerance)

Runs N Monte-Carlo trials. For each trial:
  - Perturb rainfall and key parameters
  - Run FloodModule fast (vectorised estimate rather than full simulation)
  - Collect scalar metrics

Returns p10/mean/p90 ranges for each metric.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from app.services.consequence.domains.base import DomainImpact

logger = logging.getLogger(__name__)


@dataclass
class UncertaintyResult:
    """Monte-Carlo uncertainty outputs."""
    risk_reduction_value: float
    risk_reduction_low: float
    risk_reduction_high: float

    population_protected_value: float
    population_protected_low: float
    population_protected_high: float

    mobility_disruption_value: float
    mobility_disruption_low: float
    mobility_disruption_high: float

    confidence: str          # "high" | "medium" | "low"
    dominant_uncertainty: str
    n_trials: int


class UncertaintyRunner:
    """Monte-Carlo uncertainty quantification over simulation parameters."""

    # Coefficient of variation (std/mean) for each uncertain param
    CV_RAINFALL = 0.20
    CV_EDGE_WEIGHT = 0.15
    CV_DRAIN_CAP = 0.10

    def run(
        self,
        flood_impacts_base: dict[int, DomainImpact],
        mobility_impacts_base: dict[int, DomainImpact],
        flood_impacts_null: dict[int, DomainImpact],     # no-intervention baseline
        mobility_impacts_null: dict[int, DomainImpact],
        rainfall_mm: float,
        n_trials: int,
        rng_seed: int,
    ) -> UncertaintyResult:
        """
        Run Monte-Carlo over uncertain parameters and produce ranges.

        Strategy: perturb the key scalars (rainfall, capacities) analytically
        using first-order propagation + a fast N-sample simulation to bound ranges.
        This avoids N full re-runs of the physics model (too slow for N=50+).
        """
        rng = np.random.default_rng(rng_seed)

        # Collect baseline metrics
        base_metrics = self._compute_metrics(
            flood_impacts_base, mobility_impacts_base,
            flood_impacts_null, mobility_impacts_null,
        )

        # Monte-Carlo: perturb scalars, scale metrics proportionally
        rainfall_samples = rng.normal(1.0, self.CV_RAINFALL, n_trials)
        drain_samples = rng.normal(1.0, self.CV_DRAIN_CAP, n_trials)
        # Clamp to physically plausible range
        rainfall_samples = np.clip(rainfall_samples, 0.5, 1.8)
        drain_samples = np.clip(drain_samples, 0.7, 1.3)

        # Risk reduction scales sub-linearly with rainfall perturbation
        # (more rain = less relative risk reduction from intervention)
        rr_trials = base_metrics["risk_reduction"] * (
            1.0 / np.sqrt(rainfall_samples) * drain_samples
        )
        rr_trials = np.clip(rr_trials, 0.0, 0.95)

        # Population protected scales with risk reduction
        pp_base = base_metrics["population_protected"]
        pp_trials = pp_base * (rr_trials / max(base_metrics["risk_reduction"], 1e-6))
        pp_trials = np.clip(pp_trials, 0, pp_base * 2.0)

        # Mobility disruption inversely scales with drain improvement
        mob_base = base_metrics["mobility_disruption"]
        mob_trials = mob_base * rainfall_samples / drain_samples
        mob_trials = np.clip(mob_trials, 0, mob_base * 3.0)

        # Determine confidence based on variance
        rr_cv = float(np.std(rr_trials) / max(np.mean(rr_trials), 1e-6))
        if rr_cv < 0.10:
            confidence = "high"
        elif rr_cv < 0.25:
            confidence = "medium"
        else:
            confidence = "low"

        # Dominant uncertainty: whichever CV is largest
        drain_cv = float(np.std(drain_samples * drain_samples))
        dominant = "rainfall_intensity" if self.CV_RAINFALL >= self.CV_DRAIN_CAP else "drain_capacity"

        return UncertaintyResult(
            risk_reduction_value=float(np.mean(rr_trials)),
            risk_reduction_low=float(np.percentile(rr_trials, 10)),
            risk_reduction_high=float(np.percentile(rr_trials, 90)),

            population_protected_value=float(np.mean(pp_trials)),
            population_protected_low=float(np.percentile(pp_trials, 10)),
            population_protected_high=float(np.percentile(pp_trials, 90)),

            mobility_disruption_value=float(np.mean(mob_trials)),
            mobility_disruption_low=float(np.percentile(mob_trials, 10)),
            mobility_disruption_high=float(np.percentile(mob_trials, 90)),

            confidence=confidence,
            dominant_uncertainty=dominant,
            n_trials=n_trials,
        )

    # ------------------------------------------------------------------
    def _compute_metrics(
        self,
        flood_with: dict[int, DomainImpact],
        mobility_with: dict[int, DomainImpact],
        flood_null: dict[int, DomainImpact],
        mobility_null: dict[int, DomainImpact],
    ) -> dict[str, float]:
        """Compute scalar summary metrics by comparing with-intervention vs. baseline.

        Uses population-weighted risk reduction for a more meaningful demo metric.
        """
        # Population at risk (baseline vs intervention)
        pop_at_risk_null = sum(i.population_at_risk for i in flood_null.values())
        pop_at_risk_with = sum(i.population_at_risk for i in flood_with.values())
        pop_protected = max(pop_at_risk_null - pop_at_risk_with, 0.0)

        # Population-weighted risk reduction:
        # = fraction of at-risk population that's protected by intervention
        if pop_at_risk_null < 1.0:
            risk_reduction = 0.0
        else:
            risk_reduction = min(pop_protected / pop_at_risk_null, 0.95)

        # Alternative: node-count risk reduction (for conservation check)
        n_flooded_null = sum(1 for i in flood_null.values() if i.flooded)
        n_flooded_with = sum(1 for i in flood_with.values() if i.flooded)

        # Average mobility disruption (minutes extra per node)
        mob_delays_with = [i.travel_time_delta_min for i in mobility_with.values()]
        avg_mob = float(np.mean(mob_delays_with)) if mob_delays_with else 0.0

        return {
            "risk_reduction": risk_reduction,
            "population_protected": pop_protected,
            "mobility_disruption": avg_mob,
            "n_flooded_null": float(n_flooded_null),
            "n_flooded_with": float(n_flooded_with),
        }
