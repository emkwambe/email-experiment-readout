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
    # Treated mean 0.5, var 1/3; control mean 0.25, var 1/4.
    # SMD = 0.25 / sqrt((1/3 + 1/4) / 2) = 0.25 * sqrt(24 / 7).
    got = checks.smd(pd.Series([0, 0, 1, 1]), pd.Series([0, 0, 0, 1]))
    assert got == pytest.approx(0.25 * math.sqrt(24 / 7))


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
    assert bal["n_flagged"] == sum(r["flag"] for r in bal["rows"])
    fresh = checks.balance(df)
    assert [r["smd"] for r in bal["rows"]] == pytest.approx([r["smd"] for r in fresh["rows"]], rel=1e-12)
