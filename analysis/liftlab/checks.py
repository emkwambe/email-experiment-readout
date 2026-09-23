"""Data-quality gates from analysis-plan Section 5: integrity, sample ratio mismatch, balance.

Outcome columns are touched only for pooled consistency checks (outcome lock, CLAUDE.md rule 2).
Nothing in this module groups an outcome by arm.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

EXPECTED_ROWS: int = 64_000
ARM_COLUMN: str = "segment"
CONTROL_ARM: str = "No E-Mail"
TREATMENT_ARMS: list[str] = ["Mens E-Mail", "Womens E-Mail"]
ARMS: list[str] = TREATMENT_ARMS + [CONTROL_ARM]
SRM_HALT_P: float = 0.001
SMD_FLAG: float = 0.1

# Documented levels (analysis-plan Section 2; zip_code per the 2026-09-23 Deviations entry).
DOCUMENTED_LEVELS: dict[str, list[Any]] = {
    "segment": ["Mens E-Mail", "Womens E-Mail", "No E-Mail"],
    "history_segment": [
        "1) $0 - $100", "2) $100 - $200", "3) $200 - $350", "4) $350 - $500",
        "5) $500 - $750", "6) $750 - $1,000", "7) $1,000 +",
    ],
    "zip_code": ["Urban", "Surburban", "Rural"],
    "channel": ["Phone", "Web", "Multichannel"],
    "mens": [0, 1],
    "womens": [0, 1],
    "newbie": [0, 1],
    "visit": [0, 1],
    "conversion": [0, 1],
}

NUMERIC_COVARIATES: list[str] = ["recency", "history", "mens", "womens", "newbie"]
CATEGORICAL_COVARIATES: list[str] = ["history_segment", "zip_code", "channel"]


def _gate(violations: int) -> dict[str, Any]:
    return {"passed": bool(violations == 0), "violations": int(violations)}


def integrity(df: pd.DataFrame) -> dict[str, Any]:
    """Gate 1. Every check is pooled over all rows; none is split by arm."""
    gates: dict[str, dict[str, Any]] = {
        "row_count_is_64000": {"passed": bool(len(df) == EXPECTED_ROWS), "violations": int(abs(len(df) - EXPECTED_ROWS))},
        "no_nulls": _gate(int(df.isna().sum().sum())),
        "spend_nonnegative": _gate(int((df["spend"] < 0).sum())),
        "spend_positive_implies_conversion": _gate(int(((df["spend"] > 0) & (df["conversion"] != 1)).sum())),
        "conversion_implies_visit": _gate(int(((df["conversion"] == 1) & (df["visit"] != 1)).sum())),
    }
    for col, levels in DOCUMENTED_LEVELS.items():
        values = pd.Series(df[col].astype(object))
        gates[f"documented_levels_{col}"] = _gate(int((~values.isin(levels)).sum()))
    return {
        "passed": all(g["passed"] for g in gates.values()),
        "row_count": int(len(df)),
        "expected_row_count": EXPECTED_ROWS,
        "column_count": int(df.shape[1]),
        "gates": gates,
        "documented_levels": {k: [str(v) for v in vs] for k, vs in DOCUMENTED_LEVELS.items()},
    }


def srm_test(observed: dict[str, int]) -> dict[str, Any]:
    """Chi-square goodness of fit of arm counts against an equal split."""
    arms = list(observed)
    counts = np.array([observed[a] for a in arms], dtype=float)
    expected = np.full(len(arms), counts.sum() / len(arms))
    chi2, p = stats.chisquare(counts, expected)
    return {
        "observed": {a: int(observed[a]) for a in arms},
        "expected": {a: float(e) for a, e in zip(arms, expected)},
        "total": int(counts.sum()),
        "df": len(arms) - 1,
        "chi_square": float(chi2),
        "p_value": float(p),
        "halt_threshold": SRM_HALT_P,
        "halt": bool(p < SRM_HALT_P),
    }


def srm(df: pd.DataFrame) -> dict[str, Any]:
    """Gate 2 on the real data."""
    counts = df[ARM_COLUMN].astype(object).value_counts()
    return srm_test({a: int(counts.get(a, 0)) for a in ARMS})


def smd(treated: pd.Series, control: pd.Series) -> float:
    """Standardized mean difference: (mean_t - mean_c) / sqrt((var_t + var_c) / 2), sample variances."""
    t = treated.astype(float)
    c = control.astype(float)
    pooled = np.sqrt((t.var(ddof=1) + c.var(ddof=1)) / 2.0)
    diff = t.mean() - c.mean()
    if pooled == 0:
        return 0.0 if diff == 0 else float(np.sign(diff) * np.inf)
    return float(diff / pooled)


def covariate_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-period covariates, categoricals one-hot encoded as `column=level` (raw source levels)."""
    parts = [df[NUMERIC_COVARIATES].astype(float)]
    for col in CATEGORICAL_COVARIATES:
        values = df[col].astype(object)
        for level in sorted(values.unique()):
            parts.append((values == level).astype(float).rename(f"{col}={level}"))
    return pd.concat(parts, axis=1)


def balance(df: pd.DataFrame) -> dict[str, Any]:
    """Gate 3: SMD for every pre-period covariate, each email arm vs No E-Mail."""
    x = covariate_matrix(df)
    arm = df[ARM_COLUMN].astype(object)
    control = x[arm == CONTROL_ARM]
    rows: list[dict[str, Any]] = []
    for t_arm in TREATMENT_ARMS:
        treated = x[arm == t_arm]
        for cov in x.columns:
            value = smd(treated[cov], control[cov])
            rows.append({
                "arm": t_arm,
                "control": CONTROL_ARM,
                "covariate": cov,
                "smd": value,
                "abs_smd": abs(value),
                "flag": bool(abs(value) > SMD_FLAG),
            })
    flagged = [r for r in rows if r["flag"]]
    return {
        "flag_threshold": SMD_FLAG,
        "method": "SMD = (mean_treated - mean_control) / sqrt((var_treated + var_control) / 2), sample variances; categoricals one-hot",
        "n_covariates": int(x.shape[1]),
        "n_flagged": len(flagged),
        "max_abs_smd": max(r["abs_smd"] for r in rows),
        "rows": rows,
    }
