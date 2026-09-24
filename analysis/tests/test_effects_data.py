"""Independent verification of the Sprint 2 exports on the real data (Step 6)."""

from __future__ import annotations

import json
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.proportion import confint_proportions_2indep

from liftlab import effects, load
from liftlab.run import SPRINT2_FILES, WEB_DATA

ARMS = ["No E-Mail", "Mens E-Mail", "Womens E-Mail"]


@pytest.fixture(scope="module")
def s2() -> dict[str, Any]:
    missing = [n for n in SPRINT2_FILES if not (WEB_DATA / n).exists()]
    assert not missing, f"Run `python -m liftlab.run --stage sprint2` first; missing {missing}"
    return {n: json.loads((WEB_DATA / n).read_text(encoding="utf-8")) for n in SPRINT2_FILES}


@pytest.fixture(scope="module")
def sql() -> dict[str, dict[str, float]]:
    """Arm-level aggregates computed in DuckDB straight from the raw CSV, independent of pandas."""
    con = duckdb.connect()
    rows = con.execute(
        """
        SELECT segment,
               COUNT(*)::BIGINT          AS n,
               AVG(spend)                AS mean_spend,
               SUM(visit)::BIGINT        AS visits,
               SUM(conversion)::BIGINT   AS conversions,
               AVG(visit)                AS visit_rate,
               AVG(conversion)           AS conversion_rate
        FROM read_csv_auto(?, header = true)
        GROUP BY segment
        """,
        [str(load.RAW_CSV)],
    ).fetchall()
    cols = ["n", "mean_spend", "visits", "conversions", "visit_rate", "conversion_rate"]
    return {r[0]: dict(zip(cols, r[1:])) for r in rows}


def contrast(block: dict[str, Any], cid: str) -> dict[str, Any]:
    return next(c for c in block["contrasts"] if c["id"] == cid)


# ---------- DuckDB recomputation (tolerance 1e-9) ----------

def test_duckdb_arm_means_match(s2: dict[str, Any], sql: dict[str, dict[str, float]]) -> None:
    arms = s2["effects_primary.json"]["arms"]
    for a in ARMS:
        assert arms[a]["n"] == sql[a]["n"]
        assert arms[a]["mean"] == pytest.approx(sql[a]["mean_spend"], abs=1e-9)


def test_duckdb_h1_h2_differences_match(s2: dict[str, Any], sql: dict[str, dict[str, float]]) -> None:
    p = s2["effects_primary.json"]
    for cid, arm in [("H1", "Mens E-Mail"), ("H2", "Womens E-Mail")]:
        assert contrast(p, cid)["estimate"] == pytest.approx(sql[arm]["mean_spend"] - sql["No E-Mail"]["mean_spend"], abs=1e-9)


def test_duckdb_rates_match(s2: dict[str, Any], sql: dict[str, dict[str, float]]) -> None:
    m = s2["effects_secondary.json"]["metrics"]
    for a in ARMS:
        assert m["visit_rate"]["arms"][a]["rate"] == pytest.approx(sql[a]["visit_rate"], abs=1e-9)
        assert m["conversion_rate"]["arms"][a]["rate"] == pytest.approx(sql[a]["conversion_rate"], abs=1e-9)
        assert m["visit_rate"]["arms"][a]["events"] == sql[a]["visits"]
        assert m["conversion_rate"]["arms"][a]["events"] == sql[a]["conversions"]


# ---------- primary ----------

def test_primary_welch_matches_scipy_on_real_data(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    p = s2["effects_primary.json"]
    for c in p["contrasts"]:
        x = df.loc[df["segment"] == c["treatment"], "spend"].to_numpy()
        y = df.loc[df["segment"] == c["comparison"], "spend"].to_numpy()
        sp = stats.ttest_ind(x, y, equal_var=False)
        ci = sp.confidence_interval(0.95)
        assert c["welch_t"] == pytest.approx(sp.statistic, rel=1e-10)
        assert c["p_value"] == pytest.approx(sp.pvalue, rel=1e-8)
        assert c["ci_analytic"] == pytest.approx([ci.low, ci.high], rel=1e-10)


def test_primary_holm_family_and_agreement(s2: dict[str, Any]) -> None:
    p = s2["effects_primary.json"]
    h1, h2, h3 = (contrast(p, i) for i in ("H1", "H2", "H3"))
    assert [h1["p_holm"], h2["p_holm"]] == pytest.approx(effects.holm([h1["p_value"], h2["p_value"]]))
    assert h3["holm_family"] is False and h3["p_holm"] is None
    for c in (h1, h2, h3):
        ag = c["agreement"]
        assert ag["passed"] is True
        assert 0.8 <= ag["width_ratio"] <= 1.25
        assert ag["sign_analytic"] == ag["sign_bootstrap"]
        lo, hi = c["ci_bootstrap"]
        assert lo < c["estimate"] < hi
    assert p["bootstrap"] == {"resamples": 10_000, "seed": 20260923, "arm_order": ARMS,
                              "method": "percentile, resampling within arm"}


def test_bootstrap_ci_is_reproducible(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    fresh = effects.primary(df)
    assert [c["ci_bootstrap"] for c in fresh["contrasts"]] == [c["ci_bootstrap"] for c in s2["effects_primary.json"]["contrasts"]]


# ---------- secondary ----------

def test_secondary_newcombe_and_holm(s2: dict[str, Any]) -> None:
    for metric in ("visit_rate", "conversion_rate"):
        block = s2["effects_secondary.json"]["metrics"][metric]
        arms = block["arms"]
        for c in block["contrasts"]:
            t, k = arms[c["treatment"]], arms[c["comparison"]]
            lo, hi = confint_proportions_2indep(t["events"], t["n"], k["events"], k["n"], method="newcomb", compare="diff")
            assert c["ci_newcombe"] == pytest.approx([lo, hi], rel=1e-9)
        assert [c["p_holm"] for c in block["contrasts"]] == pytest.approx(effects.holm([c["p_value"] for c in block["contrasts"]]))
        assert [c["id"] for c in block["contrasts"]] == ["H1", "H2"]


def test_converter_spend_is_descriptive_only(s2: dict[str, Any]) -> None:
    d = s2["effects_secondary.json"]["spend_among_converters"]
    assert d["descriptive_only"] is True
    assert "post-treatment" in d["reason"]
    text = json.dumps(d).lower()
    assert "p_value" not in text and "ci_" not in text and "p_holm" not in text


# ---------- CUPED ----------

def test_cuped_theta_is_ols_slope_on_real_data(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    c = s2["cuped.json"]
    slope = sm.OLS(df["spend"].to_numpy(), sm.add_constant(df["history"].to_numpy())).fit().params[1]
    assert c["theta"] == pytest.approx(slope, rel=1e-9)
    assert c["primary_estimate"] == "unadjusted"
    for r in c["contrasts"]:
        assert r["unadjusted"]["primary"] is True and r["adjusted"]["primary"] is False
        assert r["sign_agrees"] is True
    assert c["all_signs_agree"] is True


def test_cuped_unadjusted_matches_primary(s2: dict[str, Any]) -> None:
    for r in s2["cuped.json"]["contrasts"]:
        p = contrast(s2["effects_primary.json"], r["id"])
        assert r["unadjusted"]["estimate"] == pytest.approx(p["estimate"], rel=1e-12)
        assert r["unadjusted"]["ci"] == pytest.approx(p["ci_analytic"], rel=1e-12)


def test_cuped_variance_reduction_bounded_by_within_arm_r2(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    for arm, v in s2["cuped.json"]["variance_by_arm"].items():
        g = df[df["segment"] == arm]
        r2 = np.corrcoef(g["spend"], g["history"])[0, 1] ** 2
        assert v["variance_reduction"] <= r2 + 1e-12


# ---------- heterogeneity ----------

def test_heterogeneity_eight_tests_with_holm(s2: dict[str, Any]) -> None:
    h = s2["heterogeneity.json"]
    assert h["n_tests"] == len(h["tests"]) == 8
    ps = [t["interaction_test"]["p_value"] for t in h["tests"]]
    assert [t["interaction_test"]["p_holm"] for t in h["tests"]] == pytest.approx(effects.holm(ps))
    assert h["n_reject_holm"] == sum(t["interaction_test"]["reject_holm"] for t in h["tests"])
    dfs = {t["dimension"]: t["interaction_test"]["df"] for t in h["tests"]}
    assert dfs == {"prior_merchandise": 2, "newbie": 1, "channel": 2, "zip_code": 2}


def test_segment_estimates_match_within_segment_means(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    from liftlab.heterogeneity import segment_labels
    for t in s2["heterogeneity.json"]["tests"]:
        sub = df[df["segment"].astype(object).isin([t["arm"], t["comparison"]])]
        labels = segment_labels(sub, t["dimension"])
        assert [r["segment"] for r in t["segments"]] == sorted(labels.unique())  # fixed order, never ranked
        n_total = 0
        for r in t["segments"]:
            seg = sub[labels == r["segment"]]
            email = seg.loc[seg["segment"] == t["arm"], "spend"]
            ctrl = seg.loc[seg["segment"] == t["comparison"], "spend"]
            assert (r["n_email"], r["n_control"]) == (len(email), len(ctrl))
            assert r["estimate"] == pytest.approx(email.mean() - ctrl.mean(), rel=1e-9)
            assert r["ci_low"] < r["estimate"] < r["ci_high"]
            n_total += len(email) + len(ctrl)
        assert n_total == len(sub)


def test_zip_code_segments_keep_source_spelling(s2: dict[str, Any]) -> None:
    zips = {r["segment"] for t in s2["heterogeneity.json"]["tests"] if t["dimension"] == "zip_code" for r in t["segments"]}
    assert zips == {"Rural", "Surburban", "Urban"}


def test_cuped_correlation_export(df: pd.DataFrame, s2: dict[str, Any]) -> None:
    corr = s2["cuped.json"]["correlation_spend_history"]
    assert corr["pooled"] == pytest.approx(np.corrcoef(df["spend"], df["history"])[0, 1], rel=1e-12)
    for arm, v in s2["cuped.json"]["variance_by_arm"].items():
        assert v["variance_reduction"] <= corr["by_arm"][arm] ** 2 + 1e-12
