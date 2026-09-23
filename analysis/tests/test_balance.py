from __future__ import annotations

import math
from typing import Any

import pandas as pd
import pytest

from liftlab import checks


def test_smd_known_answer_unit_variance() -> None:
    # Both groups have sample variance 1; means differ by -1, so SMD = -1.
    assert checks.smd(pd.Series([1, 2, 3]), pd.Series([2, 3, 4])) == pytest.approx(-1.0)


def test_smd_known_answer_binary() -> None:
    # Binary form: p_t = 0.5, p_t(1-p_t) = 0.25; p_c = 0.25, p_c(1-p_c) = 0.1875.
    # SMD = 0.25 / sqrt((0.25 + 0.1875) / 2) = 0.25 / sqrt(7/32) = 0.534522...
    got = checks.smd(pd.Series([0, 0, 1, 1]), pd.Series([0, 0, 0, 1]), binary=True)
    assert got == pytest.approx(0.25 / math.sqrt(7 / 32))
    assert got == pytest.approx(0.5345224838, abs=1e-9)


def test_smd_continuous_uses_sample_variance() -> None:
    # Same data treated as continuous: sample variances 1/3 and 1/4, so SMD = 0.25 * sqrt(24 / 7).
    got = checks.smd(pd.Series([0, 0, 1, 1]), pd.Series([0, 0, 0, 1]))
    assert got == pytest.approx(0.25 * math.sqrt(24 / 7))


def test_covariate_types() -> None:
    assert not checks.is_binary_covariate("recency")
    assert not checks.is_binary_covariate("history")
    for name in ["mens", "womens", "newbie", "zip_code=Surburban", "channel=Web", "history_segment=1) $0 - $100"]:
        assert checks.is_binary_covariate(name)


def test_smd_zero_variance() -> None:
    assert checks.smd(pd.Series([1, 1]), pd.Series([1, 1])) == 0.0


def test_balance_covers_every_covariate_for_both_arms(df: pd.DataFrame, exports: dict[str, Any]) -> None:
    bal = exports["balance.json"]
    n_cov = checks.covariate_matrix(df).shape[1]
    assert bal["n_covariates"] == n_cov
    assert len(bal["rows"]) == 2 * n_cov
    assert {r["arm"] for r in bal["rows"]} == set(checks.TREATMENT_ARMS)
    for r in bal["rows"]:
        assert r["flag"] is (abs(r["smd"]) > 0.1)
        assert r["type"] == ("binary" if checks.is_binary_covariate(r["covariate"]) else "continuous")
    assert bal["n_flagged"] == sum(r["flag"] for r in bal["rows"])
    fresh = checks.balance(df)
    assert [r["smd"] for r in bal["rows"]] == pytest.approx([r["smd"] for r in fresh["rows"]], rel=1e-12)
