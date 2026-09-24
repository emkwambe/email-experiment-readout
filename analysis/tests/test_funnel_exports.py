"""v1.0.1 funnel exports: relative lifts for visits and purchases, purchase rate among visitors (descriptive)."""

from __future__ import annotations

import json
import math
from typing import Any

import pytest

from liftlab.run import WEB_DATA


@pytest.fixture(scope="module")
def sec() -> dict[str, Any]:
    return json.loads((WEB_DATA / "effects_secondary.json").read_text(encoding="utf-8"))


def test_relative_lifts_match_rates_and_delta_method(sec: dict[str, Any]) -> None:
    for metric, block in sec["metrics"].items():
        for c in block["contrasts"]:
            t, k = block["arms"][c["treatment"]], block["arms"][c["comparison"]]
            rl = c["relative_lift"]
            assert rl["estimate"] == pytest.approx(t["rate"] / k["rate"] - 1, rel=1e-12)
            # Delta method with sample variances of 0/1 outcomes: var(mean) = p(1-p)/(n-1).
            vt = t["rate"] * (1 - t["rate"]) / (t["n"] - 1)
            vk = k["rate"] * (1 - k["rate"]) / (k["n"] - 1)
            se = math.sqrt(vt / k["rate"] ** 2 + t["rate"] ** 2 * vk / k["rate"] ** 4)
            assert rl["se"] == pytest.approx(se, rel=1e-9)
            assert rl["ci_low"] < rl["estimate"] < rl["ci_high"]
            assert rl["supplementary"] is True and rl["pre_registered"] is False


def test_purchase_rate_among_visitors_is_descriptive_and_consistent(sec: dict[str, Any]) -> None:
    block = sec["purchase_rate_among_visitors"]
    assert block["descriptive_only"] is True
    assert "post-treatment" in block["reason"]
    text = json.dumps(block).lower()
    assert "p_value" not in text and "ci_" not in text and "p_holm" not in text
    visits, convs = sec["metrics"]["visit_rate"]["arms"], sec["metrics"]["conversion_rate"]["arms"]
    for arm, v in block["arms"].items():
        # Every purchaser visited (integrity gate), so purchasers among visitors = all purchasers.
        assert v["visitors"] == visits[arm]["events"]
        assert v["purchasers"] == convs[arm]["events"]
        assert v["purchase_rate_among_visitors"] == pytest.approx(v["purchasers"] / v["visitors"])
