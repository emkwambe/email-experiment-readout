"""Guard the outcome lock (CLAUDE.md rules 2 and 9).

Since the outcome-unlock commit, by-arm outcome estimates may appear only in the Sprint 2 exports
(analysis-plan Sections 6-8). Every other export must still be free of them, and no export, module
or page may contain targeting, policy or train/holdout-split output (Sections 9-10, Sprint 3).

The by-arm walk inspects every JSON object that directly holds a number. Its context is the chain
of keys leading to it plus its own keys and direct string values. A number whose context names both
an arm and an outcome is a by-arm outcome, unless the object is explicitly marked as computed from
assumed parameters (the power grid), whose rows test_power recomputes from arm sizes alone.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from liftlab import load
from liftlab.run import SPRINT1_FILES, SPRINT2_FILES, WEB_DATA

OUTCOME_TERMS = ("visit", "conversion", "convert", "spend", "revenue", "purchase", "buyer")
ARM_TERMS = ("mens e-mail", "womens e-mail", "no e-mail", "control", "treat", "arm")
LOCKED_FILES = SPRINT1_FILES + ["manifest.json"]
ALLOWED_FILES = set(LOCKED_FILES + SPRINT2_FILES)

# Sections 9-10: nothing resembling a targeting model, policy, holdout split or recommendation.
TARGETING_KEY = re.compile(r"target|polic|uplift|qini|holdout|train|split|top_?k|recommend|send_to|decision", re.I)
TARGETING_CODE = re.compile(
    r"train_test_split|StratifiedShuffleSplit|KFold|GradientBoosting|HistGradientBoosting|sklift\.models|"
    r"qini|uplift_at_k|holdout|TwoModels|SoloModel|ClassTransformation",
    re.I,
)


def leaks(node: Any, path: tuple[str, ...] = ()) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        own_strings = [str(k) for k in node] + [v for v in node.values() if isinstance(v, str)]
        has_number = any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in node.values())
        context = " ".join(path + tuple(own_strings)).lower()
        if (
            has_number
            and node.get("basis") != "assumed_parameters"
            and any(t in context for t in OUTCOME_TERMS)
            and any(t in context for t in ARM_TERMS)
        ):
            found.append("/".join(path) or "<root>")
        for k, v in node.items():
            found += leaks(v, path + (str(k),))
    elif isinstance(node, list):
        for v in node:
            found += leaks(v, path)
    return found


def all_keys(node: Any) -> list[str]:
    if isinstance(node, dict):
        return [str(k) for k in node] + [k for v in node.values() for k in all_keys(v)]
    if isinstance(node, list):
        return [k for v in node for k in all_keys(v)]
    return []


def published() -> dict[str, Any]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(WEB_DATA.glob("*.json"))}


def test_guard_detects_synthetic_leaks() -> None:
    assert leaks({"by_arm": {"Mens E-Mail": {"spend_mean": 1.2}}})
    assert leaks({"visit_rate": {"Womens E-Mail": 0.1, "No E-Mail": 0.09}})
    assert leaks({"rows": [{"arm": "Mens E-Mail", "metric": "conversion", "value": 0.01}]})
    assert leaks({"rows": [{"arm": "Mens E-Mail", "metric": "conversion", "value": 0.01, "basis": "observed"}]})


def test_guard_allows_pooled_and_pre_period() -> None:
    assert not leaks({"gates": {"conversion_implies_visit": {"passed": True, "violations": 0}}})
    assert not leaks({"rows": [{"arm": "Mens E-Mail", "covariate": "history", "smd": 0.01}]})


def test_targeting_patterns_detect_synthetic_output() -> None:
    assert any(TARGETING_KEY.search(k) for k in all_keys({"policy": {"top_k": 20, "net_revenue": 1.0}}))
    assert any(TARGETING_KEY.search(k) for k in all_keys({"rows": [{"recommendation": "send"}]}))
    assert TARGETING_CODE.search("from sklearn.model_selection import train_test_split")
    assert not any(TARGETING_KEY.search(k) for k in all_keys({"estimate": 0.5, "ci_low": 0.1, "segment": "Web"}))


def test_only_known_exports_exist() -> None:
    unknown = set(published()) - ALLOWED_FILES
    assert not unknown, f"unexpected exports (by-arm outcomes are allowed only in {SPRINT2_FILES}): {unknown}"


@pytest.mark.parametrize("name", LOCKED_FILES)
def test_no_outcome_by_arm_outside_sprint2_exports(exports: dict[str, Any], name: str) -> None:
    assert leaks(exports[name]) == []


def test_outcome_terms_only_in_pooled_gates_and_assumed_grid(exports: dict[str, Any]) -> None:
    for name in ["srm.json", "balance.json", "manifest.json"]:
        text = str({k: v for k, v in exports[name].items() if k != "manifest"}).lower()
        assert not any(t in text for t in OUTCOME_TERMS), name


def test_no_targeting_or_policy_output_in_any_export() -> None:
    for name, payload in published().items():
        assert not TARGETING_KEY.search(name), name
        bad = sorted({k for k in all_keys(payload) if TARGETING_KEY.search(k)})
        assert not bad, f"{name}: {bad}"


def test_no_targeting_model_or_split_in_code() -> None:
    roots = [load.REPO_ROOT / "analysis" / "liftlab", load.REPO_ROOT / "web" / "app", load.REPO_ROOT / "web" / "lib"]
    files = [p for r in roots for p in r.rglob("*") if p.suffix in {".py", ".ts", ".tsx"}]
    assert files
    hits = [f"{p.relative_to(load.REPO_ROOT)}" for p in files if TARGETING_CODE.search(p.read_text(encoding="utf-8"))]
    assert not hits, hits
    assert not [p for p in files if re.search(r"uplift|target|polic", p.stem, re.I)]
