from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from liftlab import load
from liftlab.run import FROZEN_FILE, SPRINT1_FILES, WEB_DATA, documented_sha256

MANIFEST_KEYS = {"commit_sha", "working_tree_dirty", "dataset_sha256", "generated_utc", "script", "seed", "stage"}


def test_every_export_has_manifest(exports: dict[str, Any]) -> None:
    for name, payload in exports.items():
        m = payload["manifest"]
        assert MANIFEST_KEYS <= set(m), name
        assert re.fullmatch(r"[0-9a-f]{40}", m["commit_sha"]), name
        assert m["dataset_sha256"] == documented_sha256(), name
        assert m["seed"] == 20260923, name
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", m["generated_utc"]), name


def test_manifest_lists_exactly_the_published_exports(exports: dict[str, Any]) -> None:
    listed = [f["file"] for f in exports["manifest.json"]["files"]]
    present = sorted(p.name for p in WEB_DATA.glob("*.json") if p.name != "manifest.json")
    assert sorted(listed) == present
    assert listed[: len(SPRINT1_FILES)] == SPRINT1_FILES


def test_every_published_file_shares_one_manifest(exports: dict[str, Any]) -> None:
    # The single-use holdout evaluation keeps the manifest of the run that produced it.
    run_manifest = exports["manifest.json"]["manifest"]
    for path in WEB_DATA.glob("*.json"):
        m = json.loads(path.read_text(encoding="utf-8"))["manifest"]
        assert m["dataset_sha256"] == documented_sha256(), path.name
        if path.name != FROZEN_FILE:
            assert m == run_manifest, path.name


def test_local_dataset_matches_documented_hash() -> None:
    assert load.sha256_file(load.RAW_CSV) == documented_sha256()


def test_exports_retain_raw_source_zip_level(exports: dict[str, Any]) -> None:
    # Deviations 2026-09-23: "Surburban" stays as in the source; only the website relabels it.
    assert "Surburban" in exports["integrity.json"]["documented_levels"]["zip_code"]
    covariates = {r["covariate"] for r in exports["balance.json"]["rows"]}
    assert "zip_code=Surburban" in covariates
    assert "zip_code=Suburban" not in covariates


def test_web_plan_copy_is_identical_to_locked_plan() -> None:
    plan = load.REPO_ROOT / "docs" / "analysis-plan.md"
    copy = load.REPO_ROOT / "web" / "content" / "analysis-plan.md"
    assert copy.read_bytes() == plan.read_bytes(), "run `npm --prefix web run build` to resync web/content"


def test_preregistration_commit_is_recorded(exports: dict[str, Any]) -> None:
    pre = exports["manifest.json"]["preregistration"]
    assert re.fullmatch(r"[0-9a-f]{40}", pre["commit_sha"])
    assert pre["file"] == "docs/analysis-plan.md"


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(load.REPO_ROOT), *args], check=True, capture_output=True, text=True).stdout


def test_preregistration_precedes_all_loader_code(exports: dict[str, Any]) -> None:
    pre = exports["manifest.json"]["preregistration"]["commit_sha"]
    assert not [p for p in _git("ls-tree", "-r", "--name-only", pre).splitlines() if p.startswith("analysis/")]
    loader_commits = _git("log", "--format=%H", "--", "analysis/liftlab/load.py").split()
    assert loader_commits
    for c in loader_commits:
        assert c != pre
        subprocess.run(["git", "-C", str(load.REPO_ROOT), "merge-base", "--is-ancestor", pre, c], check=True)


def test_readme_cites_computed_preregistration_commit(exports: dict[str, Any]) -> None:
    pre = exports["manifest.json"]["preregistration"]["commit_sha"]
    readme = (load.REPO_ROOT / "README.md").read_text(encoding="utf-8")
    cited = set(re.findall(r"commit/([0-9a-f]{40})", readme))
    assert cited == {pre}
