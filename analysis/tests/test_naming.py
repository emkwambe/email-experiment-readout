"""v1.0.2 rename guard: the retired name "LiftLab" appears in public-facing files only to explain the rename.

Historical records (commit messages, past correction-log entries, sprint briefs, verification files) and the locked
analysis plan are deliberately excluded. The internal Python package name `liftlab` is lowercase and not matched.
"""

from __future__ import annotations

import re

from liftlab import load

ROOT = load.REPO_ROOT
PUBLIC = [ROOT / "README.md", ROOT / "CLAUDE.md"] + [
    p for d in ("web/app", "web/lib", "web/scripts", "analysis/liftlab") for p in (ROOT / d).rglob("*")
    if p.suffix in {".ts", ".tsx", ".mjs", ".py", ".md"}
]
NEW_SITE = "https://email-experiment-readout.vercel.app"
FOOTER = "An analytics case study built with Claude Code by Eddy Mkwambe."


def test_retired_name_only_explains_the_rename() -> None:
    offenders = []
    for path in PUBLIC:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"LiftLab", line) and "LiftLab Analytics" not in line:
                offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert not offenders, offenders


def test_readme_names_the_rename_and_footer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# Email Experiment Readout\n")
    assert "Formerly named LiftLab; renamed to avoid confusion with LiftLab Analytics, Inc." in readme
    assert readme.rstrip().endswith(FOOTER)
    assert "liftlab-email-experiment.vercel.app" not in readme


def test_site_footer_and_default_urls() -> None:
    assert FOOTER in (ROOT / "web/app/layout.tsx").read_text(encoding="utf-8")
    for script in ("smoke.mjs", "screenshots.mjs"):
        assert NEW_SITE in (ROOT / "web/scripts" / script).read_text(encoding="utf-8")
    assert "github.com/emkwambe/email-experiment-readout" in (ROOT / "web/lib/format.ts").read_text(encoding="utf-8")
