# Correction Log

This log records every place where AI-generated work (Claude Code or Claude Chat) was wrong, incomplete, or overconfident, and how the error was caught. It exists because the value of AI-assisted analysis depends on the verification around it, and that verification should be visible.

Each entry is added in the same commit as its fix.

## Entry format

**YYYY-MM-DD · Sprint N · short title**
- **What was produced:** what the AI generated.
- **What was wrong:** the specific error.
- **How it was caught:** which test, check, gate, or human review found it.
- **Fix:** what changed; commit SHA.
- **Lesson / guard added:** a new test or rule, if any, that prevents recurrence.

## Entries

**2026-09-23 · Sprint 1 · CLAUDE.md specified a Python runtime that was not installed**
- **What was produced:** During planning, Claude Chat wrote CLAUDE.md with `py -3.12 -m venv ...` as the environment setup command.
- **What was wrong:** Nobody checked which Python runtimes were installed. The machine had only 3.13 and 3.11, so `py -3.12` failed with "No suitable Python runtime found."
- **How it was caught:** Claude Code ran `py -0p` at the start of Sprint 1 Step 2, stopped, and reported the failure instead of switching to another Python version.
- **Fix:** Python 3.12.10 was installed with `winget install -e --id Python.Python.3.12`, and `py -0p` confirmed it was registered. The spec was left unchanged. Committed with the Step 2 scaffold.
- **Lesson / guard added:** Every future sprint file must include an environment preflight step (`py -0p`, `node -v`, `vercel --version`, `gh auth status`) before any setup commands.

**2026-09-23 · Sprint 1 · Editable install line in requirements.txt resolved against the wrong directory**
- **What was produced:** Claude Code added `-e .` to `analysis\requirements.txt` so that the one CLAUDE.md install command would also install the `liftlab` package.
- **What was wrong:** pip resolves relative paths in a requirements file against the current working directory, not the file's location. CLAUDE.md forbids `cd`, so the command tried to install `C:\Users\HP` as a project and failed.
- **How it was caught:** Before committing, Claude Code ran the install from a directory outside the repo and got `does not appear to be a Python project`.
- **Fix:** Removed `-e .` from `requirements.txt`. Added one absolute-path command to the CLAUDE.md Commands section: `python.exe -m pip install -e C:\dev\liftlab-email-experiment\analysis`. Both commands were re-verified from outside the repo, and `import liftlab` succeeded. Committed with the Step 2 scaffold.
- **Lesson / guard added:** Test setup commands from a directory other than the repo root, because a relative path can pass by accident when run from the repo.

**2026-09-23 · Sprint 1 · Unverified explanation of the dataset hash difference**
- **What was produced:** Claude Code's draft of `docs\data-source.md` said the local file's SHA-256 differed from the canonical MineThatData CSV "because the canonical file uses CRLF line endings and the loader re-serialises the data with pandas."
- **What was wrong:** Only half of that was right. Claude Code then compared the files directly and found the loader changes nothing: the local file is byte-identical to the decompressed scikit-uplift mirror. The byte differences are between the mirror and the canonical file: CRLF line endings, and integer-valued `spend` written as `0.0` in the mirror. The first explanation had not been checked.
- **How it was caught:** Before committing, Claude Code checked its own claim. It stripped CR from the canonical file and diffed it against the local file (they still differed on `0` vs `0.0`), then hashed the decompressed mirror (`00a6a868…`, the same as the local file).
- **Fix:** The cross-check is now computed in code (`liftlab.load.cross_check`): mirror byte identity, the canonical file's SHA-256, and parsed-content identity. The doc renders those results, and the prose explanation matches what was observed. Committed with the Step 3 loader.
- **Lesson / guard added:** Any claim in a generated doc about why two artifacts differ must be backed by a check the code runs, not stated from inference.

**2026-09-23 · Sprint 1 · Hand-typed numbers in website copy (rule 1)**
- **What was produced:** In its first draft of the web pages, Claude Code wrote the integrity-gate label "Row count equals the documented 64,000" and the home-page sentence "randomly split … customers into three groups".
- **What was wrong:** Both put a number on the site that did not come from a JSON export, which CLAUDE.md rule 1 forbids. The customer count in the same sentence was already read from `integrity.json`; the gate label and the group count were not.
- **How it was caught:** Claude Code reviewed its own web code against rule 1 before the first build, looking for literal numbers in the page and label files.
- **Fix:** `integrity.json` now exports `expected_row_count`. The gate label reads "documented population size", and the page shows both counts from JSON. The group count is computed from the arms in `srm.json`. Committed with the Step 7 web scaffold.
- **Lesson / guard added:** Review every web page and label file for literal numbers before building. The one intentional exception is `web/content/analysis-plan.md`, which is the locked plan rendered verbatim; a test checks that it is byte-identical to `docs/analysis-plan.md`.

**2026-09-23 · Sprint 1 · Display defects on /checks**
- **What was produced:** Claude Code's first version of `/checks`.
- **What was wrong:** Gate names showed literal Markdown backticks (`` `zip_code` contains only… ``). The power banner said "Planning values from assumed parameters" twice. On narrow screens the header nav did not wrap and pushed the page wider than the viewport.
- **How it was caught:** Claude Code reviewed headless-browser screenshots of the locally built site before deploying.
- **Fix:** Plain-text gate labels in `web/lib/labels.ts`, a single banner heading taken from `power.json`'s `label`, and a wrapping header. Re-checked with a 540 px screenshot. Committed with the Step 7 web scaffold follow-up.
- **Lesson / guard added:** Take a screenshot of every page at desktop width and at narrow width before each deploy. Headless Edge can't render below about 500 px, so a true phone-width check needs device emulation.

**2026-09-23 · Sprint 2 · Balance SMD used sample variance for binary covariates**
- **What was produced:** In Sprint 1, Claude Code's `checks.smd` used the sample variance (ddof = 1) for every covariate, and its unit test encoded that choice (`0.25 * sqrt(24/7)` for a binary example).
- **What was wrong:** The standard definition uses p(1−p) for binary covariates (`mens`, `womens`, `newbie` and every one-hot dummy), not the sample variance, which is larger by a factor of n/(n−1). The Sprint 1 test checked the formula as implemented, so it could not catch a wrong choice of formula. With roughly 21,000 customers per group the numerical effect is tiny: the largest |SMD| moved from 0.0163595 to 0.0163599, and 0 covariates were flagged before and after.
- **How it was caught:** Human review. The Sprint 2 brief (Step 0.3) asked Claude Code to confirm the formula, and the implementation did not match the binary case.
- **Fix:** `smd(..., binary=True)` uses p(1−p); `is_binary_covariate` classifies each covariate, and `balance.json` records each row's `type`. A new hand-computed test gives 0.25 / sqrt(7/32) = 0.5345224838 for binary data. The continuous case keeps its own test. The Sprint 1 exports are regenerated in the commit after this one, from a clean tree.
- **Lesson / guard added:** A unit test must check against a reference definition that exists independently of the implementation, not the implementation's own arithmetic.

**2026-09-23 · Sprint 2 · Tables clipped at true phone width on /checks**
- **What was produced:** Claude Code's `/checks` tables, which Sprint 1 could only verify at 540 px.
- **What was wrong:** At 390 px with device emulation, arm names broke at the hyphen ("Mens E- / Mail"), the MDE column headers wrapped onto three lines, and after a first fix the SRM table was clipped inside its scroll container (the Share column was cut off). The page-level overflow check passed throughout, because the clipping was inside the table's own scroll box.
- **How it was caught:** Claude Code reviewed Playwright 390×844 screenshots (Sprint 2, Step 0.5).
- **Fix:** Arm names kept on one line, MDE headers shortened (the contrast moved into the table caption), secondary annotations on their own line, and tighter cell padding below the `sm` breakpoint. Also fixed in the same pass: `/plan` now renders the author's single line breaks (`remark-breaks`), so "Author" and "Status", and H1/H2/H3, are no longer merged into one paragraph.
- **Lesson / guard added:** `npm run screenshots` now also fails when any horizontal scroll container on a page is clipped. It was confirmed to fail on the old build before the fix.

**2026-09-23 · Sprint 2 · Plan specified a four-cell mens × womens crossing that the population cannot contain**
- **What was produced:** During planning, Claude Chat wrote analysis-plan Section 8, dimension 1: "Prior merchandise purchase (`mens`, `womens` flags, crossed into four groups)." The Sprint 2 brief repeated it.
- **What was wrong:** The neither/neither cell cannot exist. The data documentation defines the population as customers who purchased within the prior twelve months, so each has bought men's or women's merchandise or both. This was knowable from the documentation alone, before any data access. The data confirms it: 0 customers have `mens=0, womens=0`.
- **How it was caught:** Claude Code's covariate-only pre-check (cell counts of `mens` × `womens`, overall and by arm) before any effect estimate was computed. It stopped and reported the discrepancy while no outcome results were visible.
- **Fix:** A dated Deviations entry in `docs/analysis-plan.md` makes dimension 1 three levels (2 interaction df), keeps the Holm family at 8 tests, and records all Sections 6–8 method clarifications before any estimate. Committed on its own, before `effects.py` exists.
- **Lesson / guard added:** Future plans must check categorical cell structure against the data documentation (population definition, possible combinations of levels) before specifying crossings.
