"""Single-use holdout evaluation (analysis-plan Deviations 2026-09-24, 1c-1d, 1g).

This is the only module allowed to read holdout rows. `python -m liftlab.evaluate` runs the evaluation once
and writes web/public/data/targeting.json; it refuses to run if that file already exists or the working
tree is dirty. `--verify` recomputes the evaluation without writing and checks it matches the committed file.
Models are refit on the training split with the committed training.json choices; nothing is re-tuned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from liftlab import SEED, load, models, run, split
from liftlab.checks import ARM_COLUMN

MENS, WOMENS, NONE = models.MENS, models.WOMENS, models.NONE
N_BOOT: int = 2000
COST_GRID: list[float] = [round(0.01 * i, 2) for i in range(1, 51)]
POLICIES: list[str] = ["P0", "P1", "P2", "P3", "P4a", "P4b", "P5"]  # order also breaks ties in 1d
BLANKET: list[str] = ["P1", "P2"]
TARGETED: list[str] = ["P3", "P4a", "P4b", "P5"]
TARGETING_JSON = run.WEB_DATA / "targeting.json"
TRAINING_JSON = run.WEB_DATA / "training.json"


# ---------- pure estimators (tested on synthetic data) ----------

def contributions(arm: np.ndarray, spend: np.ndarray, action: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row IPW contribution spend * 1{T = action} / (1/3), and the per-row send indicator."""
    return spend * (arm == action) / models.NOMINAL_P, (action != NONE).astype(float)


def hajek_value(arm: np.ndarray, spend: np.ndarray, action: np.ndarray, weights: np.ndarray | None = None) -> float:
    """Self-normalized value: sum over arms a of (1/n_a) * sum_{T=a, action=a} spend (weights = bootstrap counts)."""
    w = np.ones(len(arm)) if weights is None else weights
    total = 0.0
    for a in models.ACTIONS:
        in_a = arm == a
        n_a = float(np.sum(w * in_a))
        total += float(np.sum(w * in_a * (action == a) * spend)) / n_a
    return total


def bootstrap_weights(n: int, n_boot: int, rng: np.random.Generator, chunk: int = 200):
    """Yield (chunk_size, n) matrices of resample counts: each row is one bootstrap resample of the rows."""
    for start in range(0, n_boot, chunk):
        size = min(chunk, n_boot - start)
        idx = rng.integers(0, n, size=(size, n))
        w = np.zeros((size, n), dtype=np.float64)
        for r in range(size):
            w[r] = np.bincount(idx[r], minlength=n)
        yield w


def ci(draws: np.ndarray) -> list[float]:
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return [float(lo), float(hi)]


def policy_table(arm: np.ndarray, spend: np.ndarray, actions: dict[str, np.ndarray], cost: float,
                 n_boot: int, seed: int) -> dict[str, Any]:
    """Point values and paired bootstrap draws for every policy in `actions` (all on the same resamples)."""
    names = list(actions)
    contrib = np.column_stack([contributions(arm, spend, actions[p])[0] for p in names])
    sent = np.column_stack([contributions(arm, spend, actions[p])[1] for p in names])
    # Hajek pieces: per arm a, numerator columns spend * 1{T=a, action=a} and the arm indicator.
    in_arm = np.column_stack([(arm == a).astype(float) for a in models.ACTIONS])
    hajek_num = {a: np.column_stack([spend * (arm == a) * (actions[p] == a) for p in names]) for a in models.ACTIONS}
    n = len(arm)
    point_v = contrib.mean(axis=0)
    point_share = sent.mean(axis=0)
    draws_v, draws_share, draws_h = [], [], []
    rng = np.random.default_rng(seed)
    for w in bootstrap_weights(n, n_boot, rng):
        draws_v.append(w @ contrib / n)
        draws_share.append(w @ sent / n)
        counts = w @ in_arm
        draws_h.append(sum((w @ hajek_num[a]) / counts[:, [j]] for j, a in enumerate(models.ACTIONS)))
    dv, ds, dh = np.vstack(draws_v), np.vstack(draws_share), np.vstack(draws_h)
    return {
        "names": names,
        "value": dict(zip(names, point_v)),
        "share_sent": dict(zip(names, point_share)),
        "net_value": {p: float(point_v[i] - cost * point_share[i]) for i, p in enumerate(names)},
        "hajek_value": {p: hajek_value(arm, spend, actions[p]) for p in names},
        "draws_value": dv,
        "draws_net": dv - cost * ds,
        "draws_hajek": dh,
        "draws_share": ds,
    }


def winner_rule(net: dict[str, float], diff_ci: dict[str, list[float]]) -> dict[str, Any]:
    """Rule 1d. `diff_ci[p]` is the paired 95% CI of NV(p) - NV(best blanket) for targeted p."""
    best = max(POLICIES, key=lambda p: (net[p], -POLICIES.index(p)))
    best_blanket = max(BLANKET, key=lambda p: (net[p], -POLICIES.index(p)))
    if best == "P0":
        winner, reason = "P0", "P0 has the highest holdout net value: send nothing."
    elif best in BLANKET:
        winner, reason = best, f"{best} (a blanket policy) has the highest holdout net value."
    elif diff_ci[best][0] > 0:
        winner, reason = best, f"{best} beats {best_blanket}: the paired 95% CI of the difference lies above zero."
    else:
        winner, reason = best_blanket, (
            f"{best} has the highest point estimate, but the paired 95% CI of its difference from {best_blanket} "
            "includes zero, so the best blanket policy is kept.")
    return {
        "highest_net_value": best,
        "best_blanket": best_blanket,
        "winner": winner,
        "targeting_beat_blanket": winner in TARGETED,
        "reason": reason,
    }


# ---------- the single evaluation ----------

def training_fingerprint(training: dict[str, Any]) -> str:
    """SHA-256 of the training.json content without its manifest (the manifest changes on every export)."""
    body = {k: v for k, v in training.items() if k != "manifest"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _policy_actions(hold: pd.DataFrame, uplift: pd.DataFrame, training: dict[str, Any], cost: float) -> dict[str, np.ndarray]:
    sel = training["selection"]
    n = len(hold)
    return {
        "P0": models.blanket(n, NONE),
        "P1": models.blanket(n, MENS),
        "P2": models.blanket(n, WOMENS),
        "P3": models.apply_segment_rule(hold, sel["p3_rule"]),
        "P4a": models.top_k(uplift[MENS].to_numpy(), sel["p4"][MENS]["chosen_k"], MENS),
        "P4b": models.top_k(uplift[WOMENS].to_numpy(), sel["p4"][WOMENS]["chosen_k"], WOMENS),
        "P5": models.uplift_assignment(uplift, cost),
    }


def compute(df: pd.DataFrame, training: dict[str, Any], sealed_hash: str | None = None) -> dict[str, Any]:
    """The evaluation. `sealed_hash` defaults to the committed split.json (synthetic smoke tests pass their own)."""
    data = split.SplitData(df)
    sealed = sealed_hash or json.loads((run.WEB_DATA / "split.json").read_text(encoding="utf-8"))["holdout_index_sha256"]
    if data.holdout_sha256() != sealed:
        raise RuntimeError("holdout hash does not match the sealed split.json")
    params = {a: training["tuning"][a]["chosen"] for a in models.MODEL_ARMS}
    fitted = models.fit_arm_models(data.train(), params)

    hold = data.holdout()
    uplift = models.predict_uplift(fitted, hold)
    arm = hold[ARM_COLUMN].astype(object).to_numpy()
    spend = hold["spend"].to_numpy(float)
    cost = models.DEFAULT_COST

    # Seven pre-selected policies at the default cost (primary comparison).
    actions = _policy_actions(hold, uplift, training, cost)
    t = policy_table(arm, spend, actions, cost, N_BOOT, SEED)
    i0 = t["names"].index("P0")
    best_blanket = max(BLANKET, key=lambda p: (t["net_value"][p], -POLICIES.index(p)))
    ib = t["names"].index(best_blanket)
    rows = []
    diff_ci: dict[str, list[float]] = {}
    for i, p in enumerate(t["names"]):
        inc_draws = t["draws_value"][:, i] - t["draws_value"][:, i0]
        net_draws = t["draws_net"][:, i] - t["draws_net"][:, i0]
        hajek_inc = t["hajek_value"][p] - t["hajek_value"]["P0"]
        nominal_inc = t["value"][p] - t["value"]["P0"]
        row = {
            "policy": p,
            "share_sent": float(t["share_sent"][p]),
            "action_share": {a: float(np.mean(actions[p] == a)) for a in models.ACTIONS},
            "value": float(t["value"][p]),
            "net_value": t["net_value"][p],
            "incremental_revenue_vs_p0": float(nominal_inc),
            "incremental_revenue_vs_p0_ci": ci(inc_draws),
            "net_value_vs_p0": float(t["net_value"][p] - t["net_value"]["P0"]),
            "net_value_vs_p0_ci": ci(net_draws),
            "hajek_value": t["hajek_value"][p],
            "hajek_incremental_revenue_vs_p0": float(hajek_inc),
            "hajek_incremental_revenue_vs_p0_ci": ci(t["draws_hajek"][:, i] - t["draws_hajek"][:, i0]),
            "hajek_sign_disagrees": bool(p != "P0" and np.sign(hajek_inc) != np.sign(nominal_inc)),
        }
        if p in TARGETED:
            diff_ci[p] = ci(t["draws_net"][:, i] - t["draws_net"][:, ib])
            row["net_value_minus_best_blanket"] = float(t["net_value"][p] - t["net_value"][best_blanket])
            row["net_value_minus_best_blanket_ci"] = diff_ci[p]
        rows.append(row)
    decision_1d = winner_rule(t["net_value"], diff_ci)

    # Descriptive: holdout net value vs k for P4a / P4b (k was chosen on training).
    k_actions = {f"{a}|{k}": models.top_k(uplift[a].to_numpy(), k, a) for a in models.EMAIL_ARMS for k in models.K_GRID}
    kt = policy_table(arm, spend, {"P0": actions["P0"], **k_actions}, cost, N_BOOT, SEED)
    k_curves = {a: [{"k": k, "net_value_vs_p0": float(kt["net_value"][f"{a}|{k}"] - kt["net_value"]["P0"]),
                     "net_value_vs_p0_ci": ci(kt["draws_net"][:, kt["names"].index(f"{a}|{k}")] - kt["draws_net"][:, 0])}
                    for k in models.K_GRID] for a in models.EMAIL_ARMS}

    # Cost grid: P1 and P2 (linear in cost) and P5 re-optimized at each cost.
    grid = []
    for c in COST_GRID:
        acts = {"P0": actions["P0"], "P1": actions["P1"], "P2": actions["P2"], "P5": models.uplift_assignment(uplift, c)}
        g = policy_table(arm, spend, acts, c, N_BOOT, SEED)
        grid.append({"cost": c, **{p: {"net_value_vs_p0": float(g["net_value"][p] - g["net_value"]["P0"]),
                                        "net_value_vs_p0_ci": ci(g["draws_net"][:, g["names"].index(p)] - g["draws_net"][:, 0]),
                                        "share_sent": float(g["share_sent"][p])}
                                   for p in ["P1", "P2", "P5"]}})

    return {
        "estimator": "nominal IPW, V = mean(spend * 1{T = pi(x)} * 3); NV = V - cost * share sent",
        "robustness_estimator": "Hajek (self-normalized by holdout arm shares); robustness check only",
        "bootstrap": {"resamples": N_BOOT, "seed": SEED, "paired": True, "interval": "percentile 95%"},
        "cost": cost,
        "holdout_index_sha256": data.holdout_sha256(),
        "training_fingerprint_sha256": training_fingerprint(training),
        "n_holdout": int(len(hold)),
        "holdout_arm_share": {a: float(np.mean(arm == a)) for a in models.ACTIONS},
        "selected": {"p3_dimension": training["selection"]["p3_selected_dimension"],
                     "p3_rule": training["selection"]["p3_rule"]["rule"],
                     "p4a_k": training["selection"]["p4"][MENS]["chosen_k"],
                     "p4b_k": training["selection"]["p4"][WOMENS]["chosen_k"]},
        "policies": rows,
        "winner": decision_1d,
        "hajek_sign_flags": [r["policy"] for r in rows if r["hajek_sign_disagrees"]],
        "qini_holdout": {a: models.qini_for_arm(hold, uplift[a], a) for a in models.EMAIL_ARMS},
        "net_value_by_k": k_curves,
        "cost_grid": grid,
    }


def blanket_values_duckdb(df: pd.DataFrame) -> dict[str, float]:
    """Independent recomputation of V(P0), V(P1), V(P2) in DuckDB SQL from the raw CSV, restricted to the
    holdout. Returns aggregates only; holdout rows never leave this module."""
    data = split.SplitData(df)
    ids = pd.DataFrame({"customer_index": data.holdout().index.to_numpy()})
    con = duckdb.connect()
    con.register("holdout_ids", ids)
    row = con.execute(
        """
        WITH raw AS (SELECT row_number() OVER () - 1 AS customer_index, * FROM read_csv_auto(?, header = true)),
             h AS (SELECT r.* FROM raw r JOIN holdout_ids USING (customer_index))
        SELECT 3 * AVG(CASE WHEN segment = 'No E-Mail' THEN spend ELSE 0 END),
               3 * AVG(CASE WHEN segment = 'Mens E-Mail' THEN spend ELSE 0 END),
               3 * AVG(CASE WHEN segment = 'Womens E-Mail' THEN spend ELSE 0 END),
               COUNT(*)
        FROM h
        """,
        [str(load.RAW_CSV)],
    ).fetchone()
    return {"P0": row[0], "P1": row[1], "P2": row[2], "n": row[3]}


def _close(a: Any, b: Any, rel: float = 1e-9) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k], rel) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y, rel) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return bool(np.isclose(a, b, rtol=rel, atol=1e-12))
    return a == b


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="recompute and compare with the committed targeting.json")
    args = parser.parse_args(argv)
    df = load.load()
    training = json.loads(TRAINING_JSON.read_text(encoding="utf-8"))
    if args.verify:
        committed = json.loads(TARGETING_JSON.read_text(encoding="utf-8"))
        fresh = compute(df, training)
        same = _close({k: committed[k] for k in fresh}, fresh)
        print(f"verify: recomputed evaluation {'MATCHES' if same else 'DIFFERS FROM'} the committed targeting.json")
        return 0 if same else 1
    if TARGETING_JSON.exists():
        print("REFUSED: targeting.json exists; the holdout is evaluated once (Deviations 2026-09-24, 1g). "
              "Use --verify to reproduce it.", file=sys.stderr)
        return 3
    if run.git_commit()["working_tree_dirty"]:
        print("REFUSED: working tree is dirty; the single evaluation must run on a committed tree.", file=sys.stderr)
        return 4
    raw_sha = load.sha256_file(load.RAW_CSV)
    if raw_sha != run.documented_sha256():
        print("HALT: dataset SHA-256 does not match docs/data-source.md", file=sys.stderr)
        return 2
    result = compute(df, training)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = run.manifest(raw_sha, "holdout-evaluation", generated)
    m["script"] = "python -m liftlab.evaluate"
    run.write_json(TARGETING_JSON, {"manifest": m, "evaluated_at_code_commit_sha": m["commit_sha"], **result})
    print(json.dumps({"winner": result["winner"], "hajek_sign_flags": result["hajek_sign_flags"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
