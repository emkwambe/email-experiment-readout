# Email-experiment-readout — Pre-Registered Analysis Plan

**Author:** Eddy Mkwambe
**Status:** Locked. This document was committed before any data loader existed in the repository; the git history is the timestamp. The body below is not edited after commit. Changes are recorded only in the Deviations section at the end.

## 1. Business question

A retailer emailed a randomly selected subset of its recent customers. The decision to support is: **should the team send these emails again, which version, and to which customers, given that each send has a cost?**

## 2. Experiment design (as described by the data publisher)

Population: 64,000 customers who purchased within the prior twelve months. Each was randomly assigned to one of three arms of roughly equal size:

- **Mens E-Mail** — an email featuring men's merchandise
- **Womens E-Mail** — an email featuring women's merchandise
- **No E-Mail** — control

Outcomes were observed over the two weeks following the send: whether the customer visited the site (`visit`), purchased (`conversion`), and dollars spent (`spend`).

Pre-period covariates: `recency` (months since last purchase), `history_segment` and `history` (dollar value of purchases in the prior year), `mens` and `womens` (prior purchase of that merchandise), `zip_code` (Urban, Suburban, Rural), `newbie` (new customer in prior twelve months), `channel` (Phone, Web, Multichannel).

## 3. Hypotheses

**H1 (primary).** The Mens E-Mail increases revenue per customer relative to No E-Mail.
**H2 (primary).** The Womens E-Mail increases revenue per customer relative to No E-Mail.
**H3 (secondary).** Revenue per customer differs between Mens E-Mail and Womens E-Mail.

All tests are two-sided. We state directional expectations (H1, H2) but test two-sided so that a harmful email would be detected.

## 4. Metrics

**Primary metric: revenue per customer** — mean `spend` over all customers in the arm, including zeros. This is the metric that maps to the business decision, because cost is incurred per customer emailed, not per buyer.

**Secondary metrics:** visit rate and conversion rate.

**Descriptive only:** spend among converters. This is conditioned on a post-treatment outcome and is subject to selection bias, so it is reported for context and never used for inference or the recommendation.

**Guardrails (limitation).** The dataset contains no unsubscribe, complaint, or long-term retention data. We state this openly. In a production program, unsubscribe rate and 90-day revenue would be pre-registered guardrails, and the recommendation would be conditional on them.

## 5. Data quality gates (run before any outcome analysis)

The analysis halts, and the halt is reported, if any gate fails.

1. **Integrity:** exactly 64,000 rows; no nulls in any column; `spend >= 0`; `spend > 0` implies `conversion = 1`; `conversion = 1` implies `visit = 1`; categorical columns contain only documented levels.
2. **Sample ratio mismatch (SRM):** chi-square goodness-of-fit test of arm counts against an equal 1/3 split. **Halt threshold: p < 0.001.**
3. **Covariate balance:** standardized mean difference (SMD) for every pre-period covariate (one-hot for categoricals), each treatment arm vs control. **Flag threshold: |SMD| > 0.1.** Flags are reported; they do not halt the analysis but are addressed with the covariate-adjusted estimate in Section 7.

## 6. Primary analysis

For each of H1 and H2:

- **Estimate:** difference in mean revenue per customer (treatment minus control).
- **Test:** Welch's t-test.
- **Interval:** 95% percentile bootstrap confidence interval, 10,000 resamples, seed 20260923, resampling within arm. Spend is zero-inflated and right-skewed, so the bootstrap interval is reported alongside the analytic interval, and the two are required to agree in sign and approximately in width. A material disagreement is reported rather than resolved silently.
- **Multiplicity:** Holm correction across the two primary contrasts (H1, H2) at family-wise α = 0.05.
- **Relative lift:** reported with a delta-method interval, secondary to the absolute dollar difference.

H3 is tested the same way and reported without inclusion in the primary family.

Secondary metrics (visit rate, conversion rate): difference in proportions with a two-proportion z-test and Wilson-based intervals, Holm-corrected within each metric across H1 and H2.

## 7. Variance reduction (CUPED)

As a pre-specified secondary estimate, revenue per customer is adjusted with CUPED using prior-year `history` as the covariate, with θ estimated on pooled data. We report the adjusted estimate, its interval, and the variance reduction achieved. **The unadjusted estimate in Section 6 remains the primary result.** If the adjusted and unadjusted estimates disagree in sign, that is reported as a finding.

## 8. Heterogeneous effects (pre-specified, confirmatory within a limited family)

Treatment effects on revenue per customer are estimated within these four pre-specified dimensions only:

1. Prior merchandise purchase (`mens`, `womens` flags, crossed into four groups)
2. `newbie`
3. `channel`
4. `zip_code`

For each email arm, effect heterogeneity is tested with a treatment-by-segment interaction in an OLS model with heteroskedasticity-robust (HC3) standard errors. Holm correction is applied across the eight interaction tests (four dimensions × two email arms). Segment-level estimates are reported with intervals whether or not the interaction is significant.

Any segmentation beyond these four dimensions is **exploratory**, is labeled as such everywhere it appears, and cannot drive the recommendation on its own.

## 9. Targeting model (pre-specified exploratory)

To test whether targeting beats sending to everyone:

- Split customers 70/30 into train and holdout, stratified by arm, seed 20260923.
- Fit a two-model uplift estimator for each email arm (separate gradient-boosted regressors for treated and control revenue using pre-period covariates only), predicting incremental revenue per customer.
- On the holdout only, evaluate with a Qini curve and compute realized incremental revenue for the policy "send to the top k% by predicted uplift" for k in {10, 20, …, 100}.
- Compare against sending to everyone and against a simple rule derived from Section 8.

The holdout is used once. Model iteration happens only on the training split with cross-validation.

## 10. Decision rule

The cost per email sent is an **assumed parameter**, not a property of the data: default $0.10, with sensitivity analysis from $0.01 to $0.50.

- Recommend sending an email to a group if the **lower bound** of the 95% interval for incremental revenue per customer exceeds the cost per email.
- If the point estimate exceeds cost but the lower bound does not, the recommendation is "promising, test again at larger scale," not "send."
- The recommended targeting policy is the one with the highest realized holdout net incremental revenue (incremental revenue minus send cost), provided it beats send-to-all by more than holdout sampling noise (bootstrap on the holdout).

Revenue is not margin. The readout states that net profit depends on gross margin, which the data does not contain.

## 11. Reporting commitments

- Every estimate is shown with an interval.
- Null and negative results are reported with the same prominence as positive ones.
- All numbers on the site trace to a JSON export with a manifest (commit SHA, dataset hash, seed).
- The readout states limitations: two-week window, one historical send (2008), no guardrail data, no margin data.

## Deviations

*None at time of commit. Future entries: date, what changed, why, and effect on conclusions.*

**2026-09-23 · Documented levels for `zip_code` (Section 5, gate 1)**
- **What changed:** For the integrity gate's documented-levels check, the documented levels of `zip_code` are `{Urban, Surburban, Rural}`. "Surburban" is how the source file spells the level that Hillstrom's post describes as "Suburban" ("Classifies zip code as Urban, Suburban, or Rural").
- **Why:** The data file uses the spelling "Surburban". Read literally against the post's wording, gate 1 would fail on a spelling difference, not on a data problem. The local file is byte-identical to the scikit-uplift mirror, and its parsed contents are identical to the original MineThatData CSV (see `docs\data-source.md`). The raw data and the loader are unchanged; "Surburban" is kept exactly as in the source. The gate is still an exact-match check, so any other value fails it.
- **Effect on conclusions:** None. This is a label spelling and changes no estimate or conclusion. The website displays the label as "Suburban" through a single presentation-layer mapping, with a footnote giving the source spelling. Analysis code and JSON exports keep the raw level.

**2026-09-23 · Heterogeneity dimension 1 has three observed levels; Sections 6–8 method clarifications**
- **Timing:** This entry was written after the outcome-unlock commit (`cf44832`) and **before any effect estimate was computed**. The only data inspected to write it are covariate cell counts (`mens` × `womens`, overall and by arm). These are pre-period covariates; no outcome (`visit`, `conversion`, `spend`) was computed, printed or viewed.
- **What changed (Section 8, dimension 1):** The plan says to cross `mens` and `womens` into four groups. The data contains three: men's only (`mens=1, womens=0`), women's only (`mens=0, womens=1`), and both (`mens=1, womens=1`). The neither/neither cell is empty, because every customer in the population is a recent purchaser of at least one of the two. Dimension 1 is therefore estimated with three levels, and its joint interaction test has 2 degrees of freedom instead of 3. It remains one test per email arm, so the Holm family is still 8 tests (4 dimensions × 2 arms).
- **Clarifications (methods the plan leaves open, fixed here before any result is visible):**
  1. *Bootstrap vs analytic agreement (Section 6).* "Agree in sign" means both 95% intervals lie entirely above zero, both lie entirely below zero, or both include zero. "Approximately in width" means the width ratio (bootstrap ÷ analytic) is between 0.8 and 1.25. Failing either is reported rather than resolved.
  2. *Bootstrap draws.* Each arm is resampled once: 10,000 resamples within the arm, seed 20260923, arms drawn in a fixed order. H1, H2 and H3 all use the same per-arm resampled means.
  3. *Relative lift.* Treatment mean ÷ comparison mean − 1, with a delta-method standard error and a normal 95% interval. For H3 (Mens vs Womens) the comparison group is Womens.
  4. *Secondary metrics.* The two-proportion z-test uses the pooled standard error. The Newcombe hybrid score interval (Newcombe 1998, method 10) uses Wilson intervals without continuity correction.
  5. *CUPED (Section 7).* θ = cov(spend, history) ÷ var(history), estimated on all rows pooled across the three arms. `history` is centred at its pooled mean. Variance reduction per arm is 1 − Var(adjusted) ÷ Var(unadjusted), measured within that arm. It is applied to H1 and H2 only.
  6. *Heterogeneity (Section 8).* Each model is fitted on one email arm plus No E-Mail. The joint Wald test of the interaction terms uses the chi-square form with the HC3 covariance. Each segment's treatment effect is the linear combination of the treatment coefficient and that segment's interaction coefficient. Its 95% CI is computed from the full HC3 covariance matrix, **including the covariance between the two coefficients**.
- **Effect on conclusions:** None on Sections 6 and 7. On Section 8, dimension 1 has one fewer interaction term, reflecting how the population is actually structured rather than any analysis choice. The recommendation logic (Sections 9–10) is unaffected.

**2026-09-24 · Sections 9–10: targeting policies, uplift model, policy-value estimator, winner rule, decision rule application**
- **Timing:** Written after the Sprint 2 estimates were published (Sections 6–8, commit `8c7d7e4`) and **before any train/holdout split, targeting model or policy value existed**. No holdout exists when this entry is committed.
- **Why this entry is needed:** Section 9 compares the model against "a simple rule derived from Section 8". No Section 8 interaction test survived Holm correction, and the segment estimates are already public, so a hand-picked rule would be post hoc. Several estimator details are also not fixed by the plan. Everything below is fixed now, before any split.
- **1a. Policies.** Each policy maps a customer to exactly one action in {Mens, Womens, None}.
  - **P0:** send nothing.
  - **P1:** everyone gets Mens.
  - **P2:** everyone gets Womens.
  - **P3:** CV-selected segment rule.
    - For each of the four Section 8 dimensions (dimension 1 with its three observed levels), a candidate rule gives each level the action with the highest training-estimated net revenue per customer. For action A in level ℓ that value is mean spend(A, ℓ) − mean spend(None, ℓ) − $0.10; None scores 0.
    - The four candidates are compared by 5-fold CV on the training split only (KFold, shuffled, seed 20260923). Each fold builds the rule on 4 folds and scores the 5th with the 1c inverse-probability net-value estimator. The highest mean CV net value wins; ties go to dimension order. The selected rule is refit on the full training split.
    - No human choice is involved.
  - **P4a / P4b:** Mens (or Womens) goes to the top k% of customers by predicted incremental revenue for that arm, and None to the rest, for k ∈ {10, 20, …, 100}. **k is selected for each arm by 5-fold CV net value on the training split** (same folds and estimator as P3), so P4a and P4b each enter the holdout comparison as one pre-selected policy. The holdout net-value-vs-k curves are reported as descriptive only. With k selected by training CV, **the holdout comparison involves exactly seven pre-selected policies: P0, P1, P2, P3, P4a, P4b, P5.**
  - **P5:** each customer gets the action with the highest predicted net incremental revenue (predicted uplift − cost), or None if both predicted net values are ≤ 0. On the cost grid, P5's assignment is recomputed at each cost.
- **1b. Uplift model.**
  - A two-model estimator: separate `HistGradientBoostingRegressor` models for spend in Mens, Womens and No E-Mail, trained on the training split.
  - Features are `recency`, `history`, `mens`, `womens`, `zip_code`, `newbie`, `channel`. `history_segment` is excluded as redundant. `zip_code` and `channel` use the model's native categorical support.
  - Hyperparameters are tuned per arm by 5-fold CV mean squared error (KFold, shuffled, seed 20260923) over the grid `max_depth` {3, 5} × `learning_rate` {0.05, 0.1} × `max_iter` {100, 300} × `min_samples_leaf` {50, 200}. The lowest mean CV MSE wins; ties go to grid order.
  - Predicted uplift for arm A = pred_A − pred_None.
  - Out-of-fold predictions for the training diagnostics use the chosen hyperparameters. Because tuning used the same training data, the out-of-fold diagnostics are mildly optimistic, and this is stated wherever they are reported.
- **Qini curve and coefficient.**
  - For arm A, the population is the customers in A or No E-Mail, ranked by predicted uplift for A (descending).
  - At each fraction φ of that ranking (100 points): Q(φ) = R_T(φ) − R_C(φ) · N_T(φ) / N_C(φ).
    - R_T(φ) and R_C(φ) are cumulative spend of treated and control customers within the top φ.
    - **N_T(φ) and N_C(φ) are the cumulative treated and control counts within the top φ of the ranking, not the arm totals.**
  - The Qini coefficient is the area between Q and the random-targeting line from (0, 0) to (1, Q(1)), divided by the population size, in dollars per customer.
  - It is reported out-of-fold on training, and on the holdout for P4a and P4b.
- **1c. Policy value on the holdout.**
  - Primary estimator: V(π) = mean over holdout customers of spend × 1{T = π(x)} × 3. This uses the nominal randomization probabilities of 1/3.
  - Net value: NV(π) = V(π) − cost × (share of holdout customers with π(x) ≠ None).
  - Each policy's net value and incremental revenue per customer are reported relative to P0.
  - Uncertainty: 2,000 bootstrap resamples of the holdout (seed 20260923), with every policy computed on each resample so comparisons are paired. Intervals are percentile.
  - **Robustness check only:** the self-normalized (Hájek) value, which weights each arm by the holdout's actual arm share (V_H(π) = Σ_a (1/n_a) Σ_{i: T=a, π(x_i)=a} spend_i), is reported alongside the nominal value for every policy. The nominal estimate remains primary for 1d. Any policy where the two estimators disagree on sign relative to P0 is flagged in the report.
- **1d. Winner rule.**
  - The recommended policy is the one with the highest nominal holdout net value at $0.10.
  - A targeted policy (P3, P4a, P4b or P5) replaces the best blanket policy (whichever of P1 and P2 has the higher holdout net value) **only if** the paired bootstrap 95% CI of their net-value difference lies entirely above zero. Otherwise the best blanket policy is recommended, and the readout states that targeting did not demonstrably beat blanket sending on this data.
  - If P0 has the highest net value, the recommendation is to send nothing.
- **1e. Decision rule (Section 10), using the full-sample Section 6 estimates.**
  - The interval is the Welch analytic 95% CI, the plan's primary interval; the bootstrap bound is reported alongside.
  - Status of each email at $0.10:
    - "send" if the lower bound > cost;
    - "promising — test again" if the point estimate > cost ≥ the lower bound;
    - "do not send" otherwise.
  - Sensitivity: costs from $0.01 to $0.50 in $0.01 steps.
  - Break-even cost at the point estimate and at the lower bound, computed exactly rather than read off the grid.
  - **Combining 1d and 1e:** the recommendation is the 1d winner, and each email it sends carries its 1e status. If any email it sends is not "send", the recommendation for that email becomes "promising — test again".
- **1f. Supplementary margin view** (a presentation aid derived from pre-registered quantities, not pre-registered itself; the data contains no margin). Minimum gross margin at which sending is justified = cost ÷ incremental revenue per customer, at the point estimate and at the lower bound, for the default cost only.
- **1g. Holdout discipline.**
  - The split is 70/30, stratified by arm, seed 20260923, created by one function in `liftlab/split.py`.
  - The SHA-256 of the sorted holdout customer indices is committed before any model is trained.
  - Holdout rows are readable only from `liftlab/evaluate.py`; the data layer raises an error anywhere else.
  - The holdout is evaluated once, in a dedicated commit, and is never re-evaluated unless a new Deviations entry justifies it. Re-running the pipeline may only reproduce the committed evaluation and verify it is byte-identical; it may not change it.
- **Effect on conclusions:** None on Sections 6–8. This entry fully determines how Sections 9–10 turn the estimates into a recommendation, before any holdout result can influence those choices.

**2026-09-24 · Project renamed**
- Project renamed from LiftLab to Email Experiment Readout on 2026-09-24 to avoid confusion with LiftLab Analytics, Inc. The plan's content is unchanged; references to LiftLab in this document refer to this project.
