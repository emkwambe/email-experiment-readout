"""Section 10 application and recommendation object (Sprint 3, Steps 5-6)."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

import pytest

from liftlab import decision
from liftlab.run import WEB_DATA

MENS, WOMENS = decision.MENS, decision.WOMENS


def load_json(name: str) -> dict[str, Any]:
    path = WEB_DATA / name
    if not path.exists():
        pytest.skip(f"{name} not exported yet")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dec() -> dict[str, Any]:
    return load_json("decision.json")


def test_status_rule_hand_cases() -> None:
    assert decision.status(0.77, 0.49, 0.10) == "send"
    assert decision.status(0.42, 0.08, 0.10) == "promising — test again"
    assert decision.status(0.10, -0.2, 0.10) == "do not send"  # point estimate must exceed cost
    assert decision.status(0.05, -0.2, 0.10) == "do not send"


def test_break_even_and_margins_match_hand_computation(dec: dict[str, Any]) -> None:
    primary = load_json("effects_primary.json")
    for email, cid in [(MENS, "H1"), (WOMENS, "H2")]:
        c = next(x for x in primary["contrasts"] if x["id"] == cid)
        e = dec["emails"][email]
        # Net value = incremental revenue - cost, so break-even cost = incremental revenue.
        assert e["break_even_cost_at_estimate"] == c["estimate"]
        assert e["break_even_cost_at_lower_bound"] == c["ci_analytic"][0]
        assert e["minimum_margin_at_estimate"] == pytest.approx(0.10 / c["estimate"])
        assert e["minimum_margin_at_lower_bound"] == pytest.approx(0.10 / c["ci_analytic"][0])
        expected = "send" if c["ci_analytic"][0] > 0.10 else ("promising — test again" if c["estimate"] > 0.10 else "do not send")
        assert e["status"] == expected


def test_sensitivity_grid(dec: dict[str, Any]) -> None:
    rows = dec["sensitivity"]
    assert [r["cost"] for r in rows] == [round(0.01 * i, 2) for i in range(1, 51)]
    for r in rows:
        for email in (MENS, WOMENS):
            e = dec["emails"][email]
            assert r[email]["net_at_estimate"] == pytest.approx(e["incremental_revenue_per_customer"] - r["cost"])
            assert r[email]["status"] == decision.status(e["incremental_revenue_per_customer"], e["ci_analytic"][0], r["cost"])


def test_recommendation_follows_winner_and_is_template_generated(dec: dict[str, Any]) -> None:
    targeting = load_json("targeting.json")
    rec = dec["recommendation"]
    assert rec["policy"] == targeting["winner"]["winner"]
    assert "{" not in rec["sentence"] and "}" not in rec["sentence"]
    primary = load_json("effects_primary.json")
    fresh = decision.decide(primary, targeting)
    assert fresh["recommendation"]["sentence"] == rec["sentence"]
    for email in rec["emails_sent"]:
        assert rec["email_status"][email] == dec["emails"][email]["status"]


def test_every_template_branch_fills_all_placeholders() -> None:
    primary = load_json("effects_primary.json")
    targeting = load_json("targeting.json")
    for winner in ["P0", "P1", "P2", "P5"]:
        t = copy.deepcopy(targeting)
        t["winner"] = {**t["winner"], "winner": winner, "targeting_beat_blanket": winner == "P5"}
        for cost in (0.10, 0.45, 2.0):  # 2.0 exercises the "do not send"/promising paths
            s = decision.decide(primary, t, cost)["recommendation"]["sentence"]
            assert not re.search(r"[{}]", s), (winner, cost, s)
