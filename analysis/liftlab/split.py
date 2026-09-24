"""Train/holdout split and the holdout guard (analysis-plan Deviations 2026-09-24, 1g).

Customer index = 0-based row position in data/raw/hillstrom.csv (the dataset has no ID column).
The split is 70/30, stratified by arm, seed 20260923, made by `_make_split` only. Holdout rows can be
read only from liftlab/evaluate.py: `SplitData.holdout()` raises HoldoutAccessError for any other caller,
and the holdout indices themselves are never returned by a public function (only their hash).
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from liftlab import SEED
from liftlab.checks import ARM_COLUMN
from liftlab.effects import BOOTSTRAP_ARM_ORDER

HOLDOUT_FRACTION: float = 0.30
ARM_ORDER: list[str] = BOOTSTRAP_ARM_ORDER  # fixed order in which arms draw from the generator
EVALUATE_MODULE: Path = Path(__file__).resolve().parent / "evaluate.py"
HASH_DEFINITION: str = "sha256 of the ascending holdout customer indices, comma-separated, ASCII"


class HoldoutAccessError(RuntimeError):
    """Raised when holdout rows are requested outside liftlab/evaluate.py."""


def _make_split(df: pd.DataFrame, seed: int = SEED) -> tuple[np.ndarray, np.ndarray]:
    """(train_idx, holdout_idx) as sorted customer indices. Within each arm, a seeded permutation puts
    round(30% of the arm) into the holdout."""
    rng = np.random.default_rng(seed)
    arm = df[ARM_COLUMN].astype(object).to_numpy()
    positions = np.arange(len(df))
    holdout: list[np.ndarray] = []
    for a in ARM_ORDER:
        idx = positions[arm == a]
        perm = rng.permutation(idx)
        holdout.append(perm[: int(round(HOLDOUT_FRACTION * len(idx)))])
    holdout_idx = np.sort(np.concatenate(holdout))
    train_idx = np.setdiff1d(positions, holdout_idx)
    return train_idx, holdout_idx


def index_sha256(indices: np.ndarray) -> str:
    return hashlib.sha256(",".join(str(int(i)) for i in np.sort(indices)).encode("ascii")).hexdigest()


def holdout_index_sha256(df: pd.DataFrame, seed: int = SEED) -> str:
    """Recompute the split and return only the hash of its holdout indices."""
    return index_sha256(_make_split(df, seed)[1])


def train_indices(df: pd.DataFrame, seed: int = SEED) -> np.ndarray:
    return _make_split(df, seed)[0]


def _caller_file(depth: int) -> Path:
    return Path(sys._getframe(depth).f_code.co_filename).resolve()


@dataclass
class SplitData:
    """The only access path to split rows used by training and evaluation code."""

    df: pd.DataFrame
    train_idx: np.ndarray = field(init=False)
    _holdout_idx: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.train_idx, self._holdout_idx = _make_split(self.df)

    def train(self) -> pd.DataFrame:
        return self.df.iloc[self.train_idx].copy()

    def holdout(self) -> pd.DataFrame:
        caller = _caller_file(2)
        if caller != EVALUATE_MODULE:
            raise HoldoutAccessError(f"holdout rows requested from {caller}; only liftlab/evaluate.py may read them")
        return self.df.iloc[self._holdout_idx].copy()

    def holdout_sha256(self) -> str:
        return index_sha256(self._holdout_idx)

    def summary(self) -> dict[str, Any]:
        arm = self.df[ARM_COLUMN].astype(object).to_numpy()
        in_holdout = np.zeros(len(self.df), dtype=bool)
        in_holdout[self._holdout_idx] = True
        by_arm = {a: {"train": int(((arm == a) & ~in_holdout).sum()), "holdout": int(((arm == a) & in_holdout).sum())}
                  for a in ARM_ORDER}
        return {
            "customer_index": "0-based row position in data/raw/hillstrom.csv",
            "holdout_fraction": HOLDOUT_FRACTION,
            "stratified_by": ARM_COLUMN,
            "seed": SEED,
            "n_train": int(len(self.train_idx)),
            "n_holdout": int(len(self._holdout_idx)),
            "by_arm": by_arm,
            "holdout_index_sha256": self.holdout_sha256(),
            "hash_definition": HASH_DEFINITION,
            "holdout_readable_only_from": "liftlab/evaluate.py",
        }
