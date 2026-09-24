"""README generated blocks must match the published JSON exactly (rule 1)."""

from __future__ import annotations

import pytest

from liftlab import readme
from liftlab.run import WEB_DATA


def test_readme_generated_blocks_match_json() -> None:
    if not (WEB_DATA / "decision.json").exists() or not (WEB_DATA / "timeline.json").exists():
        pytest.skip("decision.json / timeline.json not exported yet")
    text = readme.README.read_text(encoding="utf-8")
    names = [m.group("name") for m in readme.BLOCK.finditer(text)]
    assert names == ["recommendation", "corrections"]
    assert readme.render(text) == text, "run `python -m liftlab.readme` to refresh README.md"
