# CLAUDE.md — Email Experiment Readout (repo: email-experiment-readout; local folder: liftlab-email-experiment)

## What this project is

Email Experiment Readout (formerly named LiftLab; renamed to avoid confusion with LiftLab Analytics, Inc.) is a public portfolio project that analyzes a real randomized email experiment (the Kevin Hillstrom MineThatData dataset, 64,000 customers, three arms) to answer one business question: did the emails generate incremental revenue, which email, and for which customers should the team send each email next time?

It is also an explicit record of how Claude Code was used to build it. The `ai-workflow/` folder is a deliverable, not scratch space. Treat it with the same care as the code.

## Repo layout

```
C:\dev\liftlab-email-experiment\
  CLAUDE.md
  README.md
  docs\analysis-plan.md          pre-registered plan (locked; changes go in its Deviations section only)
  docs\data-source.md            provenance: source URL, retrieval date, SHA-256, row count
  ai-workflow\                   sprint prompts, correction log, verification evidence
  analysis\                      Python package, tests, scripts
    liftlab\                     importable modules (load, validate, checks, effects, uplift, export)
    tests\
    .venv\                       local only, gitignored
  data\raw\                      gitignored; downloaded dataset lives here
  web\                           Next.js 15 + TypeScript + Tailwind readout site
    public\data\                 JSON results exported by analysis (committed)
```

## Commands (Windows PowerShell, absolute paths only)

```powershell
# Python env
py -3.12 -m venv C:\dev\liftlab-email-experiment\analysis\.venv
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -r C:\dev\liftlab-email-experiment\analysis\requirements.txt
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -e C:\dev\liftlab-email-experiment\analysis

# Tests
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pytest C:\dev\liftlab-email-experiment\analysis\tests -q

# Run the pipeline and export JSON to web\public\data
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.run --stage sprint1

# Web
npm --prefix C:\dev\liftlab-email-experiment\web run build
vercel deploy --prod --cwd C:\dev\liftlab-email-experiment\web
npm --prefix C:\dev\liftlab-email-experiment\web run smoke
```

Never write commands that require `cd` first. All file writes are UTF-8 without BOM.

## Non-negotiable rules

1. **No uncomputed numbers.** Every number that appears on the website, in the README, or in any doc must come from a JSON file in `web\public\data\` produced by code in `analysis\`. Never type a statistic by hand. If a number is needed and no script produces it, write the script.

2. **Outcome lock.** Through Sprint 1, no code could compute or print any outcome metric (`visit`, `conversion`, `spend`) broken down by experiment arm; outcome columns were touched only for schema, null, range, and consistency checks on the pooled data. **As of the outcome-unlock commit (`outcome unlock: sections 6-8 (sprint 2)`, 2026-09-23), the lock is lifted for analysis-plan Sections 6–8 only**: primary, secondary, CUPED, and heterogeneous-effect estimates. By-arm outcome estimates may appear only in the Sprint 2 exports (`effects_primary.json`, `effects_secondary.json`, `cuped.json`, `heterogeneity.json`). Sections 9 and 10 stay locked (see rule 9). The pre-registration is only credible if this holds.

3. **The analysis plan is locked.** `docs\analysis-plan.md` is committed before the data loader exists. Do not edit its body. Any departure from it is recorded in its Deviations section with date, reason, and effect on conclusions.

4. **Provenance on every export.** Every JSON export includes a `manifest` block: git commit SHA, dataset SHA-256, UTC timestamp, script name, and random seed where applicable.

5. **Reproducibility.** Global seed `20260923`. There are two commands, by design:
   - `python -m liftlab.load` fetches the dataset and regenerates `docs\data-source.md`. This is a provenance event and is run rarely.
   - `python -m liftlab.run --stage <stage>` regenerates every published number for that stage. It halts if the dataset's SHA-256 does not match the one recorded in `docs\data-source.md`.

6. **Tests before claims.** A result is not "done" until a test asserts it: integrity checks, SRM, balance, and later the effect estimates against an independent computation (for example, bootstrap vs analytic CI agreement).

7. **Correction log.** When Claude Code produces something wrong that is caught by a test, a check, or human review (a wrong formula, a leaked outcome, a misread column, an off-by-one, an unjustified claim), append an entry to `ai-workflow\correction-log.md` in the same commit as the fix. Be specific and honest. This log is one of the most important artifacts in the repo.

8. **Say what you verified.** At the end of every sprint task, report the exact commands run and their actual output (test counts, row counts, p-values from JSON). Never report success without evidence.

9. **Targeting discipline.** Through Sprint 2, no targeting model or rule and no train/holdout split existed. **As of the Sections 9–10 Deviations commit (2026-09-24), targeting work is permitted only as that entry specifies**, and only in these modules: `liftlab/split.py` (the split and the holdout guard), `liftlab/models.py` (training-split models, P3 and P4 selection, policies), `liftlab/evaluate.py` (the only code that may read holdout rows, run once), and `liftlab/decision.py` (Section 10 application). `liftlab/meta.py` is also allowlisted as a **read-only workflow-record module**: it names the split and evaluation milestones only to find them in git history. It must not import the data-access layer, the targeting modules, pandas or numpy, or open anything under `data\`, and a test enforces this. Its outputs appear only in `split.json`, `training.json`, `targeting.json` and `decision.json`. Every targeting choice is made on the training split. The holdout is evaluated once, in a dedicated commit, and never re-evaluated without a Deviations entry. Sprint 2 heterogeneity estimates remain estimates: they are never ranked or hand-turned into a send rule.

## Style

Python: type hints, small pure functions, `pandas` + `numpy` + `scipy` + `statsmodels`, `duckdb` where SQL is clearer. No notebooks as source of truth; notebooks may exist in `analysis\explore\` but nothing published depends on them.

Web: Next.js 15 App Router, TypeScript strict, Tailwind. Server components read JSON from `public\data` at build time. The readout leads with the decision, then the evidence, then methodology. Plain, confident, business-facing language. Show uncertainty (confidence intervals) everywhere a point estimate appears.
