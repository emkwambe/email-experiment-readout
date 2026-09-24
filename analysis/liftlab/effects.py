"""Effect estimates for analysis-plan Sections 6 and 7 (primary, secondary, CUPED).

Method choices not fixed by the plan are recorded in its Deviations entry of 2026-09-23
("Sections 6-8 method clarifications"); the numbered comments below refer to that entry.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from liftlab import SEED
from liftlab.checks import ARM_COLUMN, CONTROL_ARM

ALPHA: float = 0.05
CONFIDENCE_LEVEL: float = 0.95
N_BOOT: int = 10_000
Z_975: float = float(stats.norm.ppf(0.975))
WIDTH_RATIO_BOUNDS: tuple[float, float] = (0.8, 1.25)

# Clarification 2: arms are resampled once, in this fixed order, from one generator.
BOOTSTRAP_ARM_ORDER: list[str] = ["No E-Mail", "Mens E-Mail", "Womens E-Mail"]

CONTRASTS: list[dict[str, Any]] = [
    {"id": "H1", "treatment": "Mens E-Mail", "comparison": CONTROL_ARM, "holm_family": True},
    {"id": "H2", "treatment": "Womens E-Mail", "comparison": CONTROL_ARM, "holm_family": True},
    {"id": "H3", "treatment": "Mens E-Mail", "comparison": "Womens E-Mail", "holm_family": False},
]
PRIMARY_CONTRASTS: list[dict[str, Any]] = [c for c in CONTRASTS if c["holm_family"]]

CONVERTER_SPEND_REASON: str = (
    "Spend among converters conditions on a post-treatment outcome (conversion), so the groups being "
    "compared are no longer randomized; any difference mixes the email's effect with who was induced "
    "to convert. Reported for context only; never used for inference or the recommendation."
)


# ---------- small pure building blocks ----------

def by_arm(df: pd.DataFrame, column: str) -> dict[str, np.ndarray]:
    arm = df[ARM_COLUMN].astype(object)
    return {a: df.loc[arm == a, column].to_numpy(dtype=float) for a in BOOTSTRAP_ARM_ORDER}


def mean_summary(x: np.ndarray) -> dict[str, Any]:
    n = len(x)
    m = float(x.mean())
    se = float(x.std(ddof=1) / np.sqrt(n))
    crit = float(stats.t.ppf(0.975, n - 1))
    return {"n": n, "mean": m, "se": se, "ci_low": m - crit * se, "ci_high": m + crit * se}


def welch(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Welch's t-test for mean(x) - mean(y) with the Welch-Satterthwaite df and a t-based 95% CI."""
    nx, ny = len(x), len(y)
    vx, vy = x.var(ddof=1) / nx, y.var(ddof=1) / ny
    diff = float(x.mean() - y.mean())
    se = float(np.sqrt(vx + vy))
    df = float((vx + vy) ** 2 / (vx**2 / (nx - 1) + vy**2 / (ny - 1)))
    t = diff / se
    p = float(2 * stats.t.sf(abs(t), df))
    crit = float(stats.t.ppf(0.975, df))
    return {"estimate": diff, "se": se, "t": float(t), "df": df, "p_value": p,
            "ci_low": diff - crit * se, "ci_high": diff + crit * se}


def bootstrap_means(x: np.ndarray, n_boot: int, rng: np.random.Generator, chunk: int = 250) -> np.ndarray:
    """Means of n_boot resamples of x (with replacement, same size as x)."""
    n = len(x)
    out = np.empty(n_boot)
    for start in range(0, n_boot, chunk):
        size = min(chunk, n_boot - start)
        idx = rng.integers(0, n, size=(size, n))
        out[start:start + size] = x[idx].mean(axis=1)
    return out


def percentile_ci(draws: np.ndarray) -> tuple[float, float]:
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return float(lo), float(hi)


def relative_lift(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Clarification 3: mean(x)/mean(y) - 1 with a delta-method SE and a normal 95% interval."""
    mx, my = float(x.mean()), float(y.mean())
    vmx, vmy = x.var(ddof=1) / len(x), y.var(ddof=1) / len(y)
    r = mx / my - 1
    se = float(np.sqrt(vmx / my**2 + mx**2 * vmy / my**4))
    return {"estimate": r, "se": se, "ci_low": r - Z_975 * se, "ci_high": r + Z_975 * se}


def sign_pattern(lo: float, hi: float) -> str:
    if lo > 0:
        return "above_zero"
    if hi < 0:
        return "below_zero"
    return "includes_zero"


def agreement(analytic: tuple[float, float], bootstrap: tuple[float, float]) -> dict[str, Any]:
    """Clarification 1: same sign pattern, and width ratio (bootstrap / analytic) within [0.8, 1.25]."""
    sa, sb = sign_pattern(*analytic), sign_pattern(*bootstrap)
    ratio = (bootstrap[1] - bootstrap[0]) / (analytic[1] - analytic[0])
    width_ok = WIDTH_RATIO_BOUNDS[0] <= ratio <= WIDTH_RATIO_BOUNDS[1]
    return {
        "sign_analytic": sa,
        "sign_bootstrap": sb,
        "sign_agrees": sa == sb,
        "width_ratio": float(ratio),
        "width_ratio_bounds": list(WIDTH_RATIO_BOUNDS),
        "width_ok": bool(width_ok),
        "passed": bool(sa == sb and width_ok),
    }


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values, returned in the input order."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return [float(a) for a in adjusted]


def wilson(x: int, n: int) -> tuple[float, float]:
    """Wilson score 95% interval, no continuity correction."""
    p = x / n
    denom = 1 + Z_975**2 / n
    center = (p + Z_975**2 / (2 * n)) / denom
    half = Z_975 * np.sqrt(p * (1 - p) / n + Z_975**2 / (4 * n**2)) / denom
    return float(center - half), float(center + half)


def newcombe(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Newcombe (1998) method 10 hybrid score interval for p1 - p2 (clarification 4)."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    lower = d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return float(lower), float(upper)


def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> dict[str, float]:
    """Two-sided z-test of p1 = p2 with the pooled SE (clarification 4)."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se = float(np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2)))
    z = (p1 - p2) / se
    return {"z": float(z), "p_value": float(2 * stats.norm.sf(abs(z)))}


# ---------- Section 6: primary ----------

def primary(df: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict[str, Any]:
    spend = by_arm(df, "spend")
    rng = np.random.default_rng(seed)
    boot = {a: bootstrap_means(spend[a], n_boot, rng) for a in BOOTSTRAP_ARM_ORDER}

    rows: list[dict[str, Any]] = []
    for c in CONTRASTS:
        x, y = spend[c["treatment"]], spend[c["comparison"]]
        w = welch(x, y)
        b_lo, b_hi = percentile_ci(boot[c["treatment"]] - boot[c["comparison"]])
        rows.append({
            "id": c["id"],
            "treatment": c["treatment"],
            "comparison": c["comparison"],
            "metric": "revenue_per_customer",
            "estimate": w["estimate"],
            "se": w["se"],
            "welch_t": w["t"],
            "welch_df": w["df"],
            "p_value": w["p_value"],
            "ci_analytic": [w["ci_low"], w["ci_high"]],
            "ci_bootstrap": [b_lo, b_hi],
            "agreement": agreement((w["ci_low"], w["ci_high"]), (b_lo, b_hi)),
            "relative_lift": relative_lift(x, y),
            "holm_family": c["holm_family"],
            "p_holm": None,
            "reject_holm": None,
        })

    family = [r for r in rows if r["holm_family"]]
    for r, p_adj in zip(family, holm([r["p_value"] for r in family])):
        r["p_holm"] = p_adj
        r["reject_holm"] = bool(p_adj < ALPHA)

    return {
        "metric": "revenue_per_customer",
        "definition": "Mean spend over all customers in the arm, including zeros",
        "confidence_level": CONFIDENCE_LEVEL,
        "alpha_familywise": ALPHA,
        "holm_family": [c["id"] for c in PRIMARY_CONTRASTS],
        "bootstrap": {"resamples": n_boot, "seed": seed, "arm_order": BOOTSTRAP_ARM_ORDER,
                      "method": "percentile, resampling within arm"},
        "arms": {a: mean_summary(spend[a]) for a in BOOTSTRAP_ARM_ORDER},
        "contrasts": rows,
        "all_agreement_passed": all(r["agreement"]["passed"] for r in rows),
    }


# ---------- Section 6: secondary ----------

def secondary(df: pd.DataFrame) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for metric, column in [("visit_rate", "visit"), ("conversion_rate", "conversion")]:
        values = by_arm(df, column)
        counts = {a: (int(v.sum()), len(v)) for a, v in values.items()}
        arms = {}
        for a, (x, n) in counts.items():
            lo, hi = wilson(x, n)
            arms[a] = {"n": n, "events": x, "rate": x / n, "ci_low": lo, "ci_high": hi}
        rows = []
        for c in PRIMARY_CONTRASTS:
            x1, n1 = counts[c["treatment"]]
            x2, n2 = counts[c["comparison"]]
            lo, hi = newcombe(x1, n1, x2, n2)
            z = two_proportion_z(x1, n1, x2, n2)
            rows.append({
                "id": c["id"], "treatment": c["treatment"], "comparison": c["comparison"],
                "estimate": x1 / n1 - x2 / n2, "ci_newcombe": [lo, hi],
                "z": z["z"], "p_value": z["p_value"],
            })
        for r, p_adj in zip(rows, holm([r["p_value"] for r in rows])):
            r["p_holm"] = p_adj
            r["reject_holm"] = bool(p_adj < ALPHA)
        metrics[metric] = {"arms": arms, "contrasts": rows}

    conv = df[df["conversion"] == 1]
    conv_spend = by_arm(conv, "spend")
    descriptive = {
        "descriptive_only": True,
        "reason": CONVERTER_SPEND_REASON,
        "arms": {a: {"n_converters": len(v), "mean_spend_among_converters": float(v.mean())}
                 for a, v in conv_spend.items()},
    }
    return {
        "confidence_level": CONFIDENCE_LEVEL,
        "alpha_familywise": ALPHA,
        "holm": "within each metric across H1 and H2",
        "interval": "Newcombe (1998) method 10 hybrid score interval; Wilson without continuity correction",
        "test": "two-proportion z-test, pooled standard error",
        "metrics": metrics,
        "spend_among_converters": descriptive,
    }


# ---------- Section 7: CUPED ----------

def cuped_theta(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))


def cuped(df: pd.DataFrame) -> dict[str, Any]:
    """Clarification 5: pooled theta, history centred at its pooled mean, H1 and H2 only."""
    y = df["spend"].to_numpy(dtype=float)
    x = df["history"].to_numpy(dtype=float)
    theta = cuped_theta(y, x)
    adjusted = df.assign(spend_cuped=y - theta * (x - x.mean()))
    raw = by_arm(adjusted, "spend")
    adj = by_arm(adjusted, "spend_cuped")

    variance = {a: {"var_unadjusted": float(raw[a].var(ddof=1)), "var_adjusted": float(adj[a].var(ddof=1)),
                    "variance_reduction": float(1 - adj[a].var(ddof=1) / raw[a].var(ddof=1))}
                for a in BOOTSTRAP_ARM_ORDER}
    rows = []
    for c in PRIMARY_CONTRASTS:
        u = welch(raw[c["treatment"]], raw[c["comparison"]])
        a = welch(adj[c["treatment"]], adj[c["comparison"]])
        rows.append({
            "id": c["id"], "treatment": c["treatment"], "comparison": c["comparison"],
            "unadjusted": {"primary": True, "estimate": u["estimate"], "se": u["se"], "p_value": u["p_value"],
                           "ci": [u["ci_low"], u["ci_high"]]},
            "adjusted": {"primary": False, "estimate": a["estimate"], "se": a["se"], "p_value": a["p_value"],
                         "ci": [a["ci_low"], a["ci_high"]]},
            "se_ratio_adjusted_to_unadjusted": a["se"] / u["se"],
            "sign_agrees": bool(np.sign(a["estimate"]) == np.sign(u["estimate"])),
        })
    hist = by_arm(adjusted, "history")
    return {
        "covariate": "history",
        "confidence_level": CONFIDENCE_LEVEL,
        "correlation_spend_history": {
            "pooled": float(np.corrcoef(y, x)[0, 1]),
            "by_arm": {a: float(np.corrcoef(raw[a], hist[a])[0, 1]) for a in BOOTSTRAP_ARM_ORDER},
        },
        "theta": theta,
        "theta_definition": "cov(spend, history) / var(history), pooled over all arms",
        "history_pooled_mean": float(x.mean()),
        "primary_estimate": "unadjusted",
        "interval": "Welch analytic 95% CI on the adjusted outcome",
        "variance_by_arm": variance,
        "contrasts": rows,
        "all_signs_agree": all(r["sign_agrees"] for r in rows),
    }
