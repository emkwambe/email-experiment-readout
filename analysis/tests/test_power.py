from __future__ import annotations

import math
from typing import Any

import pytest
from statsmodels.stats.power import NormalIndPower

from liftlab import power


def _statsmodels_mde(sd: float, n_t: int, n_c: int) -> float:
    """Independent MDE: solve the standardized effect with statsmodels, then scale by sd."""
    d = NormalIndPower().solve_power(
        effect_size=None, nobs1=n_t, alpha=power.ALPHA, power=power.POWER,
        ratio=n_c / n_t, alternative="two-sided",
    )
    return float(d) * sd


@pytest.mark.parametrize("sd", power.ASSUMED_REVENUE_SD)
def test_revenue_mde_matches_statsmodels(sd: float) -> None:
    assert power.mde_mean(sd, 21_300, 21_300) == pytest.approx(_statsmodels_mde(sd, 21_300, 21_300), rel=1e-4)


@pytest.mark.parametrize("p", [0.005, 0.01, 0.02, 0.10, 0.15, 0.20])
def test_proportion_mde_matches_statsmodels(p: float) -> None:
    sd = math.sqrt(p * (1 - p))
    assert power.mde_proportion(p, 21_000, 22_000) == pytest.approx(_statsmodels_mde(sd, 21_000, 22_000), rel=1e-4)


def test_exported_power_grid_recomputes(exports: dict[str, Any]) -> None:
    pw = exports["power.json"]
    assert pw["basis"] == "assumed_parameters"
    assert pw["alpha_per_test"] == 0.025 and pw["power"] == 0.80
    assert len(pw["proportions"]) == 2 * 6
    assert len(pw["revenue_per_customer"]) == 2 * 5
    for r in pw["proportions"]:
        assert r["basis"] == "assumed_parameters"
        p = r["assumed_baseline_rate"]
        expected = _statsmodels_mde(math.sqrt(p * (1 - p)), r["n_treatment"], r["n_control"])
        assert r["mde_absolute"] == pytest.approx(expected, rel=1e-4)
    for r in pw["revenue_per_customer"]:
        assert r["basis"] == "assumed_parameters"
        expected = _statsmodels_mde(r["assumed_sd_dollars"], r["n_treatment"], r["n_control"])
        assert r["mde_dollars"] == pytest.approx(expected, rel=1e-4)


def test_power_uses_arm_sizes_from_srm(exports: dict[str, Any]) -> None:
    observed = exports["srm.json"]["observed"]
    for r in exports["power.json"]["proportions"] + exports["power.json"]["revenue_per_customer"]:
        arm, control = r["contrast"].split(" vs ")
        assert r["n_treatment"] == observed[arm] and r["n_control"] == observed[control]
