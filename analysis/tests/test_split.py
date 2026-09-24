"""Split and holdout guard (Sprint 3, Step 2; Deviations 2026-09-24, 1g)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from liftlab import split
from liftlab.run import WEB_DATA


@pytest.fixture(scope="module")
def sealed() -> dict:
    path = WEB_DATA / "split.json"
    assert path.exists(), "Run `python -m liftlab.run --stage sprint3` first"
    return json.loads(path.read_text(encoding="utf-8"))


def test_recomputed_split_matches_sealed_hash(df: pd.DataFrame, sealed: dict) -> None:
    assert split.holdout_index_sha256(df) == sealed["holdout_index_sha256"]
    assert split.SplitData(df).holdout_sha256() == sealed["holdout_index_sha256"]


def test_split_is_a_stratified_partition(df: pd.DataFrame, sealed: dict) -> None:
    train_idx = split.train_indices(df)
    assert len(np.unique(train_idx)) == len(train_idx) == sealed["n_train"]
    arm = df["segment"].astype(object).to_numpy()
    for a, sizes in sealed["by_arm"].items():
        n = int((arm == a).sum())
        assert sizes["holdout"] == round(0.30 * n)
        assert sizes["train"] + sizes["holdout"] == n
        assert int((arm[train_idx] == a).sum()) == sizes["train"]
    assert sealed["n_train"] + sealed["n_holdout"] == len(df)


def test_split_is_deterministic(df: pd.DataFrame) -> None:
    assert split.holdout_index_sha256(df) == split.holdout_index_sha256(df)
    assert split.holdout_index_sha256(df, seed=1) != split.holdout_index_sha256(df)


def test_holdout_guard_blocks_non_evaluate_callers(df: pd.DataFrame) -> None:
    data = split.SplitData(df)
    with pytest.raises(split.HoldoutAccessError):
        data.holdout()


def test_holdout_guard_blocks_indirect_callers(df: pd.DataFrame) -> None:
    # A helper defined outside evaluate.py that forwards the call is still blocked.
    data = split.SplitData(df)

    def training_helper() -> pd.DataFrame:
        return data.holdout()

    with pytest.raises(split.HoldoutAccessError):
        training_helper()


def test_train_rows_exclude_holdout(df: pd.DataFrame, sealed: dict) -> None:
    train = split.SplitData(df).train()
    assert len(train) == sealed["n_train"]
    assert np.array_equal(train.index.to_numpy(), df.index[split.train_indices(df)].to_numpy())


def test_no_module_touches_holdout_internals() -> None:
    # Only split.py (which defines them) and evaluate.py may reference the private split internals.
    from liftlab import load
    pkg = load.REPO_ROOT / "analysis" / "liftlab"
    offenders = [p.name for p in pkg.glob("*.py") if p.name not in {"split.py", "evaluate.py"}
                 and ("_holdout_idx" in p.read_text(encoding="utf-8") or "_make_split" in p.read_text(encoding="utf-8"))]
    assert not offenders, offenders
