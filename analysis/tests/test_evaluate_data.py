"""Checks on the single holdout evaluation (Sprint 3, Steps 4 and 6). Skipped until targeting.json exists."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from liftlab import evaluate
from liftlab.run import WEB_DATA


@pytest.fixture(scope="module")
def targeting() -> dict[str, Any]:
    path = WEB_DATA / "targeting.json"
    if not path.exists():
        pytest.skip("holdout not evaluated yet")
    return json.loads(path.read_text(encoding="utf-8"))


def by_policy(t: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {r["policy"]: r for r in t["policies"]}


def test_seven_preselected_policies_and_provenance(targeting: dict[str, Any]) -> None:
    assert [r["policy"] for r in targeting["policies"]] == evaluate.POLICIES
    split_json = json.loads((WEB_DATA / "split.json").read_text(encoding="utf-8"))
    assert targeting["holdout_index_sha256"] == split_json["holdout_index_sha256"]
    assert targeting["n_holdout"] == split_json["n_holdout"]
    assert targeting["evaluated_at_code_commit_sha"] == targeting["manifest"]["commit_sha"]
    assert targeting["manifest"]["working_tree_dirty"] is False
    training = json.loads((WEB_DATA / "training.json").read_text(encoding="utf-8"))
    assert targeting["training_fingerprint_sha256"] == evaluate.training_fingerprint(training)


def test_winner_follows_rule_1d(targeting: dict[str, Any]) -> None:
    rows = by_policy(targeting)
    net = {p: r["net_value"] for p, r in rows.items()}
    diff = {p: rows[p]["net_value_minus_best_blanket_ci"] for p in evaluate.TARGETED}
    assert evaluate.winner_rule(net, diff) == targeting["winner"]


def test_duckdb_recomputes_blanket_values(df: pd.DataFrame, targeting: dict[str, Any]) -> None:
    sql = evaluate.blanket_values_duckdb(df)
    rows = by_policy(targeting)
    assert sql["n"] == targeting["n_holdout"]
    for p in ("P0", "P1", "P2"):
        assert rows[p]["value"] == pytest.approx(sql[p], rel=1e-9)


def test_p1_holdout_increment_overlaps_full_sample_h1(targeting: dict[str, Any]) -> None:
    # Consistency, not equality: the holdout P1 increment's CI must overlap the Section 6 H1 CI.
    primary = json.loads((WEB_DATA / "effects_primary.json").read_text(encoding="utf-8"))
    h1 = next(c for c in primary["contrasts"] if c["id"] == "H1")["ci_analytic"]
    lo, hi = by_policy(targeting)["P1"]["incremental_revenue_vs_p0_ci"]
    assert lo <= h1[1] and h1[0] <= hi


def test_hajek_flags_are_consistent(targeting: dict[str, Any]) -> None:
    flags = [r["policy"] for r in targeting["policies"] if r["hajek_sign_disagrees"]]
    assert flags == targeting["hajek_sign_flags"]


def test_cost_grid_and_k_curves_complete(targeting: dict[str, Any]) -> None:
    assert [g["cost"] for g in targeting["cost_grid"]] == evaluate.COST_GRID
    for arm, curve in targeting["net_value_by_k"].items():
        assert [r["k"] for r in curve] == list(range(10, 101, 10))
    for q in targeting["qini_holdout"].values():
        assert len(q["phi"]) == len(q["q"]) == 101
