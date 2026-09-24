"""Fill the generated blocks in README.md from the published JSON (rule 1: no hand-typed numbers).

Usage: python -m liftlab.readme   (rewrites the blocks in place; tests/test_readme.py fails if they drift)
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from liftlab.run import WEB_DATA
from liftlab.load import REPO_ROOT

README = REPO_ROOT / "README.md"
BLOCK = re.compile(r"(<!-- generated:(?P<name>[a-z-]+) -->\n)(?P<body>.*?)(<!-- /generated -->)", re.S)


def _load(name: str) -> dict[str, Any]:
    return json.loads((WEB_DATA / name).read_text(encoding="utf-8"))


def blocks() -> dict[str, str]:
    decision = _load("decision.json")
    record = _load("timeline.json")
    rec = decision["recommendation"]
    log = record["correction_log"]
    origin = ", ".join(f"{n} from {k}" for k, n in sorted(log["by_origin"].items(), key=lambda kv: -kv[1]))
    caught = "\n".join(f"  - {k}: {n}" for k, n in sorted(log["by_caught"].items(), key=lambda kv: -kv[1]))
    rec_lines = [f"> **{rec['sentence']}**"]
    if rec.get("supplementary_margin_sentence"):
        rec_lines.append(f">\n> {rec['supplementary_margin_sentence']}")
    return {
        "recommendation": "\n".join(rec_lines) + "\n",
        "corrections": (
            f"- **{log['n_entries']} errors** caught and recorded in the [correction log](ai-workflow/correction-log.md): {origin}.\n"
            f"- How they were caught:\n{caught}\n"
        ),
    }


def render(text: str) -> str:
    values = blocks()
    return BLOCK.sub(lambda m: m.group(1) + values[m.group("name")] + m.group(4), text)


def main() -> int:
    text = README.read_text(encoding="utf-8")
    README.write_text(render(text), encoding="utf-8", newline="\n")
    print("README generated blocks updated:", ", ".join(blocks()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
