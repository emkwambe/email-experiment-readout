# LiftLab — Sprint 3: Targeting, Decision, Readout

Read these before doing anything:

- `C:\Dev\liftlab-email-experiment\CLAUDE.md`
- `C:\Dev\liftlab-email-experiment\docs\analysis-plan.md`, including all Deviations
- `C:\Dev\liftlab-email-experiment\ai-workflow\sprint-2-verification.md`

**Sprint goal:** answer the business question with a recommendation:

- whether to send;
- which email;
- to whom;
- at what cost it stops paying.

The recommendation must be backed by a targeting analysis whose holdout is used exactly once. The site becomes a decision-first readout, and the project closes with a complete case study of the Claude Code workflow.

Stop and report at any failed check, surprising result, or plan ambiguity.

## Step 0 — Preflight and Sprint 2 follow-ups

1. **Environment preflight:** run `py -0p`, `node -v`, `vercel --version`, and `gh auth status`, and report the output.
2. **Screenshots.**
   - Gitignore full-resolution screenshot output.
   - Change the Playwright script to also write a compressed WebP set: 50% scale, quality around 70. Only the WebP set is committed, at sprint end.
   - Add a check that fails if any committed evidence image exceeds 300 KB.
   - Do not touch history.
3. **H3 note.** On `/results`, add one neutral sentence near H3: the dollar difference and the relative lift are different estimands, and the relative-lift interval is wider because it also carries uncertainty in the comparison group's mean.
4. **CUPED note.** On `/results`, state plainly that CUPED produced negligible variance reduction because prior-year spend is only weakly correlated with two-week spend. Read the correlation from JSON; export it if it isn't exported yet.

Commit with the message: `sprint 3 step 0: preflight, evidence image policy, H3 and CUPED notes`. Include `sprint-3.md` in this commit.

## Step 1 — Deviations entry for Sections 9–10 (before any split exists)

Write a dated Deviations entry in `docs\analysis-plan.md` that fixes the following. Commit it before Step 2, and report the SHA.

### 1a. Policies compared

Seven policies, each mapping a customer to exactly one action in {Mens, Womens, None}:

- **P0** Send nothing.
- **P1** Send everyone the Mens E-Mail.
- **P2** Send everyone the Womens E-Mail.
- **P3** CV-selected segment rule.
  - For each of the four pre-specified Section 8 dimensions (dimension 1 with its three observed levels), build a candidate rule. For each level, it assigns the action with the highest training-estimated net revenue per customer, where None has net value 0.
  - Select among the four candidates by 5-fold cross-validated net revenue on the training split only, seed 20260923.
  - No human choice is involved. This replaces "a simple rule derived from Section 8", because no heterogeneity test survived correction and segment estimates were already public, so a hand-picked rule would be post hoc.
- **P4a / P4b** Uplift top-k% per arm, as the plan specifies. Send the Mens (or Womens) email to the top k% by predicted incremental revenue, for k in {10, 20, …, 100}, and None to the rest.
- **P5** Uplift assignment. Each customer gets the action with the highest predicted net incremental revenue (predicted uplift minus cost), or None if both predicted net values are ≤ 0.

### 1b. Uplift model

- Two-model estimator: separate `HistGradientBoostingRegressor` models for spend in Mens, Womens, and No E-Mail on the training split.
- Features are pre-period only: `recency`, `history`, `mens`, `womens`, `zip_code`, `newbie`, `channel`. Exclude `history_segment` as redundant with `history`.
- Tune hyperparameters by 5-fold CV mean squared error within each arm's training data, over a small pre-declared grid:
  - `max_depth` {3, 5}
  - `learning_rate` {0.05, 0.1}
  - `max_iter` {100, 300}
  - `min_samples_leaf` {50, 200}
- Predicted uplift for arm A is pred_A − pred_None.

### 1c. Policy value estimator (holdout)

Randomization probabilities are known (1/3 each), so the policy value is estimated with inverse-probability weighting:

- V(π) = mean over holdout customers of [spend × 1{T = π(x)} × 3].
- Net value: NV(π) = V(π) − cost × (share of holdout customers for whom π(x) ≠ None).
- Report each policy's net value per customer relative to P0.
- Also report the incremental revenue per customer of each policy relative to P0.

Uncertainty comes from 2,000 bootstrap resamples of the holdout (seed 20260923), computing all policies on each resample so the comparisons are paired.

### 1d. Winner rule

- The recommended policy is the one with the highest holdout net value at the default cost of $0.10.
- A targeted policy (P3, P4, or P5) replaces the best blanket policy (P1 or P2) **only if** the paired bootstrap 95% CI of their difference in net value lies entirely above zero.
- Otherwise the best blanket policy is recommended, and the readout states that targeting did not demonstrably beat blanket sending on this data.

### 1e. Decision rule (Section 10) application

Using the full-sample Section 6 estimates:

- For each email, report its status at cost $0.10:
  - "send" if the 95% CI lower bound > cost;
  - "promising — test again" if the point estimate > cost ≥ lower bound;
  - "do not send" otherwise.
- Sensitivity: evaluate costs from $0.01 to $0.50 in $0.01 steps. For each email, report the break-even cost at the point estimate and at the lower bound.

### 1f. Supplementary margin view (labeled supplementary, not pre-registered)

Minimum gross margin at which sending is justified = cost ÷ incremental revenue per customer. Report it at both the point estimate and the lower bound, for default cost only. This is labeled as a presentation aid derived from pre-registered quantities, since the data contains no margin.

### 1g. Holdout discipline

- Split 70/30, stratified by arm, seed 20260923.
- The split is created by one function, and its holdout customer-index hash is committed before any model is trained.
- Holdout evaluation runs once, in a dedicated commit. It is never rerun unless a Deviations entry justifies it.

## Step 2 — Split and seal

Implement `liftlab/split.py`. Write `web\public\data\split.json` with:

- train and holdout sizes per arm;
- the SHA-256 of the sorted holdout customer indices;
- a manifest block.

Add a test that recomputes the split and asserts the hash matches.

**Add a holdout guard.** A test fails if any training, tuning, or rule-selection code path reads holdout rows. Implement it by having the data access layer raise an error when a holdout index is requested outside `liftlab/evaluate.py`.

Commit with the message: `split and seal holdout (before any model training)`. Report the SHA and hash.

## Step 3 — Training-split work

On the training split only:

1. Tune and fit the uplift models.
2. Build the P3 candidates and select one by CV.
3. Export the P3 selection result and the CV results.
4. Export the model CV metrics and chosen hyperparameters.

Report training-split diagnostics:

- The CV Qini coefficient for each arm, using out-of-fold predictions.
- The share of customers assigned to each action under P5 at $0.10.

If the out-of-fold Qini is near zero, report it. That is an expected and legitimate outcome given the weak features.

Commit with the message: `training-split models and rule selection (holdout untouched)`.

## Step 4 — Single holdout evaluation

Implement `liftlab/evaluate.py`. It runs once:

- The Qini curves on the holdout for P4a and P4b.
- The net value for every policy at $0.10.
- Paired bootstrap CIs for every targeted-minus-best-blanket difference.
- The net-value curve for P4a and P4b across k.
- The winner per rule 1d.
- Net value across the full cost grid for P1, P2, and P5.

Export `targeting.json`. Commit with the message: `holdout evaluation (single use)`. Report the SHA.

## Step 5 — Decision exports

Implement the Section 10 application (1e) and the supplementary margin view (1f). Export `decision.json`, containing:

- per-email status at $0.10;
- break-even costs;
- the sensitivity table;
- the minimum margins;
- the winning policy with its holdout net value and interval;
- a machine-readable recommendation object.

The recommendation object's text fields are generated from template strings filled with JSON values. None are hand-typed.

## Step 6 — Independent verification (as tests)

- Check the IPW policy value on a synthetic dataset with a known true policy value. The estimate's CI should cover it.
- Recompute P1's and P2's holdout values independently in DuckDB SQL, and assert they match `evaluate.py`.
- Check that P1's holdout incremental revenue per customer is consistent with the Section 6 full-sample H1 estimate. Holdout and full-sample CIs should overlap. Report the overlap check; it is not a hard equality.
- Verify the break-even cost calculations against hand-computed values from the JSON inputs.
- Confirm the holdout guard raises when training code requests holdout rows.

## Step 7 — Readout website

**Restructure `/` as the decision-first readout:**

1. **Recommendation** — one plain sentence generated from `decision.json`, with the winning policy, its incremental revenue per customer and interval, and the cost assumption.
2. **Why** — primary effects in brief, linking to `/results`.
3. **Does targeting help?** — a short answer from `targeting.json`, linking to `/targeting`.
4. **When it stops paying** — a sensitivity chart of net value vs cost per email, with break-even points marked, plus the supplementary margin view, clearly labeled.
5. **What we saw in the funnel** — visit lift vs conversion lift from `effects_secondary.json`, framed neutrally as a question for the landing-experience owner.
6. **Limitations** — two-week window, 2008 data, no guardrails, no margin data, weak pre-period features.
7. **How we know** — links to `/plan` (with the pre-registration SHA), `/checks`, `/results`, `/targeting`, `/how-its-built`.

**Add `/targeting`:**

- Qini curves per arm on the holdout.
- The net-value-vs-k curves.
- A policy comparison table with paired CIs against the best blanket policy.
- The P3 selection result.
- A sentence stating that the holdout was evaluated once, with the commit SHA.

**Expand `/how-its-built` into the case study:**

- A timeline built from git: pre-registration → first data access → outcome unlock → Deviations entries → holdout seal → holdout evaluation, each with SHA and date. Generate it with a script that reads git log at build time and writes `timeline.json`.
- Correction-log statistics parsed from `ai-workflow\correction-log.md` by code: entry count, count by origin (Claude Chat vs Claude Code), and count by how each error was caught.
- The division of labor: planning decisions in chat, execution in Claude Code, verification by tests and human review.
- Links to every sprint prompt and verification file.

Update the status badge to "Complete".

All numbers come from JSON. Charts are inline SVG. Apply the `Surburban` → `Suburban` display mapping and footnote wherever zip_code appears.

## Step 8 — Smoke, deploy, finalize

Extend smoke to check:

- `/targeting` returns 200;
- `decision.json` has a recommendation object and numeric break-even costs;
- `targeting.json` has the winner and holdout evaluation commit SHA;
- `timeline.json` includes the pre-registration SHA `48c63f4`;
- every manifest's dataset hash matches.

Then:

1. Run the 390px screenshots for all pages in both themes, and commit the WebP set.
2. Deploy with `vercel deploy --prod --cwd C:\Dev\liftlab-email-experiment\web`.
3. Run `npm --prefix C:\Dev\liftlab-email-experiment\web run smoke` against production.
4. Write `ai-workflow\sprint-3-verification.md`.
5. Update the correction log.

**Finalize the README:**

- the recommendation in one sentence, generated from JSON at build time or copied by a script, never hand-typed;
- the live URL;
- the pre-registration SHA;
- methods in one short paragraph;
- the "How this was built with Claude Code" section with correction-log statistics;
- reproduction commands;
- limitations.

Tag the release `v1.0` and push with tags.

## Definition of Done

- [ ] Step 0 committed; evidence image policy enforced
- [ ] Sections 9–10 Deviations entry committed before the split; SHA reported
- [ ] Split sealed with its holdout hash before training; holdout guard test passes
- [ ] Training-split models tuned; P3 selected by CV; out-of-fold Qini reported
- [ ] Holdout evaluated exactly once in a dedicated commit; SHA reported
- [ ] Winner determined by rule 1d; decision and sensitivity exported
- [ ] All verification tests pass (report the pytest summary line)
- [ ] `/` is decision-first; `/targeting` live; `/how-its-built` has the generated timeline and correction statistics
- [ ] Smoke passes against production (report the output); 390px screenshots pass in both themes
- [ ] README finalized; `v1.0` tagged and pushed
- [ ] Correction log and sprint-3 verification file complete

## Final report format

End the sprint with a short report containing:

- the commits made, with SHAs, including the Deviations, seal, and holdout-evaluation commits;
- test and smoke output verbatim;
- the recommendation sentence as generated;
- each policy's holdout net value with its CI;
- the winner and whether targeting beat blanket sending;
- per-email status at $0.10 and break-even costs;
- the out-of-fold and holdout Qini summaries;
- correction-log entries added;
- anything surprising.
