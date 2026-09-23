# LiftLab

**Did a retailer's emails generate incremental revenue, which email, and who should get each one next time? A pre-registered analysis of a real randomized email experiment, built in the open with Claude Code.**

- **Live readout:** https://liftlab-email-experiment.vercel.app
- **Pre-registration commit:** [`48c63f40ef275432fc9464b0d2ce107657270982`](https://github.com/emkwambe/liftlab-email-experiment/commit/48c63f40ef275432fc9464b0d2ce107657270982). The analysis plan, project rules and Sprint 1 brief were committed before any data loader existed. The full SHA is also exported in [`web/public/data/manifest.json`](web/public/data/manifest.json), and a test checks that this commit precedes every commit touching the loader.
- **Dataset:** Kevin Hillstrom's MineThatData E-Mail Analytics and Data Mining Challenge (2008). Provenance, hashes and the check against the original file are in [`docs/data-source.md`](docs/data-source.md).

## Status: Sprint 1 of 3

| Sprint | Scope | State |
|---|---|---|
| 1 | Pre-registration, data-quality gates, first deploy | Done: gates published, **outcomes still locked** |
| 2 | Primary and secondary effects, CUPED, heterogeneous effects | Not started |
| 3 | Uplift targeting model, decision rule, final readout | Not started |

No outcome (visits, conversions, spend) has been compared across email groups yet. The gate results are on [/checks](https://liftlab-email-experiment.vercel.app/checks), and every number there is read from the JSON in [`web/public/data/`](web/public/data/).

## How this was built with Claude Code

The project doubles as a record of AI-assisted analysis that can be checked:

- **Plan in chat, execute in Claude Code, verify by tests.** Each sprint is specified in a sprint file ([`ai-workflow/sprint-1.md`](ai-workflow/sprint-1.md)), which Claude Code carries out under the binding rules in [`CLAUDE.md`](CLAUDE.md): no hand-typed numbers, an outcome lock until Sprint 2, a manifest on every export, and one command per stage.
- **[Correction log](ai-workflow/correction-log.md).** Every error that Claude (in chat or in Claude Code) made and that a test, a check or a review caught is recorded, committed together with its fix.
- **[Verification evidence](ai-workflow/sprint-1-verification.md).** The exact commands run at the end of the sprint and their output.
- **The locked plan** is [`docs/analysis-plan.md`](docs/analysis-plan.md). Its body is never edited; departures go in its Deviations section.

## Reproduce

Windows PowerShell, absolute paths, Python 3.12, Node 22.

```powershell
# Python environment
py -3.12 -m venv C:\dev\liftlab-email-experiment\analysis\.venv
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -r C:\dev\liftlab-email-experiment\analysis\requirements.txt
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -e C:\dev\liftlab-email-experiment\analysis

# Regenerate every Sprint 1 number (downloads the dataset if absent, halts if its SHA-256
# does not match docs\data-source.md) and write JSON to web\public\data
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.run --stage sprint1

# Tests
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pytest C:\dev\liftlab-email-experiment\analysis\tests -q

# Optional: re-download the data, re-check it against the original MineThatData CSV, and regenerate docs\data-source.md
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.load

# Website
npm --prefix C:\dev\liftlab-email-experiment\web install
npm --prefix C:\dev\liftlab-email-experiment\web run build
npm --prefix C:\dev\liftlab-email-experiment\web run smoke
```

## Layout

```
docs/            locked analysis plan, data provenance
ai-workflow/     sprint briefs, correction log, verification evidence
analysis/        liftlab Python package (load, checks, power, run) and tests
web/             Next.js 15 readout; web/public/data holds the exported JSON
```
