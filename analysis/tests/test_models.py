"""Training-split models, policies and Qini (Sprint 3, Step 3); holdout guard from training code (Step 6)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from liftlab import models, split
from liftlab.run import WEB_DATA

MENS, WOMENS, NONE = models.MENS, models.WOMENS, models.NONE


@pytest.fixture(scope="module")
def training() -> dict:
    path = WEB_DATA / "training.json"
    assert path.exists(), "Run `python -m liftlab.run --stage sprint3` first"
    return json.loads(path.read_text(encoding="utf-8"))


def test_qini_hand_example() -> None:
    # Ranked rows (uplift 3,2,1,0): treated/spend = (T,10), (C,0), (T,5), (C,1). With 2 points:
    # phi=0.5: top 2 -> R_T=10, R_C=0, N_T=1, N_C=1 -> Q=10. phi=1: R_T=15, R_C=1, N_T=2, N_C=2 -> Q=14.
    # Gap to the random line phi*Q(1): 0, 3, 0; trapezoid area = 1.5; per customer = 1.5 / 4.
    out = models.qini(np.array([3.0, 2.0, 1.0, 0.0]), np.array([1, 0, 1, 0]), np.array([10.0, 0.0, 5.0, 1.0]), points=2)
    assert out["q"] == pytest.approx([0.0, 10.0, 14.0])
    assert out["coefficient"] == pytest.approx(0.375)


def test_qini_uses_within_top_counts_not_arm_totals() -> None:
    # With arm totals (N_T=2, N_C=2 at every phi) Q(0.5) would be 10 - 0*1 = 10 either way, so use a case
    # where the top half is all treated: within-top N_C=0 means no control subtraction.
    out = models.qini(np.array([3.0, 2.0, 1.0, 0.0]), np.array([1, 1, 0, 0]), np.array([4.0, 4.0, 2.0, 2.0]), points=2)
    assert out["q"][1] == pytest.approx(8.0)
    assert out["q"][2] == pytest.approx(8.0 - 4.0 * 2 / 2)


def test_qini_matches_analytic_value_for_perfect_ranking() -> None:
    # tau ~ U(0, 2), half treated, ranked by true tau: Q(phi) ~ (n/2) * phi * (2 - phi), Q(1) ~ n/2, so the
    # area between Q and the random line is (n/2) * (1/2 - 1/3) = n/12, i.e. 1/12 per customer.
    rng = np.random.default_rng(0)
    n = 40_000
    tau = rng.uniform(0, 2, n)
    treated = rng.integers(0, 2, n)
    spend = rng.normal(5, 1, n) + treated * tau
    good = models.qini(tau, treated, spend)["coefficient"]
    rand = models.qini(rng.permutation(tau), treated, spend)["coefficient"]
    assert good == pytest.approx(1 / 12, abs=0.01)
    assert abs(rand) < 0.02


def test_top_k_and_uplift_assignment() -> None:
    u = np.array([0.5, 2.0, -1.0, 1.0, 0.0])
    assert list(models.top_k(u, 40, MENS)) == [NONE, MENS, NONE, MENS, NONE]
    assert list(models.top_k(u, 100, WOMENS)) == [WOMENS] * 5
    frame = pd.DataFrame({MENS: [0.3, 0.05, 0.2, -1.0], WOMENS: [0.1, 0.08, 0.2, 0.5]})
    assert list(models.uplift_assignment(frame, 0.10)) == [MENS, NONE, MENS, WOMENS]


def test_segment_rule_hand_example() -> None:
    frame = pd.DataFrame({
        "segment": [MENS, WOMENS, NONE] * 4,
        "newbie": [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
        "spend": [1.0, 0.0, 0.0, 1.0, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0],
    })
    rule = models.segment_rule(frame, "newbie", 0.10)
    # newbie=0: Mens 1.0-0-0.1=0.9, Womens 0.2-0-0.1=0.1 -> Mens. newbie=1: Mens -0.1, Womens 0.05-0.1=-0.05 -> None.
    assert rule["rule"] == {"newbie=0": MENS, "newbie=1": NONE}
    assert rule["training_net_value"]["newbie=0"][MENS] == pytest.approx(0.9)


def test_ipw_net_value_formula() -> None:
    frame = pd.DataFrame({"segment": [MENS, NONE, WOMENS], "spend": [3.0, 1.0, 2.0]})
    action = np.array([MENS, MENS, NONE], dtype=object)
    # Matches: row 0 (spend 3). Value = 3*3/3 = 3; sent share 2/3 -> net 3 - 0.1*2/3.
    assert models.ipw_net_value(frame, action, 0.10) == pytest.approx(3.0 - 0.1 * 2 / 3)


def test_training_export_is_consistent(training: dict) -> None:
    for arm, t in training["tuning"].items():
        assert t["chosen"] in models.PARAM_GRID
        assert t["cv_mse"] == min(r["cv_mse_mean"] for r in t["grid"])
        assert len(t["grid"]) == len(models.PARAM_GRID) == 16
    sel = training["selection"]
    means = {c["dimension"]: c["cv_net_value_mean"] for c in sel["p3_candidates"]}
    assert means[sel["p3_selected_dimension"]] == max(means.values())
    for arm, p in sel["p4"].items():
        best = max(r["cv_net_value_mean"] for r in p["by_k"])
        assert next(r for r in p["by_k"] if r["k"] == p["chosen_k"])["cv_net_value_mean"] == best
    assert sum(training["p5_training_oof_action_share"].values()) == pytest.approx(1.0)
    assert training["fixed_model_params"]["early_stopping"] is False


def test_holdout_guard_raises_for_training_code(df: pd.DataFrame) -> None:
    # A call that originates in liftlab/models.py (the training module) must be refused.
    data = split.SplitData(df)
    namespace: dict = {}
    exec(compile("def request(d):\n    return d.holdout()\n", str(Path(models.__file__).resolve()), "exec"), namespace)
    with pytest.raises(split.HoldoutAccessError):
        namespace["request"](data)


def test_training_module_never_requests_holdout() -> None:
    source = Path(models.__file__).read_text(encoding="utf-8")
    assert ".holdout(" not in source and "_holdout_idx" not in source
