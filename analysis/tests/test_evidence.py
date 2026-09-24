"""Evidence image policy (Sprint 3, Step 0.2): no committed evidence image may exceed 300 KB.

Checks both the committed tree (HEAD) and the index, so a staged oversize image fails before commit.
Full-resolution screenshots live in the gitignored ai-workflow/evidence/full/.
"""

from __future__ import annotations

import subprocess

from liftlab import load

LIMIT_BYTES = 300 * 1024
IMAGE_SUFFIXES = (".png", ".webp", ".jpg", ".jpeg", ".gif")
EVIDENCE = "ai-workflow/evidence"


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(load.REPO_ROOT), *args], check=True, capture_output=True, text=True).stdout


def _blob_sizes(entries: list[tuple[str, str]]) -> dict[str, int]:
    shas = "\n".join(sha for sha, _ in entries) + "\n"
    out = subprocess.run(["git", "-C", str(load.REPO_ROOT), "cat-file", "--batch-check=%(objectsize)"],
                         input=shas, check=True, capture_output=True, text=True).stdout.split()
    return {path: int(size) for (_, path), size in zip(entries, out)}


def evidence_images() -> dict[str, int]:
    committed = [(line.split()[2], line.split("\t", 1)[1]) for line in _git("ls-tree", "-r", "HEAD", "--", EVIDENCE).splitlines()]
    staged = [(line.split()[1], line.split("\t", 1)[1]) for line in _git("ls-files", "-s", "--", EVIDENCE).splitlines()]
    entries = [(sha, p) for sha, p in committed + staged if p.lower().endswith(IMAGE_SUFFIXES)]
    return _blob_sizes(entries) if entries else {}


def test_no_evidence_image_exceeds_300_kb() -> None:
    oversize = {p: s for p, s in evidence_images().items() if s > LIMIT_BYTES}
    assert not oversize, f"evidence images over {LIMIT_BYTES} bytes: {oversize}"


def test_full_resolution_output_is_ignored() -> None:
    assert _git("check-ignore", "-q", "--no-index", f"{EVIDENCE}/full/x.png") == ""
