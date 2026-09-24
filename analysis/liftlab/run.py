"""Pipeline entry point: `python -m liftlab.run --stage sprint1`.

Regenerates every published Sprint 1 number and writes JSON exports with a manifest block
to web/public/data/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from liftlab import SEED, checks, effects, heterogeneity, load, power, split

WEB_DATA: Path = load.REPO_ROOT / "web" / "public" / "data"
SCRIPT: str = "liftlab.run"
SPRINT1_FILES: list[str] = ["integrity.json", "srm.json", "balance.json", "power.json"]
# The only exports allowed to hold outcome estimates by arm (CLAUDE.md rule 2, analysis-plan Sections 6-8).
SPRINT2_FILES: list[str] = ["effects_primary.json", "effects_secondary.json", "cuped.json", "heterogeneity.json"]
# Sections 9-10 outputs (CLAUDE.md rule 9). Targeting content may appear only in TARGETING_FILES.
TARGETING_FILES: list[str] = ["split.json", "training.json", "targeting.json", "decision.json"]
SPRINT3_FILES: list[str] = TARGETING_FILES + ["timeline.json"]


def git_commit() -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(load.REPO_ROOT), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    dirty = git("status", "--porcelain", "--", ".", ":(exclude)web/public/data")
    return {"commit_sha": git("rev-parse", "HEAD"), "working_tree_dirty": bool(dirty)}


PLAN_PATH: str = "docs/analysis-plan.md"


def preregistration() -> dict[str, str]:
    """The commit that first added the analysis plan (the pre-registration reference)."""
    out = subprocess.run(
        ["git", "-C", str(load.REPO_ROOT), "log", "--diff-filter=A", "--format=%H %cI", "--", PLAN_PATH],
        check=True, capture_output=True, text=True,
    ).stdout.strip().splitlines()
    sha, committed = out[-1].split(" ")
    committed_utc = datetime.fromisoformat(committed).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"commit_sha": sha, "committed_utc": committed_utc, "file": PLAN_PATH}


def documented_sha256() -> str:
    """The dataset SHA-256 recorded in docs/data-source.md."""
    text = load.DATA_SOURCE_DOC.read_text(encoding="utf-8")
    match = re.search(r"\| SHA-256 \| `([0-9a-f]{64})` \|", text)
    if not match:
        raise RuntimeError("No dataset SHA-256 found in docs/data-source.md")
    return match.group(1)


def manifest(dataset_sha256: str, stage: str, generated_utc: str) -> dict[str, Any]:
    return {
        **git_commit(),
        "dataset_sha256": dataset_sha256,
        "generated_utc": generated_utc,
        "script": f"python -m {SCRIPT} --stage {stage}",
        "seed": SEED,
        "stage": stage,
    }


def write_json(path: Path, payload: dict[str, Any]) -> str:
    text = json.dumps(payload, indent=2, allow_nan=False, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


STAGES: list[str] = ["sprint1", "sprint2", "sprint3"]


def run_stage(stage: str) -> int:
    """Stages are cumulative: sprint2 regenerates the Sprint 1 exports as well as its own."""
    raw = load.fetch_raw()
    expected = documented_sha256()
    if raw.sha256 != expected:
        print(f"HALT: dataset SHA-256 {raw.sha256} != documented {expected}", file=sys.stderr)
        return 2
    df = load.load()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m = manifest(raw.sha256, stage, generated)
    arm_sizes = checks.srm(df)["observed"]
    results: dict[str, dict[str, Any]] = {
        "integrity.json": checks.integrity(df),
        "srm.json": checks.srm(df),
        "balance.json": checks.balance(df),
        "power.json": power.power_grid(arm_sizes, checks.CONTROL_ARM, checks.TREATMENT_ARMS),
    }
    summary: dict[str, Any] = {
        "integrity_passed": results["integrity.json"]["passed"],
        "srm_p_value": results["srm.json"]["p_value"],
        "srm_halt": results["srm.json"]["halt"],
        "balance_n_flagged": results["balance.json"]["n_flagged"],
        "halted": (not results["integrity.json"]["passed"]) or results["srm.json"]["halt"],
    }
    stop = summary["halted"]

    if stage in ("sprint2", "sprint3") and not summary["halted"]:
        results["effects_primary.json"] = effects.primary(df)
        results["effects_secondary.json"] = effects.secondary(df)
        results["cuped.json"] = effects.cuped(df)
        results["heterogeneity.json"] = heterogeneity.heterogeneity(df)
        summary["effects_agreement_passed"] = results["effects_primary.json"]["all_agreement_passed"]
        summary["cuped_signs_agree"] = results["cuped.json"]["all_signs_agree"]
        summary["heterogeneity_n_tests"] = results["heterogeneity.json"]["n_tests"]
        summary["heterogeneity_n_reject_holm"] = results["heterogeneity.json"]["n_reject_holm"]
        stop = stop or not summary["effects_agreement_passed"] or not summary["cuped_signs_agree"]

    if stage == "sprint3" and not stop:
        data = split.SplitData(df)
        results["split.json"] = data.summary()

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    file_hashes = {
        name: write_json(WEB_DATA / name, {"manifest": m, **payload}) for name, payload in results.items()
    }
    write_json(WEB_DATA / "manifest.json", {
        "manifest": m,
        "preregistration": preregistration(),
        "files": [{"file": n, "sha256": h} for n, h in file_hashes.items()],
        "summary": summary,
    })
    print(json.dumps({"manifest": m, "summary": summary}, indent=2))
    return 1 if stop else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", required=True, choices=STAGES)
    args = parser.parse_args(argv)
    return run_stage(args.stage)


if __name__ == "__main__":
    sys.exit(main())
