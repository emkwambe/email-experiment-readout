"""Workflow record for /how-its-built: a timeline read from git and statistics parsed from the correction log.

Written to web/public/data/timeline.json by `python -m liftlab.run --stage sprint3` (rule 1: numbers on the
site come from analysis code). Milestones are located by git queries, never typed by hand.

Read-only workflow-record module (CLAUDE.md rule 9): it reads git history and the correction log only. It must
not import the data-access layer, the targeting modules, pandas or numpy, or open anything under data/;
tests/test_meta.py enforces this.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
CORRECTION_LOG = REPO_ROOT / "ai-workflow" / "correction-log.md"
PLAN = "docs/analysis-plan.md"

ENTRY_HEADING = re.compile(r"^\*\*(\d{4}-\d{2}-\d{2}) · Sprint (\d+) · (.+?)\*\*\s*$", re.M)

# How-caught categories, first match wins (order matters). Each is (label, pattern on the "How it was caught" text).
CAUGHT_RULES: list[tuple[str, str]] = [
    ("Human review", r"human review"),
    ("Claude Code pre-check or plan review (before results)", r"pre-check|plan ambiguity|py -0p|preflight"),
    ("Automated test or guard", r"\btests?\b.*\b(fail|caught)|guard tests?|failed on its first run|test run"),
    ("Screenshot review", r"screenshot"),
    ("Claude Code self-review", r"."),
]


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO_ROOT), *args], check=True, capture_output=True, text=True).stdout


def _commit(sha: str) -> dict[str, str]:
    full, iso, subject = _git("show", "-s", "--format=%H%x1f%cI%x1f%s", sha).strip().split("\x1f")
    utc = datetime.fromisoformat(iso).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"sha": full, "short_sha": full[:7], "date_utc": utc, "subject": subject}


def _first_adding(path: str) -> str | None:
    out = _git("log", "--diff-filter=A", "--format=%H", "--", path).split()
    return out[-1] if out else None


def _subject_match(prefix: str) -> str | None:
    for line in _git("log", "--format=%H%x1f%s").splitlines():
        sha, subject = line.split("\x1f", 1)
        if subject.startswith(prefix):
            return sha
    return None


def timeline() -> list[dict[str, Any]]:
    events: list[tuple[str, str, str | None]] = [
        ("preregistration", "Pre-registration: analysis plan committed", _first_adding(PLAN)),
        ("first_data_access", "First data access: data loader committed", _first_adding("analysis/liftlab/load.py")),
        ("outcome_unlock", "Outcome unlock (Sections 6–8)", _subject_match("outcome unlock")),
    ]
    added = _first_adding(PLAN)
    for sha in reversed(_git("log", "--format=%H", "--", PLAN).split()):
        if sha != added:
            events.append(("deviation", "Plan Deviations entry", sha))
    events += [
        ("holdout_seal", "Holdout sealed (hash committed before training)", _first_adding("web/public/data/split.json")),
        ("holdout_evaluation", "Holdout evaluated (single use)", _first_adding("web/public/data/targeting.json")),
    ]
    out = [{"event": kind, "label": label, **_commit(sha)} for kind, label, sha in events if sha]
    return sorted(out, key=lambda e: e["date_utc"])


def _field(body: str, name: str) -> str:
    m = re.search(rf"- \*\*{re.escape(name)}:\*\*(.*?)(?=\n- \*\*|\Z)", body, re.S)
    return m.group(1).strip() if m else ""


def correction_entries(text: str | None = None) -> list[dict[str, Any]]:
    text = CORRECTION_LOG.read_text(encoding="utf-8") if text is None else text
    heads = list(ENTRY_HEADING.finditer(text))
    entries = []
    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        produced = _field(body, "What was produced")
        caught = _field(body, "How it was caught")
        origin = "Claude Chat" if "Claude Chat" in produced else "Claude Code"
        how = next(label for label, pat in CAUGHT_RULES if re.search(pat, caught, re.I | re.S))
        entries.append({"date": h.group(1), "sprint": int(h.group(2)), "title": h.group(3), "origin": origin, "caught_by": how})
    return entries


def correction_stats() -> dict[str, Any]:
    entries = correction_entries()
    return {
        "source": "ai-workflow/correction-log.md",
        "n_entries": len(entries),
        "by_origin": dict(Counter(e["origin"] for e in entries)),
        "by_caught": dict(Counter(e["caught_by"] for e in entries)),
        "by_sprint": {str(k): v for k, v in sorted(Counter(e["sprint"] for e in entries).items())},
        "caught_rules": [{"label": label, "pattern": pat} for label, pat in CAUGHT_RULES],
        "origin_rule": "Claude Chat if the 'What was produced' field names Claude Chat, otherwise Claude Code",
        "entries": entries,
    }


def workflow_files() -> list[str]:
    return sorted(p for p in _git("ls-files", "ai-workflow").split() if p.endswith(".md"))


def record() -> dict[str, Any]:
    return {"timeline": timeline(), "correction_log": correction_stats(), "workflow_files": workflow_files()}
