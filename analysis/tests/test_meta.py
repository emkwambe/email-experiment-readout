"""Workflow record: git timeline and correction-log statistics (Sprint 3, Step 7)."""

from __future__ import annotations

import json

import pytest

from liftlab import meta
from liftlab.run import WEB_DATA


@pytest.fixture(scope="module")
def record() -> dict:
    path = WEB_DATA / "timeline.json"
    if not path.exists():
        pytest.skip("timeline.json not exported yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_timeline_starts_with_preregistration(record: dict) -> None:
    events = record["timeline"]
    assert events[0]["event"] == "preregistration"
    assert events[0]["sha"].startswith("48c63f4")
    kinds = [e["event"] for e in events]
    for k in ["first_data_access", "outcome_unlock", "deviation", "holdout_seal", "holdout_evaluation"]:
        assert k in kinds
    order = {k: kinds.index(k) for k in ["preregistration", "first_data_access", "outcome_unlock", "holdout_seal", "holdout_evaluation"]}
    assert list(order.values()) == sorted(order.values())


def test_correction_stats_are_consistent(record: dict) -> None:
    c = record["correction_log"]
    assert c["n_entries"] == len(c["entries"]) == sum(c["by_origin"].values()) == sum(c["by_caught"].values())
    assert c["n_entries"] == len(meta.correction_entries())


def test_correction_parser_on_sample() -> None:
    sample = (
        "**2026-01-01 · Sprint 1 · A**\n- **What was produced:** Claude Chat wrote X.\n- **How it was caught:** Human review.\n\n"
        "**2026-01-02 · Sprint 2 · B**\n- **What was produced:** Claude Code wrote Y.\n- **How it was caught:** The test failed on its first run.\n"
    )
    e = meta.correction_entries(sample)
    assert [(x["origin"], x["caught_by"]) for x in e] == [("Claude Chat", "Human review"), ("Claude Code", "Automated test or guard")]


# ---------- meta.py is a read-only workflow-record module (CLAUDE.md rule 9) ----------

FORBIDDEN_IMPORTS = {"pandas", "numpy", "liftlab"}  # any liftlab import could pull in the data layer transitively
FORBIDDEN_LIFTLAB = {"split", "models", "evaluate", "decision", "load", "run"}


def test_meta_imports_nothing_from_the_data_or_targeting_layers() -> None:
    import ast
    from pathlib import Path

    tree = ast.parse(Path(meta.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            if (node.module or "").startswith("liftlab"):
                imported |= {f"liftlab.{a.name}" for a in node.names}
    roots = {m.split(".")[0] for m in imported}
    assert not roots & FORBIDDEN_IMPORTS, sorted(imported)
    assert not {m for m in imported if m.split(".")[-1] in FORBIDDEN_LIFTLAB and m.startswith("liftlab")}


def test_meta_import_does_not_load_data_modules() -> None:
    import subprocess
    import sys

    code = ("import sys, liftlab.meta; "
            "bad = [m for m in ('pandas', 'numpy', 'liftlab.load', 'liftlab.split', 'liftlab.models', "
            "'liftlab.evaluate', 'liftlab.decision') if m in sys.modules]; print(','.join(bad))")
    out = subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True).stdout.strip()
    assert out == ""


def test_meta_opens_nothing_under_data(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins
    import io
    from pathlib import Path

    data_dir = (meta.REPO_ROOT / "data").resolve()
    opened: list[Path] = []
    real_open, real_io_open = builtins.open, io.open

    def spy(file, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        if isinstance(file, (str, Path)):
            opened.append(Path(file).resolve())
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(io, "open", spy)
    meta.record()
    assert opened, "spy saw no file reads; the check would be vacuous"
    assert not [p for p in opened if p == data_dir or data_dir in p.parents]
