# LiftLab — Sprint 2: Outcome Unlock and Effect Estimation

Read `C:\Dev\liftlab-email-experiment\CLAUDE.md`, `C:\Dev\liftlab-email-experiment\docs\analysis-plan.md` (including Deviations), and `C:\Dev\liftlab-email-experiment\ai-workflow\sprint-1-verification.md` before doing anything.

**Sprint goal:** estimate every effect specified in analysis-plan Sections 6, 7, and 8, verify each estimate independently, and publish the results on a `/results` page. **No targeting model, targeting rule, or recommendation is built this sprint.** That work belongs to Sprint 3 (plan Sections 9 and 10).

Stop and report at any failed step, surprising result, or ambiguity in the plan. Do not resolve ambiguity silently.

## Step 0 — Preflight and Sprint 1 follow-ups

1. **Environment preflight** (the guard from correction-log entry 1): run `py -0p`, `node -v`, `vercel --version`, and `gh auth status`, and report the output.
2. **Rule 5 wording.** Update CLAUDE.md rule 5 to describe the two-command design explicitly:
   - `python -m liftlab.load` fetches the data and regenerates `docs\data-source.md`. It is a provenance event, run rarely.
   - `python -m liftlab.run --stage <stage>` regenerates every published number, and halts if the dataset hash does not match `docs\data-source.md`.
3. **SMD formula.** Confirm the balance SMD uses the standard definition:
   - continuous covariates: (mean_t − mean_c) / sqrt((var_t + var_c) / 2);
   - binary covariates: the p(1−p) form of the same formula.

   If the implementation differs, fix it, add a test against a hand-computed example, regenerate the Sprint 1 exports, and log the correction. Also document in `/checks` methodology notes that `history` and `history_segment` overlap by construction, and that the MDE uses a normal approximation.
4. **README note.** Add a short security note: the PostCSS advisory in Next 15 affects build-time processing of the project's own CSS only, and is left in place because the stack is pinned to Next 15.
5. **True phone-width check.** Add Playwright as a dev dependency in `web\`. Add a script that screenshots every page at a 390×844 viewport using device emulation. Review the screenshots and fix any layout defects. Commit the screenshots under `ai-workflow\evidence\sprint-2\`.

Commit Step 0 separately with the message: `sprint 2 step 0: preflight, rule 5 wording, SMD verification, mobile check`.

## Step 1 — Outcome unlock commit

Update CLAUDE.md rule 2 to read that the outcome lock is lifted for plan Sections 6–8 as of this commit, with the date.

Add a new rule: **no targeting model or targeting rule may be built, and no train/holdout split may be created, until Sprint 3.** Sprint 3 will create the split and derive every targeting rule on the training split only.

Update the outcome-lock test so it permits by-arm outcome estimates only in the new Sprint 2 export files, and still fails if any targeting or policy output exists.

Commit with the message: `outcome unlock: sections 6-8 (sprint 2)`. Report the SHA. This commit marks the moment results became visible.

## Step 2 — Primary analysis (plan Section 6)

Implement `liftlab/effects.py`. For H1 (Mens vs No E-Mail) and H2 (Womens vs No E-Mail), on revenue per customer (mean `spend` including zeros), compute:

- difference in means;
- Welch's t statistic, degrees of freedom, and raw p-value;
- the analytic 95% CI (Welch);
- a 95% percentile bootstrap CI: 10,000 resamples within arm, seed 20260923;
- Holm-adjusted p-values across H1 and H2 at family-wise α = 0.05;
- relative lift with a delta-method 95% CI, reported as secondary to the dollar difference.

Compute H3 (Mens vs Womens) the same way, outside the Holm family.

**Agreement check (required by the plan):** compare the bootstrap and analytic CIs on sign and width. Record the width ratio in the export. If they differ in sign, or the width ratio falls outside 0.8–1.25, stop and report. Do not choose one silently.

## Step 3 — Secondary metrics (plan Section 6)

For visit rate and conversion rate, for H1 and H2, compute:

- difference in proportions;
- the two-proportion z-test p-value;
- the Newcombe hybrid score interval, which is the Wilson-based interval for a difference of proportions (Newcombe 1998, method 10);
- Holm correction within each metric across H1 and H2.

Report spend among converters per arm as **descriptive only**, with no test and no interval. Label it in the export as `descriptive_only: true`, with the selection-bias reason as a string.

## Step 4 — CUPED (plan Section 7)

1. Estimate θ = cov(spend, history) / var(history) on the pooled data.
2. Compute the adjusted outcome.
3. Re-estimate H1 and H2 with Welch analytic CIs on the adjusted outcome.

Report θ, the variance reduction percentage for each arm, and the adjusted estimates alongside the unadjusted ones. Mark the unadjusted estimate as primary in the export. If adjusted and unadjusted estimates disagree in sign, flag it as a finding and stop to report.

## Step 5 — Heterogeneous effects (plan Section 8)

For each email arm vs No E-Mail, and each of the four pre-specified dimensions:

1. `mens` × `womens`, crossed into four groups
2. `newbie`
3. `channel`
4. `zip_code`

Fit an OLS model of spend on the treatment indicator, segment dummies, and their interaction, with HC3 standard errors. Test heterogeneity with a **joint Wald test of all interaction terms** for that dimension. That gives 8 tests (4 dimensions × 2 arms). Apply Holm correction across all 8.

Report the segment-level treatment effect and its 95% CI for every segment, whether or not the interaction test is significant. Include segment sample sizes. **Do not rank segments or produce any recommendation.**

## Step 6 — Independent verification

Build these as tests, not one-off checks:

- Recompute arm means, the H1 and H2 differences, and visit and conversion rates **independently in DuckDB SQL** from the raw CSV. Assert they match the pandas results to 1e-9.
- Cross-check Welch results against `scipy.stats.ttest_ind(equal_var=False)` and the statsmodels equivalent.
- Verify the Newcombe interval against a published worked example with known bounds.
- Verify Holm adjustment against a hand-computed example.
- Verify the CUPED θ against an OLS regression of spend on history.
- Test the bootstrap on a small synthetic dataset with a known true difference: the CI should cover it.

## Step 7 — Exports

Extend `liftlab.run` with `--stage sprint2`, writing to `web\public\data\`:

- `effects_primary.json`
- `effects_secondary.json`
- `cuped.json`
- `heterogeneity.json`

Each file gets a manifest block. Regenerate from a clean tree before the export commit, as in Sprint 1.

## Step 8 — Web

Add a `/results` page:

- A dot-and-whisker chart of H1, H2, and H3 revenue-per-customer differences with both CIs, Holm-adjusted p-values beside the primary contrasts, and relative lift secondary.
- Secondary metrics in a compact table.
- The CUPED comparison: unadjusted vs adjusted, with the variance reduction.
- A segment forest plot per arm per dimension, with the joint interaction test result and Holm-adjusted p shown per dimension.
- A clearly visible note: "Estimates only. The cost-based decision rule and targeting analysis are applied in Sprint 3."

Draw charts as inline SVG, built from the JSON. Every number is read from JSON. Apply the `Surburban` → `Suburban` display mapping and footnote here as well.

Update the home page status badge to "Effects estimated · targeting pending", and add `/results` to the navigation.

**Tone:** report results neutrally. Null or negative results get the same prominence as positive ones. No interpretive claims beyond what the JSON supports.

## Step 9 — Smoke, deploy, evidence

Extend `smoke.mjs` to check:

- `/results` returns 200;
- `effects_primary.json` has numeric Holm-adjusted p-values for H1 and H2;
- every sprint 2 manifest's dataset SHA-256 matches `docs\data-source.md`.

Rerun the 390px Playwright screenshots, including `/results`.

Then:

1. Deploy with `vercel deploy --prod --cwd C:\Dev\liftlab-email-experiment\web`.
2. Run `npm --prefix C:\Dev\liftlab-email-experiment\web run smoke` against production.
3. Write `ai-workflow\sprint-2-verification.md` with the full evidence.
4. Update the correction log with every error caught this sprint. If none were caught, add an explicit "none caught" entry that lists the checks that were run.
5. Update the README status to "Sprint 2 of 3".
6. Push.

## Definition of Done

- [ ] Step 0 committed: preflight output reported, rule 5 reworded, SMD formula verified (or corrected and logged), README security note, 390px screenshots reviewed
- [ ] Outcome-unlock commit exists; SHA reported
- [ ] H1, H2, H3 estimates exported with analytic and bootstrap CIs; agreement check passed (width ratios reported)
- [ ] Secondary metrics with Newcombe intervals and within-metric Holm correction
- [ ] CUPED θ, variance reduction, and adjusted estimates exported; sign agreement reported
- [ ] 8 heterogeneity tests with Holm correction; all segment estimates with CIs and sample sizes
- [ ] DuckDB independent recomputation matches pandas to 1e-9
- [ ] No targeting model, rule, or split exists anywhere in the repo
- [ ] All tests pass (report the pytest summary line); smoke passes against production (report the output)
- [ ] `/results` live, 390px-verified, numbers traceable to JSON
- [ ] Correction log and sprint-2 verification file complete; README updated; pushed

## Final report format

End the sprint with a short report containing:

- the commits made, with SHAs;
- test and smoke output verbatim;
- the H1, H2, and H3 estimates with both CIs and Holm-adjusted p-values, as read from JSON;
- the secondary-metric results;
- CUPED θ and variance reduction;
- which, if any, of the 8 heterogeneity tests survive Holm correction;
- correction-log entries added;
- anything surprising, or that needs a human decision before Sprint 3.
