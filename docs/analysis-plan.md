# LiftLab — Pre-Registered Analysis Plan

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
