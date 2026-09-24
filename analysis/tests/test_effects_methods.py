"""Method-level verification on synthetic data and published examples (Sprint 2, Step 6)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import confint_proportions_2indep, proportions_ztest
from statsmodels.stats.weightstats import CompareMeans, DescrStatsW

from liftlab import effects, heterogeneity


@pytest.fixture(scope="module")
def skewed() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    x = np.where(rng.random(3000) < 0.1, rng.lognormal(4, 1, 3000), 0.0)
    y = np.where(rng.random(2500) < 0.08, rng.lognormal(4, 1, 2500), 0.0)
    return x, y


def test_welch_matches_scipy_and_statsmodels(skewed: tuple[np.ndarray, np.ndarray]) -> None:
    x, y = skewed
    w = effects.welch(x, y)
    sp = stats.ttest_ind(x, y, equal_var=False)
    assert w["t"] == pytest.approx(sp.statistic, rel=1e-12)
    assert w["p_value"] == pytest.approx(sp.pvalue, rel=1e-10)
    assert w["df"] == pytest.approx(sp.df, rel=1e-12)
    ci = sp.confidence_interval(0.95)
    assert [w["ci_low"], w["ci_high"]] == pytest.approx([ci.low, ci.high], rel=1e-10)
    cm = CompareMeans(DescrStatsW(x), DescrStatsW(y))
    t_sm, p_sm, df_sm = cm.ttest_ind(usevar="unequal")
    assert (w["t"], w["p_value"], w["df"]) == pytest.approx((t_sm, p_sm, df_sm), rel=1e-10)
    assert [w["ci_low"], w["ci_high"]] == pytest.approx(list(cm.tconfint_diff(usevar="unequal")), rel=1e-10)


def test_newcombe_published_examples() -> None:
    # Newcombe (1998), Stat Med 17:873-890, Table II, method 10 (hybrid score, no CC).
    assert effects.newcombe(56, 70, 48, 80) == pytest.approx((0.0524, 0.3339), abs=5e-5)
    assert effects.newcombe(9, 10, 3, 10) == pytest.approx((0.1705, 0.8090), abs=5e-5)


def test_newcombe_matches_statsmodels() -> None:
    for x1, n1, x2, n2 in [(56, 70, 48, 80), (120, 21000, 95, 21300), (1500, 21000, 1300, 21300)]:
        lo, hi = confint_proportions_2indep(x1, n1, x2, n2, method="newcomb", compare="diff")
        assert effects.newcombe(x1, n1, x2, n2) == pytest.approx((lo, hi), rel=1e-9)


def test_wilson_matches_statsmodels() -> None:
    from statsmodels.stats.proportion import proportion_confint
    assert effects.wilson(56, 70) == pytest.approx(proportion_confint(56, 70, method="wilson"), rel=1e-12)


def test_two_proportion_z_matches_statsmodels() -> None:
    z = effects.two_proportion_z(1500, 21000, 1300, 21300)
    z_sm, p_sm = proportions_ztest([1500, 1300], [21000, 21300])
    assert (z["z"], z["p_value"]) == pytest.approx((z_sm, p_sm), rel=1e-10)


def test_holm_hand_computed() -> None:
    # p = (0.01, 0.04, 0.03), m = 3. Sorted: 0.01 -> 3*0.01 = 0.03; 0.03 -> 2*0.03 = 0.06;
    # 0.04 -> 1*0.04 = 0.04, but step-down monotonicity lifts it to 0.06.
    assert effects.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    # Two tests: (0.02, 0.5) -> (0.04, 0.5); capping at 1.
    assert effects.holm([0.02, 0.5]) == pytest.approx([0.04, 0.5])
    assert effects.holm([0.6, 0.7]) == pytest.approx([1.0, 1.0])


def test_holm_matches_statsmodels() -> None:
    p = [0.001, 0.2, 0.013, 0.04, 0.5, 0.007, 0.3, 0.06]
    assert effects.holm(p) == pytest.approx(list(multipletests(p, method="holm")[1]))


def test_bootstrap_covers_known_difference() -> None:
    # Known true difference 0.5 between two normal populations; the 95% percentile CI should cover it,
    # and across 40 independent replications it should do so about 95% of the time.
    covered = 0
    rng = np.random.default_rng(20260923)
    for _ in range(40):
        x = rng.normal(10.5, 2.0, 400)
        y = rng.normal(10.0, 2.0, 400)
        lo, hi = effects.percentile_ci(effects.bootstrap_means(x, 2000, rng) - effects.bootstrap_means(y, 2000, rng))
        covered += lo <= 0.5 <= hi
    assert covered >= 34  # P(Binomial(40, 0.95) < 34) is about 0.2%


def test_bootstrap_is_reproducible() -> None:
    x = np.arange(100, dtype=float)
    a = effects.bootstrap_means(x, 500, np.random.default_rng(1))
    b = effects.bootstrap_means(x, 500, np.random.default_rng(1))
    assert np.array_equal(a, b)
    assert a.mean() == pytest.approx(x.mean(), abs=1.0)


def test_relative_lift_delta_method_matches_numeric_gradient(skewed: tuple[np.ndarray, np.ndarray]) -> None:
    x, y = skewed
    r = effects.relative_lift(x, y)
    mx, my = x.mean(), y.mean()
    grad = np.array([1 / my, -mx / my**2])
    cov = np.diag([x.var(ddof=1) / len(x), y.var(ddof=1) / len(y)])
    assert r["estimate"] == pytest.approx(mx / my - 1)
    assert r["se"] == pytest.approx(float(np.sqrt(grad @ cov @ grad)), rel=1e-12)


def test_agreement_rules() -> None:
    assert effects.agreement((0.1, 0.5), (0.12, 0.52))["passed"] is True
    assert effects.agreement((-0.1, 0.5), (0.02, 0.62))["sign_agrees"] is False
    assert effects.agreement((0.1, 0.5), (0.1, 0.65))["width_ok"] is False  # ratio 1.375


def test_cuped_theta_equals_ols_slope(skewed: tuple[np.ndarray, np.ndarray]) -> None:
    rng = np.random.default_rng(3)
    h = rng.gamma(2.0, 100.0, 5000)
    s = 0.02 * h + rng.normal(0, 5, 5000)
    slope = sm.OLS(s, sm.add_constant(h)).fit().params[1]
    assert effects.cuped_theta(s, h) == pytest.approx(slope, rel=1e-10)


def test_segment_effects_equal_within_segment_differences() -> None:
    # The saturated interaction model's segment effect must equal the within-segment difference in means,
    # and the joint Wald statistic must match statsmodels' own wald_test.
    rng = np.random.default_rng(11)
    n = 4000
    frame = pd.DataFrame({
        "segment": rng.choice(["Mens E-Mail", "No E-Mail"], n),
        "channel": rng.choice(["Phone", "Web", "Multichannel"], n),
    })
    effect = frame["channel"].map({"Phone": 0.0, "Web": 1.0, "Multichannel": 2.0})
    frame["spend"] = rng.normal(5, 3, n) + (frame["segment"] == "Mens E-Mail") * effect
    out = heterogeneity.fit_dimension(frame, "Mens E-Mail", "channel")
    for row in out["segments"]:
        seg = frame[frame["channel"] == row["segment"]]
        diff = seg.loc[seg["segment"] == "Mens E-Mail", "spend"].mean() - seg.loc[seg["segment"] == "No E-Mail", "spend"].mean()
        assert row["estimate"] == pytest.approx(diff, rel=1e-9)
    treated = (frame["segment"] == "Mens E-Mail").to_numpy(dtype=float)
    x, _ = heterogeneity.design(treated, frame["channel"], sorted(frame["channel"].unique()))
    fit = sm.OLS(frame["spend"].to_numpy(), x).fit(cov_type="HC3")
    r = np.zeros((2, x.shape[1]))
    r[0, 4], r[1, 5] = 1, 1
    wt = fit.wald_test(r, use_f=False, scalar=True)
    assert out["interaction_test"]["chi2"] == pytest.approx(float(wt.statistic), rel=1e-9)
    assert out["interaction_test"]["p_value"] == pytest.approx(float(wt.pvalue), rel=1e-9)


def test_segment_ci_uses_covariance_term() -> None:
    # Clarification 6: the segment SE must include 2*cov(T, T:seg); check against t_test on the same contrast.
    rng = np.random.default_rng(5)
    n = 3000
    frame = pd.DataFrame({"segment": rng.choice(["Womens E-Mail", "No E-Mail"], n), "newbie": rng.integers(0, 2, n)})
    frame["spend"] = rng.exponential(3, n)
    out = heterogeneity.fit_dimension(frame, "Womens E-Mail", "newbie")
    treated = (frame["segment"] == "Womens E-Mail").to_numpy(dtype=float)
    seg = heterogeneity.segment_labels(frame, "newbie")
    x, _ = heterogeneity.design(treated, seg, sorted(seg.unique()))
    fit = sm.OLS(frame["spend"].to_numpy(), x).fit(cov_type="HC3")
    tt = fit.t_test(np.array([[0, 1, 0, 1]]))
    row = out["segments"][1]
    assert row["estimate"] == pytest.approx(float(tt.effect[0]), rel=1e-12)
    assert row["se"] == pytest.approx(float(tt.sd[0, 0]), rel=1e-12)
    cov = np.asarray(fit.cov_params())
    assert abs(cov[1, 3]) > 0  # the covariance term is non-trivial, so omitting it would change the SE
