# Email Experiment Readout

**Did a retailer's emails generate incremental revenue, which email, and who should get each one next time? A pre-registered analysis of a real randomized email experiment, built in the open with Claude Code.**

- **Live readout:** https://email-experiment-readout.vercel.app
- **Pre-registration commit:** [`48c63f40ef275432fc9464b0d2ce107657270982`](https://github.com/emkwambe/email-experiment-readout/commit/48c63f40ef275432fc9464b0d2ce107657270982). The analysis plan, project rules and Sprint 1 brief were committed before any data loader existed. A test checks that this commit precedes every commit touching the loader.
- **Name:** Formerly named LiftLab; renamed to avoid confusion with LiftLab Analytics, Inc. The Python package keeps the internal name `liftlab`, and the local folder is still `liftlab-email-experiment`.
- **Dataset:** Kevin Hillstrom's MineThatData E-Mail Analytics and Data Mining Challenge (2008). Provenance, hashes and the check against the original file are in [`docs/data-source.md`](docs/data-source.md).

## Recommendation

<!-- generated:recommendation -->
> **Send the Mens E-Mail to every customer: in the full experiment it added $0.77 of revenue per customer (95% CI $0.49 to $1.05), against an assumed send cost of $0.10 per email; on the untouched holdout, no targeting policy beat sending to everyone.**
>
> Supplementary, not pre-registered: at $0.10 per email, sending pays if gross margin is at least 13.0% (at the point estimate) or 20.6% (at the lower bound of the 95% CI).
<!-- /generated -->

*Generated from [`web/public/data/decision.json`](web/public/data/decision.json) by `python -m liftlab.readme`; a test fails if this text drifts from the JSON.*

## Status: complete (Sprint 3 of 3)

| Sprint | Scope | Key commits (see the [timeline](https://email-experiment-readout.vercel.app/how-its-built)) |
|---|---|---|
| 1 | Pre-registration, data-quality gates, first deploy | pre-registration `48c63f4` |
| 2 | Primary and secondary effects, CUPED, heterogeneous effects | outcome unlock `cf44832`, method Deviations `7a3e092` |
| 3 | Targeting on a sealed holdout, decision rule, decision-first readout | targeting Deviations `363e98b`, holdout seal `3731c5a`, single holdout evaluation `c989424` |

## Methods

Customers were randomized to a Mens email, a Womens email or no email. After data-quality gates (integrity, sample ratio, covariate balance), the primary analysis compares revenue per customer (spend including zeros) between each email and no email: Welch tests with Holm correction, and bootstrap intervals that must agree with the analytic ones. Secondary analyses cover visit and conversion rates (Newcombe intervals), a CUPED adjustment and pre-specified segment effects (HC3 interaction tests with Holm correction). For targeting, customers were split into training and holdout sets. The holdout's customer list was hashed and committed before any model was trained, and all tuning and rule selection (gradient-boosted two-model uplift, cross-validated segment and top-k rules) used the training split only. Seven pre-selected policies were then scored once on the holdout with an inverse-probability policy-value estimator and paired bootstrap intervals. The recommendation applies the pre-registered decision rule: send only if the lower bound of the interval for incremental revenue per customer exceeds the assumed cost per email.

## How this was built with Claude Code

The project doubles as a record of AI-assisted analysis that can be checked. The full case study, including a timeline generated from git, is at [/how-its-built](https://email-experiment-readout.vercel.app/how-its-built).

- **Plan in chat, execute in Claude Code, verify by tests.** Each sprint is specified in a brief ([`sprint-1.md`](ai-workflow/sprint-1.md), [`sprint-2.md`](ai-workflow/sprint-2.md), [`sprint-3.md`](ai-workflow/sprint-3.md)), which Claude Code carries out under the binding rules in [`CLAUDE.md`](CLAUDE.md):
  - no hand-typed numbers;
  - outcomes unlocked section by section;
  - targeting only on the training split, with the holdout readable by one module only and evaluated once;
  - a manifest on every export.
- **Decisions stay with the human owner.** When the plan was ambiguous or a check failed, Claude Code stopped and asked. Each answer was committed as a dated Deviations entry in [`docs/analysis-plan.md`](docs/analysis-plan.md) before the data that could influence it was visible.
- **Every caught error is logged, with its fix, in the same commit.**
<!-- generated:corrections -->
- **17 errors** caught and recorded in the [correction log](ai-workflow/correction-log.md): 12 from Claude Code, 5 from Claude Chat.
- How they were caught:
  - Human review: 5
  - Claude Code self-review: 4
  - Claude Code pre-check or plan review (before results): 3
  - Screenshot review: 3
  - Automated test or guard: 2
<!-- /generated -->
- **Verification evidence:** [Sprint 1](ai-workflow/sprint-1-verification.md), [Sprint 2](ai-workflow/sprint-2-verification.md), [Sprint 3](ai-workflow/sprint-3-verification.md), with 390 px screenshots in [`ai-workflow/evidence/`](ai-workflow/evidence/).

## Reproduce

Windows PowerShell, absolute paths, Python 3.12, Node 22.

```powershell
# Python environment
py -3.12 -m venv C:\dev\liftlab-email-experiment\analysis\.venv
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -r C:\dev\liftlab-email-experiment\analysis\requirements.txt
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pip install -e C:\dev\liftlab-email-experiment\analysis

# Regenerate every published number (cumulative: all three sprints) and write JSON to web\public\data.
# Downloads the dataset if absent; halts if its SHA-256 does not match docs\data-source.md.
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.run --stage sprint3

# The holdout evaluation was run once and is committed; this recomputes it and checks it matches, writing nothing.
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.evaluate --verify

# Refresh the generated README blocks, then run the tests
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.readme
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pytest C:\dev\liftlab-email-experiment\analysis\tests -q

# Optional: re-download the data, re-check it against the original MineThatData CSV, and regenerate docs\data-source.md
C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.load

# Website
npm --prefix C:\dev\liftlab-email-experiment\web install
npm --prefix C:\dev\liftlab-email-experiment\web run build
npm --prefix C:\dev\liftlab-email-experiment\web run smoke
npm --prefix C:\dev\liftlab-email-experiment\web run screenshots   # 390 px device-emulated screenshots (WebP set is committed)
```

## Limitations

- Outcomes cover only the two weeks after the send.
- One historical send, in 2008.
- No guardrail data: no unsubscribe, complaint or long-term retention data.
- No margin data: revenue is not profit, and the cost per email is an assumption. The margin view on the readout is supplementary and was not pre-registered.
- Weak pre-period features limit both variance reduction and targeting (see [/results](https://email-experiment-readout.vercel.app/results) and [/targeting](https://email-experiment-readout.vercel.app/targeting)).

## Security note

`npm audit` reports a PostCSS advisory through Next 15's bundled build tooling. It affects only build-time processing of this project's own CSS: no user-supplied CSS is processed, and nothing from it runs in the deployed site. The only fix is Next 16, and this project is pinned to Next 15, so the advisory is left in place.

## Layout

```
docs/            locked analysis plan (with Deviations), data provenance
ai-workflow/     sprint briefs, correction log, verification evidence, screenshots
analysis/        liftlab Python package (load, checks, power, effects, heterogeneity, split, models,
                 evaluate, decision, meta, readme, run) and tests
web/             Next.js 15 readout; web/public/data holds the exported JSON
```

---

An analytics case study built with Claude Code by Eddy Mkwambe.
