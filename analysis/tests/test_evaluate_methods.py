"""Holdout-evaluation estimators on synthetic data (Sprint 3, Step 6). No holdout rows are used here."""

from __future__ import annotations

import numpy as np
import pytest

from liftlab import evaluate, models

MENS, WOMENS, NONE = models.MENS, models.WOMENS, models.NONE


def synthetic(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Randomized 1/3 each. y0 ~ Exp(mean 2); Mens adds 1.0 if x=1 else 0.2; Womens adds 0.5.
    Policy: x=1 -> Mens, x=0 -> Womens. True value = 2 + 0.4*1.0 + 0.6*0.5 = 2.7; sends to everyone."""
    x = rng.random(n) < 0.4
    arm = rng.choice(np.array(models.ACTIONS, dtype=object), n)
    y0 = rng.exponential(2.0, n)
    y = y0 + (arm == MENS) * np.where(x, 1.0, 0.2) + (arm == WOMENS) * 0.5
    action = np.where(x, MENS, WOMENS).astype(object)
    return arm, y, action


def test_ipw_policy_value_ci_covers_known_truth() -> None:
    rng = np.random.default_rng(20260923)
    true_net = 2.7 - 0.10 * 1.0
    covered = 0
    for rep in range(20):
        arm, y, action = synthetic(6000, rng)
        t = evaluate.policy_table(arm, y, {"P": action}, 0.10, 400, seed=rep)
        lo, hi = evaluate.ci(t["draws_net"][:, 0])
        covered += lo <= true_net <= hi
    assert covered >= 16  # P(Binomial(20, 0.95) < 16) is about 0.3%


def test_ipw_point_estimate_close_to_truth_at_scale() -> None:
    arm, y, action = synthetic(300_000, np.random.default_rng(1))
    t = evaluate.policy_table(arm, y, {"P": action}, 0.10, 50, seed=1)
    assert t["value"]["P"] == pytest.approx(2.7, abs=0.03)
    assert t["hajek_value"]["P"] == pytest.approx(2.7, abs=0.03)


def test_vectorized_hajek_matches_scalar_definition() -> None:
    rng = np.random.default_rng(3)
    arm, y, action = synthetic(2000, rng)
    t = evaluate.policy_table(arm, y, {"P": action, "Q": models.blanket(2000, MENS)}, 0.10, 30, seed=3)
    w = next(evaluate.bootstrap_weights(2000, 30, np.random.default_rng(3)))
    for j, name in enumerate(["P", "Q"]):
        pol = action if name == "P" else models.blanket(2000, MENS)
        expected = [evaluate.hajek_value(arm, y, pol, w[r]) for r in range(len(w))]
        assert t["draws_hajek"][:, j] == pytest.approx(expected, rel=1e-12)


def test_paired_bootstrap_difference_of_identical_policies_is_zero() -> None:
    arm, y, _ = synthetic(3000, np.random.default_rng(4))
    same = models.blanket(3000, MENS)
    t = evaluate.policy_table(arm, y, {"A": same, "B": same.copy()}, 0.10, 200, seed=4)
    assert evaluate.ci(t["draws_net"][:, 1] - t["draws_net"][:, 0]) == [0.0, 0.0]


def test_winner_rule_cases() -> None:
    base = {"P0": 0.0, "P1": 0.6, "P2": 0.3, "P3": 0.6, "P4a": 0.6, "P4b": 0.3, "P5": 0.7}
    # Targeted best, CI includes zero -> best blanket kept.
    w = evaluate.winner_rule(base, {"P3": [0, 0], "P4a": [0, 0], "P4b": [-0.3, -0.3], "P5": [-0.05, 0.25]})
    assert (w["highest_net_value"], w["winner"], w["targeting_beat_blanket"]) == ("P5", "P1", False)
    # Targeted best, CI above zero -> targeted wins.
    w = evaluate.winner_rule(base, {"P3": [0, 0], "P4a": [0, 0], "P4b": [-0.3, -0.3], "P5": [0.01, 0.2]})
    assert (w["winner"], w["targeting_beat_blanket"]) == ("P5", True)
    # Blanket best; ties go to policy order (P1 before P3 / P4a).
    w = evaluate.winner_rule({**base, "P5": 0.5}, {"P3": [0, 0], "P4a": [0, 0], "P4b": [-0.3, -0.3], "P5": [-0.2, 0.0]})
    assert w["winner"] == "P1"
    # Nothing pays -> send nothing.
    neg = {p: -0.1 for p in base} | {"P0": 0.0}
    assert evaluate.winner_rule(neg, {p: [-1, -0.1] for p in evaluate.TARGETED})["winner"] == "P0"


def test_full_evaluation_path_on_synthetic_outcomes(df) -> None:  # noqa: ANN001
    """Smoke-test compute() end to end without real outcomes: real covariates, permuted arm labels, noise spend."""
    import json

    from liftlab import split
    from liftlab.run import WEB_DATA

    rng = np.random.default_rng(99)
    fake = df.copy()
    fake["segment"] = rng.permutation(fake["segment"].to_numpy())
    fake["spend"] = np.where(rng.random(len(fake)) < 0.01, rng.exponential(100, len(fake)), 0.0)
    training = json.loads((WEB_DATA / "training.json").read_text(encoding="utf-8"))
    out = evaluate.compute(fake, training, sealed_hash=split.holdout_index_sha256(fake))
    assert [r["policy"] for r in out["policies"]] == evaluate.POLICIES
    assert out["winner"]["winner"] in evaluate.POLICIES
    assert len(out["cost_grid"]) == 50 and set(out["net_value_by_k"]) == set(models.EMAIL_ARMS)
