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

**2026-09-23 · Sprint 2 · Chart axis labels misstated tick values on /results**
- **What was produced:** In its first draft of `/results`, Claude Code's dollar-axis formatter wrote non-integer ticks with one decimal place.
- **What was wrong:** With a tick step of $0.25, the ticks $0.25, $0.75 and $1.25 were labelled "$0.3", "$0.8" and "$1.3", so the axis misstated where the intervals sit. Every number in the text and tooltips was correct; only the axis labels were wrong.
- **How it was caught:** Claude Code reviewed a desktop screenshot of the locally built page before any commit or deploy.
- **Fix:** Tick labels now use as many decimals as the ticks need (at least two when any tick is fractional, so "$0.25" and "$0.50"). `niceDomain` also rounds ticks to 12 significant digits, so floating-point noise such as 0.30000000000000004 cannot force a long label. Also fixed in the same review: secondary-metric table cells wrapped mid-number at 390 px. Committed with the Sprint 2 web page.
- **Lesson / guard added:** Check chart axes in screenshots against the tick values in the data, not only the plotted marks.

**2026-09-24 · Sprint 3 · Planned winner selection would have chosen k on the same holdout used to judge it**
- **What was produced:** During planning, Claude Chat wrote Sprint 3 Step 1 so that P4a and P4b each spanned 10 top-k variants (k = 10…100), with the winner being the highest holdout net value among all targeted policies.
- **What was wrong:** Choosing the best of 20 k-variants on the same holdout that then estimates the winner's value, and its paired CI against blanket sending, inflates both (the winner's curse). The comparison would have looked more favourable to targeting than the data supports.
- **How it was caught:** Claude Code flagged it as a plan ambiguity while reviewing Sprint 3 Step 1, before any split, model or policy value existed.
- **Fix:** k is now selected for each arm by 5-fold CV net value on the training split. The holdout compares exactly seven pre-selected policies (P0, P1, P2, P3, P4a, P4b, P5), and the holdout net-value-vs-k curves are descriptive only. This is recorded in the 2026-09-24 Deviations entry, committed before the split.
- **Lesson / guard added:** Every tuning choice, including thresholds such as k, is made on training data only. The holdout data layer raises an error outside `liftlab/evaluate.py`.

**2026-09-24 · Sprint 3 · First split module exposed holdout indices around the guard**
- **What was produced:** Claude Code's first `liftlab/split.py`, its tests, and a `run.py` change.
- **What was wrong:** Three leaks, all before any model existed.
  1. The public function `make_split` returned the holdout indices to any caller, so training code could have bypassed the `SplitData.holdout()` guard.
  2. `run.py` wrote the holdout hash into the `manifest.json` summary, putting a split key into a non-targeting export.
  3. That also put holdout references into `run.py`, which is not one of the four targeting modules named in CLAUDE.md rule 9.
- **How it was caught:** Leak 1 was caught by Claude Code's review of its own test code, which recomputed the split through the unguarded function. Leaks 2 and 3 were caught by the updated rule 9 guard tests (`test_no_targeting_or_policy_output_outside_targeting_exports` and `test_targeting_code_only_in_named_modules`) in the dry run before the seal commit.
- **Fix:**
  - The split function is now private (`_make_split`). The public API returns only the holdout hash (`holdout_index_sha256`) and the training indices.
  - A source-scan test fails if any module other than `split.py` and `evaluate.py` references the private internals.
  - The manifest summary line was removed; the hash lives only in `split.json`.
  - The single holdout evaluation gets its own entry point in `evaluate.py` instead of `run.py`.
- **Lesson / guard added:** An access guard is only as strong as the public API around it. Check every public function for a path that returns guarded data.

**2026-09-24 · Sprint 3 · Qini test asserted a guessed threshold instead of a derived value**
- **What was produced:** Claude Code's first synthetic Qini test asserted that a perfectly ranked coefficient should exceed 0.2 dollars per customer.
- **What was wrong:** The threshold was a guess. For uplift τ ~ U(0, 2) with half the customers treated, the expected coefficient is exactly 1/12 ≈ 0.083 per customer, so the test failed (observed 0.0755) even though the Qini code was correct.
- **How it was caught:** The test failed on its first run, and Claude Code derived the analytic value before changing anything.
- **Fix:** The test now asserts the derived value (1/12 ± 0.01, n = 40,000) and that a random ranking is near zero. The Qini code was unchanged. Committed with the Step 3 training code.
- **Lesson / guard added:** A synthetic test asserts a derived expectation, never a guessed bound. A guessed bound can hide a bug as easily as it can flag correct code.

**2026-09-24 · Sprint 3 · Rule-9 guard test is lexical and flagged a non-targeting module (guard-design limitation)**
- **What was produced:** Claude Code's Sprint 2 rule-9 guard test (`test_targeting_code_only_in_named_modules`), which scans module source for targeting vocabulary such as "holdout" and "qini", and the Sprint 3 `liftlab/meta.py` that builds the git timeline.
- **What was wrong:** The test matches words, not behaviour. It flagged `meta.py` because the module names the "holdout sealed" and "holdout evaluated" milestones and the export paths it looks up in `git log`. `meta.py` never touches the dataset, the split or any model. This was a false positive caused by how the guard was designed; no holdout protection was breached.
- **How it was caught:** The guard test failed in the Step 7 dry run. Claude Code stopped at the guard violation and the human owner chose the fix (human review).
- **Fix:**
  - `meta.py` is allowlisted in CLAUDE.md rule 9 as a read-only workflow-record module.
  - It no longer imports anything from `liftlab`: it computes the repo root itself instead of importing the data-access layer.
  - `tests/test_meta.py` now fails if `meta.py` imports pandas, numpy or any `liftlab` module (split, models, evaluate, decision, load, run), statically or at import time, or opens any path under `data/` while building the record (runtime spy on `open`).
- **Lesson / guard added:** A lexical scan is a tripwire, not the protection. The authoritative holdout protection is the data-access layer, where `SplitData.holdout()` raises outside `evaluate.py`. Modules that only need to name the holdout get an explicit import-and-access test, not a vocabulary exemption.

**2026-09-24 · Sprint 3 · Commit bbeb180 was made with a failing test because the gate checked the wrong exit code**
- **What was produced:** Claude Code's shell chain for the Step 7 commit: `pytest ... | tail -1 && git add ... && git commit ...`.
- **What was wrong:** In a pipeline without `pipefail`, the exit status is that of `tail`, not pytest. pytest reported `1 failed, 121 passed` (the exported `timeline.json` counted 12 correction entries while the log had 13), but the chain went ahead and committed `bbeb180` anyway. The failure was expected staleness, fixed by the clean export commit `e128110`, but the commit gate itself was broken and would have let a real failure through.
- **How it was caught:** Claude Code noticed the "1 failed" summary line above its own commit output. Human review then asked for a correction-log entry rather than only a note in the verification file.
- **Fix:** Every commit is now gated on pytest's own exit status. Bash commands run with `set -euo pipefail` (or check `PIPESTATUS`), and PowerShell commands capture `$LASTEXITCODE` from pytest before any pipe and commit only when it is 0, as for `e128110`. `timeline.json` is regenerated after this entry so its statistics match the log.
- **Lesson / guard added:** Never let a pipe decide whether to commit. Gate commits on the test runner's own exit code.

**2026-09-24 · v1.0.1 · Funnel interpretation on the readout was contradicted by the data**
- **What was produced:** Claude Chat's Sprint 3 brief framed readout Section 5 as a question for the landing-experience owner, and Claude Code wrote it as: "the emails brought many more customers to the site than they turned into buyers."
- **What was wrong:** The data says the opposite. Both emails lifted visits and purchases. Relative to no email, the point estimate of the purchase lift is larger than the visit lift for both emails (Mens +119% vs +72%; Womens +54% vs +43%, from `effects_secondary.json` relative lifts). Among visitors, emailed customers bought at 6.9% (Mens) and 5.8% (Womens) against 5.4% without email (descriptive only). The sentence compared absolute percentage-point changes on very different bases, which made purchases look like the weak link. It was an interpretive error that originated in Claude Chat.
- **How it was caught:** Human review of the live readout. It survived three sprints because the tests verified every number against independent computations, but nothing checked that the conclusions drawn from those numbers followed from them.
- **Fix (v1.0.1):**
  - `effects_secondary.json` now exports delta-method relative lifts for visits and purchases, labelled supplementary and not pre-registered, and the purchase rate among visitors, marked `descriptive_only` with the post-treatment selection caveat.
  - Section 5 is rewritten from those fields. Its sentences are generated conditionally from them, and the ordering claim is qualified because the intervals overlap.
  - The landing-experience question is removed; the exports do not support it.
  - Sections 2, 3 and 6 also gained explicit source lines.
- **Lesson / guard added:** Every interpretive sentence on the site must cite the specific exported fields that support it (a "Sources" line under each section of the readout), and review checks each sentence against those fields, not just the numbers.
