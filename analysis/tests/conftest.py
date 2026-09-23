from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pytest

from liftlab import load
from liftlab.run import SPRINT1_FILES, WEB_DATA


@pytest.fixture(scope="session")
def df() -> pd.DataFrame:
    return load.load()


@pytest.fixture(scope="session")
def exports() -> dict[str, Any]:
    names = SPRINT1_FILES + ["manifest.json"]
    missing = [n for n in names if not (WEB_DATA / n).exists()]
    assert not missing, f"Run `python -m liftlab.run --stage sprint1` first; missing {missing}"
    return {n: json.loads((WEB_DATA / n).read_text(encoding="utf-8")) for n in names}
