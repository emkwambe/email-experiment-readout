# LiftLab — Sprint 1: Pre-Registration, Data Gates, First Deploy

You are implementing Sprint 1 of LiftLab. Read `C:\dev\liftlab-email-experiment\CLAUDE.md` and `C:\dev\liftlab-email-experiment\docs\analysis-plan.md` in full before doing anything. Both are binding. The outcome lock in CLAUDE.md rule 2 applies for this entire sprint.

**Sprint goal:** a public site that shows the locked analysis plan and the passing (or failing) data-quality gates, with zero outcome results by arm. This proves the plan was fixed before results were seen.

Work through the steps in order. Stop and report if any step fails; do not work around a failure silently.

## Step 1 — Pre-registration commit (do this first, before any code)

1. `git init` in `C:\dev\liftlab-email-experiment`.
2. Create `.gitignore` covering `analysis\.venv\`, `data\raw\`, `__pycache__\`, `.pytest_cache\`, `web\node_modules\`, `web\.next\`, `web\.vercel\`, `.env*`.
3. Commit exactly these files with message `pre-registration: analysis plan and project conventions (before data access)`:
   - `CLAUDE.md`
   - `docs\analysis-plan.md`
   - `ai-workflow\sprint-1.md`
   - `ai-workflow\correction-log.md`
   - `.gitignore`
4. Report the commit SHA. It goes into the README later as the pre-registration reference.

## Step 2 — Python scaffold

Create `analysis\` as an installable package `liftlab` with `requirements.txt` pinning versions of: pandas, numpy, scipy, statsmodels, scikit-learn, duckdb, pytest, and scikit-uplift. Create the venv and install with the commands in CLAUDE.md.

If `scikit-uplift` fails to install or import on this Python version, record that in the correction log and implement the fallback in Step 3 instead. Do not downgrade Python silently.

## Step 3 — Data loader with provenance

Implement `liftlab/load.py`:

- Primary path: obtain the Hillstrom dataset via scikit-uplift's `fetch_hillstrom`. Inspect its signature and actual behavior first; confirm you get all original columns including `segment`, `visit`, `conversion`, and `spend`.
- Fallback path: download the original MineThatData CSV from its canonical public source. Find and verify the URL; do not guess.
- Save the raw file to `data\raw\hillstrom.csv`. Compute its SHA-256.
- Write `docs\data-source.md` recording source, URL, retrieval UTC date, SHA-256, row count, column list, and the dataset's origin (Kevin Hillstrom, MineThatData E-Mail Analytics and Data Mining Challenge, 2008).
- Return a typed DataFrame with categoricals set for `segment`, `history_segment`, `zip_code`, `channel`.

Do not print or compute any outcome aggregate by `segment`.

## Step 4 — Data quality gates

Implement `liftlab/checks.py` exactly as specified in analysis-plan Section 5:

- `integrity(df)` → every gate as a named boolean plus counts.
- `srm(df)` → observed counts per arm, expected counts, chi-square statistic, p-value, `halt` flag at p < 0.001.
- `balance(df)` → SMD for every pre-period covariate (categoricals one-hot), for each email arm vs No E-Mail, with `flag` at |SMD| > 0.1.

Implement `liftlab/power.py` for planning, using only arm sizes and **assumed** parameter grids (never observed outcomes):

- Minimum detectable effect for a difference in proportions at baseline rates {0.005, 0.01, 0.02} (conversion) and {0.10, 0.15, 0.20} (visit).
- Minimum detectable difference in revenue per customer across an assumed standard-deviation grid {$5, $10, $15, $20, $30}.
- Use α = 0.025 per test (a conservative bound for Holm across two primary contrasts) and power 0.80. Label every value as based on assumed parameters.

## Step 5 — Tests

In `analysis\tests\` write tests that:

- Assert every integrity gate passes and the row count is 64,000.
- Verify the SRM function against a hand-constructed example with a known chi-square result, then assert the real data's SRM result is present and well-formed.
- Verify SMD on a synthetic example with a known answer.
- Verify MDE against an independent calculation (for example, statsmodels power functions vs your closed form).
- **Guard the outcome lock:** assert that no Sprint 1 export JSON contains any key or value derived from `visit`, `conversion`, or `spend` grouped by arm.

## Step 6 — Export with manifest

Implement `liftlab/run.py` with `--stage sprint1` that runs the loader, gates, and power grid and writes to `web\public\data\`:

- `integrity.json`, `srm.json`, `balance.json`, `power.json`, each with a `manifest` block (commit SHA, dataset SHA-256, UTC timestamp, script, seed).
- `manifest.json` summarizing all exports.

## Step 7 — Web scaffold

Create `web\` with Next.js 15 (App Router), TypeScript strict, and Tailwind. Pages:

- `/` — the business question in one paragraph, a status badge reading "Pre-registered · outcomes locked," a link to the pre-registration commit on GitHub, and links to the pages below.
- `/plan` — renders `docs\analysis-plan.md` (copy it into the web app at build time; do not duplicate by hand).
- `/checks` — integrity gates as pass/fail, the SRM result, a balance table with flagged rows highlighted, and the MDE tables clearly labeled "planning values from assumed parameters."
- `/how-its-built` — a short page explaining the Claude Code workflow (plan in chat, execute in Claude Code, verify by tests), linking to `ai-workflow\` on GitHub and to the correction log.

Design: clean, readable, and responsive, with a light/dark theme. Every number is read from `public\data\*.json`; none are hardcoded.

## Step 8 — Smoke test and deploy

Add `web\scripts\smoke.mjs` and an `npm run smoke` script. It reads `SMOKE_URL` (default: the production URL once known) and checks:

- `/`, `/plan`, `/checks`, `/how-its-built` return 200.
- `/data/manifest.json` loads and its dataset SHA-256 matches `docs\data-source.md`.
- `/data/srm.json` has a numeric p-value.

Deploy with `vercel deploy --prod --cwd C:\dev\liftlab-email-experiment\web`, then run the smoke test against the production URL.

## Step 9 — Repo presentation

Write `README.md`:

- The one-line pitch.
- The live URL.
- The pre-registration commit SHA with a link.
- Current status (Sprint 1 of 3).
- A "How this was built with Claude Code" section linking to `ai-workflow\` and the correction log.
- Exact reproduction commands.

Create the GitHub repo `emkwambe/liftlab-email-experiment` (public), push, and set the repo website field to the production URL.

## Definition of Done

- [ ] Pre-registration commit exists and precedes every commit containing loader code
- [ ] `docs\data-source.md` records source, SHA-256, and 64,000 rows
- [ ] All tests pass; report the exact pytest summary line
- [ ] SRM and balance results exported with manifests; report the SRM p-value and any flagged covariates from the JSON
- [ ] Outcome-lock test passes; no by-arm outcome numbers exist anywhere in the repo or site
- [ ] Site live at the production URL with all four pages
- [ ] `npm run smoke` passes against production; report its output
- [ ] Correction log updated with every error caught this sprint (or an explicit "none caught" entry with the checks that were run)
- [ ] README complete, repo public, website field set

## Final report format

End the sprint with a short report containing:

- the commits made, with SHAs;
- test and smoke output verbatim;
- the production URL;
- the SRM p-value and balance flags as read from the JSON;
- the correction log entries added;
- anything you were unsure about or that needs a human decision before Sprint 2.
