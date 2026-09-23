"""Guard the outcome lock (CLAUDE.md rule 2): no Sprint 1 export may hold an outcome value by arm.

The walk inspects every JSON object that directly holds a number. Its context is the chain of
keys leading to it plus its own keys and direct string values. A number whose context names both
an arm and an outcome is a leak, unless the object is explicitly marked as computed from assumed
parameters (the power grid), whose rows test_power recomputes from arm sizes alone.
"""

from __future__ import annotations

from typing import Any

import pytest

OUTCOME_TERMS = ("visit", "conversion", "convert", "spend", "revenue", "purchase", "buyer")
ARM_TERMS = ("mens e-mail", "womens e-mail", "no e-mail", "control", "treat", "arm")


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


def test_guard_detects_synthetic_leaks() -> None:
    assert leaks({"by_arm": {"Mens E-Mail": {"spend_mean": 1.2}}})
    assert leaks({"visit_rate": {"Womens E-Mail": 0.1, "No E-Mail": 0.09}})
    assert leaks({"rows": [{"arm": "Mens E-Mail", "metric": "conversion", "value": 0.01}]})
    assert leaks({"rows": [{"arm": "Mens E-Mail", "metric": "conversion", "value": 0.01, "basis": "observed"}]})


def test_guard_allows_pooled_and_pre_period() -> None:
    assert not leaks({"gates": {"conversion_implies_visit": {"passed": True, "violations": 0}}})
    assert not leaks({"rows": [{"arm": "Mens E-Mail", "covariate": "history", "smd": 0.01}]})


@pytest.mark.parametrize("name", ["integrity.json", "srm.json", "balance.json", "power.json", "manifest.json"])
def test_no_outcome_by_arm_in_exports(exports: dict[str, Any], name: str) -> None:
    assert leaks(exports[name]) == []


def test_outcome_terms_only_in_pooled_gates_and_assumed_grid(exports: dict[str, Any]) -> None:
    for name in ["srm.json", "balance.json", "manifest.json"]:
        text = str({k: v for k, v in exports[name].items() if k != "manifest"}).lower()
        assert not any(t in text for t in OUTCOME_TERMS), name
