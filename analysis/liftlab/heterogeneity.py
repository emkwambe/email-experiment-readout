"""Heterogeneous treatment effects on revenue per customer (analysis-plan Section 8).

Four pre-specified dimensions x two email arms = 8 joint interaction tests, Holm-corrected.
Dimension 1 has three observed levels (Deviations, 2026-09-23). Segments are reported in a fixed
order and never ranked (CLAUDE.md rule 9).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from liftlab.checks import ARM_COLUMN, CONTROL_ARM, TREATMENT_ARMS
from liftlab.effects import ALPHA, CONFIDENCE_LEVEL, Z_975, holm

PRIOR_MERCHANDISE_LEVELS: dict[tuple[int, int], str] = {
    (1, 0): "mens only",
    (0, 1): "womens only",
    (1, 1): "mens and womens",
}

DIMENSIONS: list[dict[str, str]] = [
    {"id": "prior_merchandise", "label": "Prior merchandise purchase (mens x womens)"},
    {"id": "newbie", "label": "New customer"},
    {"id": "channel", "label": "Purchase channel"},
    {"id": "zip_code", "label": "Zip code class"},
]


def segment_labels(df: pd.DataFrame, dimension: str) -> pd.Series:
    """Segment label per row, using raw source levels (zip_code keeps "Surburban")."""
    if dimension == "prior_merchandise":
        pairs = list(zip(df["mens"].astype(int), df["womens"].astype(int)))
        unknown = set(pairs) - set(PRIOR_MERCHANDISE_LEVELS)
        if unknown:
            raise ValueError(f"mens x womens cells outside the three documented levels: {unknown}")
        return pd.Series([PRIOR_MERCHANDISE_LEVELS[p] for p in pairs], index=df.index)
    if dimension == "newbie":
        return df["newbie"].astype(int).map({0: "newbie=0", 1: "newbie=1"})
    return df[dimension].astype(object).astype(str)


def design(treated: np.ndarray, segments: pd.Series, levels: list[str]) -> tuple[np.ndarray, list[str]]:
    """Columns: const, T, segment dummies (levels[1:]), T x segment dummies. levels[0] is the reference."""
    dummies = np.column_stack([(segments == lv).to_numpy(dtype=float) for lv in levels[1:]])
    x = np.column_stack([np.ones(len(treated)), treated, dummies, dummies * treated[:, None]])
    names = ["const", "T"] + [f"seg[{lv}]" for lv in levels[1:]] + [f"T:seg[{lv}]" for lv in levels[1:]]
    return x, names


def wald_chi2(params: np.ndarray, cov: np.ndarray, idx: list[int]) -> dict[str, float]:
    b = params[idx]
    v = cov[np.ix_(idx, idx)]
    stat = float(b @ np.linalg.solve(v, b))
    return {"chi2": stat, "df": len(idx), "p_value": float(stats.chi2.sf(stat, len(idx)))}


def fit_dimension(df: pd.DataFrame, arm: str, dimension: str) -> dict[str, Any]:
    sub = df[df[ARM_COLUMN].astype(object).isin([arm, CONTROL_ARM])]
    treated = (sub[ARM_COLUMN].astype(object) == arm).to_numpy(dtype=float)
    segments = segment_labels(sub, dimension)
    levels = sorted(segments.unique())
    x, names = design(treated, segments, levels)
    fit = sm.OLS(sub["spend"].to_numpy(dtype=float), x).fit(cov_type="HC3")
    params, cov = np.asarray(fit.params), np.asarray(fit.cov_params())

    k = len(levels) - 1
    interaction_idx = list(range(2 + k, 2 + 2 * k))
    test = wald_chi2(params, cov, interaction_idx)

    rows = []
    for j, level in enumerate(levels):
        a = np.zeros(len(params))
        a[1] = 1.0
        if j > 0:
            a[2 + k + (j - 1)] = 1.0
        est = float(a @ params)
        se = float(np.sqrt(a @ cov @ a))  # full HC3 covariance, incl. the T / T:seg covariance term
        in_seg = (segments == level).to_numpy()
        rows.append({
            "segment": level,
            "n_email": int((in_seg & (treated == 1)).sum()),
            "n_control": int((in_seg & (treated == 0)).sum()),
            "estimate": est,
            "se": se,
            "ci_low": est - Z_975 * se,
            "ci_high": est + Z_975 * se,
        })
    return {
        "arm": arm,
        "comparison": CONTROL_ARM,
        "dimension": dimension,
        "reference_level": levels[0],
        "coefficients": names,
        "interaction_test": test,
        "segments": rows,
    }


def heterogeneity(df: pd.DataFrame) -> dict[str, Any]:
    tests = [fit_dimension(df, arm, d["id"]) for arm in TREATMENT_ARMS for d in DIMENSIONS]
    for t, p_adj in zip(tests, holm([t["interaction_test"]["p_value"] for t in tests])):
        t["interaction_test"]["p_holm"] = p_adj
        t["interaction_test"]["reject_holm"] = bool(p_adj < ALPHA)
    return {
        "metric": "revenue_per_customer",
        "model": "OLS spend ~ T + segment dummies + T x segment dummies, fitted on one email arm plus No E-Mail",
        "covariance": "HC3",
        "confidence_level": CONFIDENCE_LEVEL,
        "interaction_test": "joint Wald chi-square test of all T x segment terms",
        "segment_effect": "T + T x segment linear combination; 95% normal CI from the full HC3 covariance",
        "holm": "across all 8 interaction tests (4 dimensions x 2 email arms)",
        "alpha_familywise": ALPHA,
        "dimensions": DIMENSIONS,
        "n_tests": len(tests),
        "n_reject_holm": sum(t["interaction_test"]["reject_holm"] for t in tests),
        "tests": tests,
    }
