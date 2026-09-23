from __future__ import annotations

import re
from typing import Any

from liftlab import load
from liftlab.run import SPRINT1_FILES, documented_sha256

MANIFEST_KEYS = {"commit_sha", "working_tree_dirty", "dataset_sha256", "generated_utc", "script", "seed", "stage"}


def test_every_export_has_manifest(exports: dict[str, Any]) -> None:
    for name, payload in exports.items():
        m = payload["manifest"]
        assert MANIFEST_KEYS <= set(m), name
        assert re.fullmatch(r"[0-9a-f]{40}", m["commit_sha"]), name
        assert m["dataset_sha256"] == documented_sha256(), name
        assert m["seed"] == 20260923, name
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", m["generated_utc"]), name


def test_manifest_lists_all_exports(exports: dict[str, Any]) -> None:
    assert [f["file"] for f in exports["manifest.json"]["files"]] == SPRINT1_FILES


def test_local_dataset_matches_documented_hash() -> None:
    assert load.sha256_file(load.RAW_CSV) == documented_sha256()


def test_exports_retain_raw_source_zip_level(exports: dict[str, Any]) -> None:
    # Deviations 2026-09-23: "Surburban" stays as in the source; only the website relabels it.
    assert "Surburban" in exports["integrity.json"]["documented_levels"]["zip_code"]
    covariates = {r["covariate"] for r in exports["balance.json"]["rows"]}
    assert "zip_code=Surburban" in covariates
    assert "zip_code=Suburban" not in covariates
