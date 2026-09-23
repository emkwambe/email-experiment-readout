from __future__ import annotations

import math
from typing import Any

import pandas as pd
import pytest

from liftlab import checks


def test_srm_hand_constructed_example() -> None:
    # Observed 10, 20, 30 vs expected 20 each: chi2 = (100 + 0 + 100) / 20 = 10.
    # With 2 df the chi-square survival function is exp(-x / 2), so p = exp(-5).
    result = checks.srm_test({"A": 10, "B": 20, "C": 30})
    assert result["chi_square"] == pytest.approx(10.0)
    assert result["p_value"] == pytest.approx(math.exp(-5))
    assert result["df"] == 2
    assert result["expected"] == {"A": 20.0, "B": 20.0, "C": 20.0}
    assert result["halt"] is False  # 0.0067 >= 0.001


def test_srm_halts_below_threshold() -> None:
    result = checks.srm_test({"A": 100, "B": 200, "C": 300})
    assert result["p_value"] < 0.001
    assert result["halt"] is True


def test_srm_exact_split_is_zero() -> None:
    result = checks.srm_test({"A": 50, "B": 50, "C": 50})
    assert result["chi_square"] == pytest.approx(0.0)
    assert result["p_value"] == pytest.approx(1.0)


def test_real_srm_is_well_formed(df: pd.DataFrame, exports: dict[str, Any]) -> None:
    srm = exports["srm.json"]
    assert set(srm["observed"]) == set(checks.ARMS)
    assert srm["total"] == 64_000 == sum(srm["observed"].values())
    assert all(v == pytest.approx(64_000 / 3) for v in srm["expected"].values())
    assert isinstance(srm["p_value"], float) and 0.0 <= srm["p_value"] <= 1.0
    assert srm["chi_square"] >= 0.0
    assert srm["halt"] is (srm["p_value"] < 0.001)
    fresh = checks.srm(df)
    assert srm["p_value"] == pytest.approx(fresh["p_value"], rel=1e-12)
    assert srm["observed"] == fresh["observed"]
