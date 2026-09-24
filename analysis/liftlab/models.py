"""Training-split targeting work (analysis-plan Deviations 2026-09-24, 1a-1b): uplift models, P3 and P4
selection by cross-validation, and the policy definitions. Reads training rows only, via SplitData.train().
"""

from __future__ import annotations

import itertools
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import KFold

from liftlab import SEED
from liftlab.checks import ARM_COLUMN, CONTROL_ARM
from liftlab.heterogeneity import DIMENSIONS, segment_labels

MENS, WOMENS, NONE = "Mens E-Mail", "Womens E-Mail", CONTROL_ARM
EMAIL_ARMS: list[str] = [MENS, WOMENS]
MODEL_ARMS: list[str] = [MENS, WOMENS, NONE]
ACTIONS: list[str] = [MENS, WOMENS, NONE]  # a policy's action "No E-Mail" means: send nothing
DEFAULT_COST: float = 0.10
N_FOLDS: int = 5
NOMINAL_P: float = 1 / 3
K_GRID: list[int] = list(range(10, 101, 10))
FEATURES: list[str] = ["recency", "history", "mens", "womens", "zip_code", "newbie", "channel"]
CATEGORICAL: list[str] = ["zip_code", "channel"]
PARAM_GRID: list[dict[str, Any]] = [
    {"max_depth": d, "learning_rate": lr, "max_iter": it, "min_samples_leaf": leaf}
    for d, lr, it, leaf in itertools.product([3, 5], [0.05, 0.1], [100, 300], [50, 200])
]
FIXED_PARAMS: dict[str, Any] = {"early_stopping": False, "categorical_features": "from_dtype", "random_state": SEED}
QINI_POINTS: int = 100


# ---------- features and models ----------

def features(df: pd.DataFrame) -> pd.DataFrame:
    x = df[FEATURES].copy()
    for c in CATEGORICAL:
        x[c] = x[c].astype("category")
    for c in ["recency", "mens", "womens", "newbie"]:
        x[c] = x[c].astype(float)
    return x


def make_model(params: dict[str, Any]) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(**params, **FIXED_PARAMS)


def kfold() -> KFold:
    return KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)


def tune(x: pd.DataFrame, y: np.ndarray) -> dict[str, Any]:
    """5-fold CV MSE over PARAM_GRID; lowest mean wins, ties to grid order."""
    rows = []
    for params in PARAM_GRID:
        mses = []
        for tr, va in kfold().split(x):
            m = make_model(params).fit(x.iloc[tr], y[tr])
            mses.append(float(np.mean((m.predict(x.iloc[va]) - y[va]) ** 2)))
        rows.append({**params, "cv_mse_mean": float(np.mean(mses)), "cv_mse_folds": mses})
    best = min(range(len(rows)), key=lambda i: (rows[i]["cv_mse_mean"], i))
    return {"chosen": PARAM_GRID[best], "cv_mse": rows[best]["cv_mse_mean"], "grid": rows}


def fit_arm_models(train: pd.DataFrame, params: dict[str, dict[str, Any]]) -> dict[str, HistGradientBoostingRegressor]:
    arm = train[ARM_COLUMN].astype(object)
    return {a: make_model(params[a]).fit(features(train[arm == a]), train.loc[arm == a, "spend"].to_numpy(float))
            for a in MODEL_ARMS}


def predict_uplift(models: dict[str, HistGradientBoostingRegressor], df: pd.DataFrame) -> pd.DataFrame:
    x = features(df)
    base = models[NONE].predict(x)
    return pd.DataFrame({MENS: models[MENS].predict(x) - base, WOMENS: models[WOMENS].predict(x) - base}, index=df.index)


def oof_uplift(train: pd.DataFrame, params: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, np.ndarray]:
    """Out-of-fold predicted uplift for every training customer, plus the fold id of each row."""
    fold = np.empty(len(train), dtype=int)
    parts = []
    for f, (tr, va) in enumerate(kfold().split(train)):
        fold[va] = f
        parts.append(predict_uplift(fit_arm_models(train.iloc[tr], params), train.iloc[va]))
    return pd.concat(parts).loc[train.index], fold


# ---------- policy value (1c estimator, used here within training folds) ----------

def ipw_net_value(df: pd.DataFrame, action: np.ndarray, cost: float) -> float:
    """Nominal-1/3 IPW net value per customer: mean(spend * 1{T = action} / (1/3)) - cost * share sent."""
    t = df[ARM_COLUMN].astype(object).to_numpy()
    y = df["spend"].to_numpy(float)
    value = float(np.mean(y * (t == action) / NOMINAL_P))
    return value - cost * float(np.mean(action != NONE))


# ---------- policies ----------

def blanket(n: int, a: str) -> np.ndarray:
    return np.full(n, a, dtype=object)


def top_k(uplift: np.ndarray, k: int, arm: str) -> np.ndarray:
    """Send `arm` to the top k% by predicted uplift (ties broken by position), None to the rest."""
    n = len(uplift)
    order = np.argsort(-uplift, kind="stable")
    action = np.full(n, NONE, dtype=object)
    action[order[: int(round(n * k / 100))]] = arm
    return action


def uplift_assignment(uplift: pd.DataFrame, cost: float) -> np.ndarray:
    """P5: the action with the highest predicted net uplift, or None if both are <= 0."""
    net_m = uplift[MENS].to_numpy() - cost
    net_w = uplift[WOMENS].to_numpy() - cost
    action = np.where(net_m >= net_w, MENS, WOMENS).astype(object)
    action[np.maximum(net_m, net_w) <= 0] = NONE
    return action


def segment_rule(train: pd.DataFrame, dimension: str, cost: float) -> dict[str, Any]:
    """P3 candidate: per level, the action with the highest training-estimated net revenue (None = 0)."""
    labels = segment_labels(train, dimension)
    arm = train[ARM_COLUMN].astype(object)
    rule, values = {}, {}
    for level in sorted(labels.unique()):
        in_level = labels == level
        base = train.loc[in_level & (arm == NONE), "spend"].mean()
        net = {a: float(train.loc[in_level & (arm == a), "spend"].mean() - base - cost) for a in EMAIL_ARMS}
        net[NONE] = 0.0
        best = max(ACTIONS, key=lambda a: (net[a], -ACTIONS.index(a)))
        rule[level], values[level] = best, net
    return {"dimension": dimension, "rule": rule, "training_net_value": values}


def apply_segment_rule(df: pd.DataFrame, rule: dict[str, Any]) -> np.ndarray:
    labels = segment_labels(df, rule["dimension"])
    return labels.map(rule["rule"]).fillna(NONE).to_numpy(dtype=object)


# ---------- Qini ----------

def qini(uplift: np.ndarray, treated: np.ndarray, spend: np.ndarray, points: int = QINI_POINTS) -> dict[str, Any]:
    """Qini curve with cumulative within-top-phi counts; coefficient = area between Q and the random line
    from (0,0) to (1,Q(1)) (trapezoid over phi = 0, 1/points, ..., 1), divided by the population size."""
    order = np.argsort(-uplift, kind="stable")
    t = treated[order].astype(bool)
    y = spend[order]
    rt, rc = np.cumsum(y * t), np.cumsum(y * ~t)
    nt, nc = np.cumsum(t), np.cumsum(~t)
    n = len(y)
    phis = np.linspace(0, 1, points + 1)
    q = [0.0]
    for phi in phis[1:]:
        m = max(1, int(round(phi * n))) - 1
        q.append(float(rt[m] - (rc[m] * nt[m] / nc[m] if nc[m] > 0 else 0.0)))
    q_arr = np.array(q)
    gap = q_arr - phis * q_arr[-1]
    area = float(np.sum((gap[1:] + gap[:-1]) / 2) / points)
    return {"phi": phis.tolist(), "q": q_arr.tolist(), "coefficient": area / n, "n": int(n)}


def qini_for_arm(df: pd.DataFrame, uplift: pd.Series, arm: str) -> dict[str, Any]:
    a = df[ARM_COLUMN].astype(object)
    mask = (a == arm) | (a == NONE)
    return qini(uplift[mask].to_numpy(), (a[mask] == arm).to_numpy(), df.loc[mask, "spend"].to_numpy(float))


# ---------- training-split selection ----------

def cv_select(train: pd.DataFrame, fold: np.ndarray, oof: pd.DataFrame, cost: float) -> dict[str, Any]:
    """P3 dimension and P4 k per arm, each chosen by mean 5-fold CV net value (1c estimator) on training."""
    def cv(build: Callable[[pd.DataFrame, pd.DataFrame, pd.DataFrame], np.ndarray]) -> list[float]:
        out = []
        for f in range(N_FOLDS):
            fit_rows, score_rows = train[fold != f], train[fold == f]
            out.append(ipw_net_value(score_rows, build(fit_rows, score_rows, oof[fold == f]), cost))
        return out

    p3 = []
    for d in DIMENSIONS:
        folds = cv(lambda fit, score, _u, dim=d["id"]: apply_segment_rule(score, segment_rule(fit, dim, cost)))
        p3.append({"dimension": d["id"], "cv_net_value_folds": folds, "cv_net_value_mean": float(np.mean(folds))})
    best_d = max(range(len(p3)), key=lambda i: (p3[i]["cv_net_value_mean"], -i))

    p4: dict[str, Any] = {}
    for arm in EMAIL_ARMS:
        rows = []
        for k in K_GRID:
            folds = cv(lambda _fit, _score, u, kk=k, aa=arm: top_k(u[aa].to_numpy(), kk, aa))
            rows.append({"k": k, "cv_net_value_folds": folds, "cv_net_value_mean": float(np.mean(folds))})
        best_k = max(range(len(rows)), key=lambda i: (rows[i]["cv_net_value_mean"], -i))
        p4[arm] = {"chosen_k": rows[best_k]["k"], "by_k": rows}

    return {
        "p3_candidates": p3,
        "p3_selected_dimension": p3[best_d]["dimension"],
        "p3_rule": segment_rule(train, p3[best_d]["dimension"], cost),
        "p4": p4,
    }


def train_all(train: pd.DataFrame, cost: float = DEFAULT_COST) -> dict[str, Any]:
    """All Step 3 work on the training split. Returns the exportable summary and fitted objects."""
    arm = train[ARM_COLUMN].astype(object)
    tuning = {a: tune(features(train[arm == a]), train.loc[arm == a, "spend"].to_numpy(float)) for a in MODEL_ARMS}
    params = {a: tuning[a]["chosen"] for a in MODEL_ARMS}
    oof, fold = oof_uplift(train, params)
    selection = cv_select(train, fold, oof, cost)
    p5 = uplift_assignment(oof, cost)
    summary = {
        "cost": cost,
        "n_train": int(len(train)),
        "features": FEATURES,
        "categorical_features": CATEGORICAL,
        "fixed_model_params": {k: v for k, v in FIXED_PARAMS.items()},
        "fixed_model_params_note": "early_stopping=False so max_iter is the number of boosting iterations the grid declares",
        "folds": {"n_splits": N_FOLDS, "shuffle": True, "seed": SEED},
        "tuning": tuning,
        "oof_qini": {a: qini_for_arm(train, oof[a], a) for a in EMAIL_ARMS},
        "oof_note": "Out-of-fold diagnostics use hyperparameters tuned on the same training data, so they are mildly optimistic.",
        "selection": selection,
        "p5_training_oof_action_share": {a: float(np.mean(p5 == a)) for a in ACTIONS},
    }
    return {"summary": summary, "params": params}
