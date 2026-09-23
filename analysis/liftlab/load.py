"""Obtain the Hillstrom MineThatData dataset, record provenance, and return a typed DataFrame.

The loader never aggregates outcome columns (outcome lock, CLAUDE.md rule 2).
"""

from __future__ import annotations

import gzip
import hashlib
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DIR: Path = REPO_ROOT / "data" / "raw"
RAW_CSV: Path = RAW_DIR / "hillstrom.csv"
SKLIFT_CACHE: Path = RAW_DIR / "sklift_cache"
CANONICAL_CSV: Path = RAW_DIR / "canonical_minethatdata.csv"
DATA_SOURCE_DOC: Path = REPO_ROOT / "docs" / "data-source.md"

SKLIFT_MIRROR_URL: str = "https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz"
CANONICAL_URL: str = (
    "http://www.minethatdata.com/"
    "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)
PUBLISHER_POST_URL: str = (
    "https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html"
)

FEATURE_COLUMNS: list[str] = [
    "recency", "history_segment", "history", "mens", "womens", "zip_code", "newbie", "channel",
]
TREATMENT_COLUMN: str = "segment"
OUTCOME_COLUMNS: list[str] = ["visit", "conversion", "spend"]
COLUMNS: list[str] = FEATURE_COLUMNS + [TREATMENT_COLUMN] + OUTCOME_COLUMNS
CATEGORICAL_COLUMNS: list[str] = ["segment", "history_segment", "zip_code", "channel"]


@dataclass(frozen=True)
class RawFile:
    path: Path
    sha256: str
    source: str
    url: str
    retrieved_utc: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_raw(force: bool = False) -> RawFile:
    """Download via scikit-uplift's fetch_hillstrom and write data/raw/hillstrom.csv.

    fetch_hillstrom verifies the mirror file's MD5 before returning. The Bunch it returns
    splits features, treatment and targets; we reassemble them in the original column order.
    """
    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if force or not RAW_CSV.exists():
        from sklift.datasets import fetch_hillstrom

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        bunch = fetch_hillstrom(target_col="all", data_home=str(SKLIFT_CACHE))
        df = pd.concat([bunch.data, bunch.treatment, bunch.target], axis=1)[COLUMNS]
        df.to_csv(RAW_CSV, index=False, lineterminator="\n")
    return RawFile(
        path=RAW_CSV,
        sha256=sha256_file(RAW_CSV),
        source="scikit-uplift fetch_hillstrom (sklift 0.5.1)",
        url=SKLIFT_MIRROR_URL,
        retrieved_utc=retrieved,
    )


def read_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    """Read the raw CSV without any type coercion beyond pandas defaults."""
    return pd.read_csv(path)


def to_typed(raw: pd.DataFrame) -> pd.DataFrame:
    """Set categorical dtypes. Levels are taken verbatim from the data; nothing is recoded."""
    df = raw[COLUMNS].copy()
    df["history_segment"] = pd.Categorical(
        df["history_segment"], categories=sorted(df["history_segment"].unique()), ordered=True
    )
    for col in ["segment", "zip_code", "channel"]:
        df[col] = pd.Categorical(df[col], categories=sorted(df[col].unique()))
    for col in ["recency", "mens", "womens", "newbie", "visit", "conversion"]:
        df[col] = df[col].astype("int64")
    for col in ["history", "spend"]:
        df[col] = df[col].astype("float64")
    return df


def load() -> pd.DataFrame:
    """Return the typed dataset, fetching it first if absent."""
    fetch_raw()
    return to_typed(read_raw())


@dataclass(frozen=True)
class CrossCheck:
    mirror_gz_sha256: str
    local_equals_mirror_bytes: bool
    canonical_sha256: str
    canonical_content_identical: bool


def fetch_canonical(dest: Path = CANONICAL_CSV) -> Path:
    """Download the publisher's original CSV (used only to cross-check the mirror)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(CANONICAL_URL, dest)
    return dest


def cross_check(canonical_csv: Path = CANONICAL_CSV) -> CrossCheck:
    """Compare the local file to the sklift mirror (bytes) and to the canonical CSV (parsed content)."""
    mirror_gz = SKLIFT_CACHE / "hillstorm_no_indices.csv.gz"
    with gzip.open(mirror_gz, "rb") as f:
        mirror_bytes = f.read()
    return CrossCheck(
        mirror_gz_sha256=sha256_file(mirror_gz),
        local_equals_mirror_bytes=mirror_bytes == RAW_CSV.read_bytes(),
        canonical_sha256=sha256_file(canonical_csv),
        canonical_content_identical=read_raw(canonical_csv).equals(read_raw(RAW_CSV)),
    )


def write_data_source_doc(raw: RawFile, xc: CrossCheck) -> str:
    """Render docs/data-source.md from computed values only."""
    df = read_raw(raw.path)
    yes_no = {True: "yes", False: "**NO — investigate before use**"}
    zip_levels = ", ".join(f'"{v}"' for v in sorted(df["zip_code"].unique()))
    cols = "\n".join(f"| `{c}` | {df[c].dtype} |" for c in df.columns)
    text = f"""# Data source

*Generated by `liftlab.load.write_data_source_doc`; do not edit by hand.*

## Origin

Kevin Hillstrom, **MineThatData E-Mail Analytics and Data Mining Challenge** (March 2008).
Publisher post: {PUBLISHER_POST_URL}

## Retrieval

| Field | Value |
|---|---|
| Method | {raw.source} |
| URL | {raw.url} |
| Retrieved (UTC) | {raw.retrieved_utc} |
| Local file | `data/raw/hillstrom.csv` (gitignored) |
| SHA-256 | `{raw.sha256}` |
| Rows | {df.shape[0]:,} |
| Columns | {df.shape[1]} |

`fetch_hillstrom` verifies the mirror's MD5 before returning. The loader reassembles the
returned features, treatment and targets in the original column order and writes the CSV
with `\\n` line endings.

## Cross-check against the canonical source

Canonical CSV (linked from the publisher post): {CANONICAL_URL}

| Check | Result |
|---|---|
| sklift mirror `.csv.gz` SHA-256 | `{xc.mirror_gz_sha256}` |
| Local file byte-identical to the decompressed mirror | {yes_no[xc.local_equals_mirror_bytes]} |
| Canonical CSV SHA-256 (as downloaded) | `{xc.canonical_sha256}` |
| Parsed content identical to the canonical CSV ({df.shape[0]:,}×{df.shape[1]}, same column order) | {yes_no[xc.canonical_content_identical]} |

The canonical and mirror files differ at the byte level (the canonical file uses CRLF line
endings; the mirror writes integer-valued `spend` as `0.0`), so their hashes differ even
though the parsed data are identical. The SHA-256 above in *Retrieval* is the one every
export manifest references.

## Columns

| Column | Raw dtype |
|---|---|
{cols}

## Source-data notes

- `zip_code` levels in the file: {zip_levels}. The publisher post documents them as
  "Urban, Suburban, or Rural". The loader keeps the file's spelling and does not recode it.
"""
    DATA_SOURCE_DOC.write_text(text, encoding="utf-8", newline="\n")
    return text


def main() -> None:
    raw = fetch_raw(force=True)
    fetch_canonical()
    xc = cross_check()
    write_data_source_doc(raw, xc)
    print(f"wrote {DATA_SOURCE_DOC} sha256={raw.sha256} cross_check={xc}")


if __name__ == "__main__":
    main()
