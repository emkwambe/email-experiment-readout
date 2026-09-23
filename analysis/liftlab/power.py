"""Planning power calculations from arm sizes and ASSUMED parameters only.

No observed outcome enters any value here. Baseline rates and standard deviations are
assumed grids from the Sprint 1 spec, not properties of the data.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

ALPHA: float = 0.025  # per test, two-sided; conservative bound for Holm across H1 and H2
POWER: float = 0.80
BASIS: str = "assumed_parameters"
LABEL: str = "Planning values from assumed parameters, not observed outcomes."

ASSUMED_BASELINE_RATES: dict[str, list[float]] = {
    "conversion_rate": [0.005, 0.01, 0.02],
    "visit_rate": [0.10, 0.15, 0.20],
}
ASSUMED_REVENUE_SD: list[float] = [5.0, 10.0, 15.0, 20.0, 30.0]


def z_multiplier(alpha: float = ALPHA, power: float = POWER) -> float:
    """z_{1-alpha/2} + z_{power} for a two-sided test."""
    return float(stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power))


def mde_mean(sd: float, n_treat: int, n_ctrl: int, alpha: float = ALPHA, power: float = POWER) -> float:
    """Minimum detectable difference in means, normal approximation, common SD in both arms."""
    return z_multiplier(alpha, power) * sd * float(np.sqrt(1 / n_treat + 1 / n_ctrl))


def mde_proportion(p: float, n_treat: int, n_ctrl: int, alpha: float = ALPHA, power: float = POWER) -> float:
    """Minimum detectable absolute difference in proportions, baseline variance p(1-p) in both arms."""
    return mde_mean(float(np.sqrt(p * (1 - p))), n_treat, n_ctrl, alpha, power)


def power_grid(arm_sizes: dict[str, int], control: str, treatments: list[str]) -> dict[str, Any]:
    n_c = arm_sizes[control]
    proportions: list[dict[str, Any]] = []
    revenue: list[dict[str, Any]] = []
    for arm in treatments:
        n_t = arm_sizes[arm]
        contrast = f"{arm} vs {control}"
        for metric, rates in ASSUMED_BASELINE_RATES.items():
            for p in rates:
                mde = mde_proportion(p, n_t, n_c)
                proportions.append({
                    "basis": BASIS,
                    "contrast": contrast,
                    "n_treatment": n_t,
                    "n_control": n_c,
                    "metric": metric,
                    "assumed_baseline_rate": p,
                    "mde_absolute": mde,
                    "mde_relative": mde / p,
                })
        for sd in ASSUMED_REVENUE_SD:
            revenue.append({
                "basis": BASIS,
                "contrast": contrast,
                "n_treatment": n_t,
                "n_control": n_c,
                "metric": "revenue_per_customer",
                "assumed_sd_dollars": sd,
                "mde_dollars": mde_mean(sd, n_t, n_c),
            })
    return {
        "basis": BASIS,
        "label": LABEL,
        "alpha_per_test": ALPHA,
        "sides": 2,
        "power": POWER,
        "method": "Normal approximation; MDE = (z_{1-alpha/2} + z_power) * sd * sqrt(1/n_t + 1/n_c); proportions use sd = sqrt(p(1-p)) at the assumed baseline",
        "proportions": proportions,
        "revenue_per_customer": revenue,
    }
