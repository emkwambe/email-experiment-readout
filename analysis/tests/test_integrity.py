from __future__ import annotations

import pandas as pd

from liftlab import checks, load


def test_row_count_is_64000(df: pd.DataFrame) -> None:
    assert len(df) == 64_000
    assert list(df.columns) == load.COLUMNS


def test_every_integrity_gate_passes(df: pd.DataFrame) -> None:
    result = checks.integrity(df)
    failed = {k: g for k, g in result["gates"].items() if not g["passed"]}
    assert not failed
    assert result["passed"] is True
    assert result["row_count"] == 64_000


def test_integrity_on_raw_untyped_frame_matches_typed(df: pd.DataFrame) -> None:
    assert checks.integrity(load.read_raw()) == checks.integrity(df)


def _tiny() -> pd.DataFrame:
    return pd.DataFrame({
        "recency": [1, 2], "history_segment": ["1) $0 - $100"] * 2, "history": [10.0, 20.0],
        "mens": [1, 0], "womens": [0, 1], "zip_code": ["Urban", "Surburban"], "newbie": [0, 1],
        "channel": ["Web", "Phone"], "segment": ["Mens E-Mail", "No E-Mail"],
        "visit": [1, 0], "conversion": [1, 0], "spend": [5.0, 0.0],
    })


def test_consistency_gates_detect_violations() -> None:
    bad = _tiny()
    bad.loc[1, "spend"] = 3.0  # spend > 0 without conversion
    bad.loc[0, "visit"] = 0  # conversion without visit
    gates = checks.integrity(bad)["gates"]
    assert gates["spend_positive_implies_conversion"] == {"passed": False, "violations": 1}
    assert gates["conversion_implies_visit"] == {"passed": False, "violations": 1}
    assert gates["row_count_is_64000"]["passed"] is False


def test_documented_levels_is_exact_match() -> None:
    bad = _tiny()
    bad.loc[1, "zip_code"] = "Suburban"  # the publisher's prose spelling, not the file's
    gates = checks.integrity(bad)["gates"]
    assert gates["documented_levels_zip_code"] == {"passed": False, "violations": 1}
    bad.loc[1, "zip_code"] = "Surburban"
    bad.loc[0, "channel"] = "Email"
    gates = checks.integrity(bad)["gates"]
    assert gates["documented_levels_zip_code"]["passed"] is True
    assert gates["documented_levels_channel"] == {"passed": False, "violations": 1}


def test_nulls_and_negative_spend_detected() -> None:
    bad = _tiny()
    bad.loc[0, "history"] = None
    bad.loc[1, "spend"] = -1.0
    gates = checks.integrity(bad)["gates"]
    assert gates["no_nulls"] == {"passed": False, "violations": 1}
    assert gates["spend_nonnegative"] == {"passed": False, "violations": 1}
