# Sprint 2: verification evidence

Commands run by Claude Code during Sprint 2 (2026-09-23 to 2026-09-24 UTC), with their output pasted as printed. The
statistics below are copies of values in the committed JSON, generated at `35adf56` and committed in `8c7d7e4`. The
JSON in `web/public/data/` is the source of truth.

## Timeline (the order is what makes the estimates credible)

| Commit | What | Outcomes visible? |
|---|---|---|
| `48c63f4` | Pre-registration (Sprint 1) | No |
| `77d4a07` | Step 0: preflight, rule 5 wording, SMD corrected, 390 px check | No |
| `cf44832` | **Outcome unlock**: CLAUDE.md rule 2 lifted for Sections 6–8; rule 9 (no targeting) | No |
| `7a3e092` | Deviations entry: dimension 1 has three levels, and the Sections 6–8 method clarifications. Written using covariate-only cell counts | No |
| `35adf56` | `effects.py`, `heterogeneity.py`, tests, `/results` | Yes: first estimates computed while this code was being written |
| `8c7d7e4` | Exports from a clean tree at `35adf56` | Yes |

No effect estimate was computed before `7a3e092`. The only data inspected between `cf44832` and `7a3e092` were the
covariate counts of `mens` × `womens`, overall and by arm.

## Environment preflight (Step 0.1)

```
> py -0p
 -V:3.13 *        C:\Program Files\Python313\python.exe
 -V:3.12          C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe
 -V:3.11          C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe
> node -v               v22.18.0
> vercel --version      Vercel CLI 58.4.4
> gh auth status        ✓ Logged in to github.com account emkwambe (keyring); scopes 'gist', 'read:org', 'repo', 'workflow'
```

## Pipeline

```
> C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.run --stage sprint2
  "manifest": {
    "commit_sha": "35adf56815e9cf20c91894cfd1b3af7926c8541e",
    "working_tree_dirty": false,
    "dataset_sha256": "00a6a868e05a9ffe7382da51629f6d6dce88c5acfc945e79d314ebc78fd3a2c0",
    "generated_utc": "2026-09-24T00:01:43Z",
    "script": "python -m liftlab.run --stage sprint2",
    "seed": 20260923,
    "stage": "sprint2"
  },
  "summary": {
    "integrity_passed": true,
    "srm_p_value": 0.9036929575604196,
    "srm_halt": false,
    "balance_n_flagged": 0,
    "halted": false,
    "effects_agreement_passed": true,
    "cuped_signs_agree": true,
    "heterogeneity_n_tests": 8,
    "heterogeneity_n_reject_holm": 0
  }
exit=0
```

## Tests

```
> C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pytest C:\dev\liftlab-email-experiment\analysis\tests -q
78 passed in 15.10s
```

What the Sprint 2 tests check independently (Step 6):
- **DuckDB SQL from the raw CSV:** arm mean spend, the H1 and H2 differences, and visit and conversion rates and counts all match the exported values to 1e-9.
- **Welch:** matches `scipy.stats.ttest_ind(equal_var=False)` and statsmodels `CompareMeans.ttest_ind(usevar="unequal")` (t, df, p and CI), on synthetic data and on the real data.
- **Newcombe method 10:** reproduces Newcombe (1998) Table II, 56/70 vs 48/80 → (0.0524, 0.3339) and 9/10 vs 3/10 → (0.1705, 0.8090), and matches statsmodels `confint_proportions_2indep(method="newcomb")`.
- **Holm:** matches a hand-computed example (0.01, 0.04, 0.03) → (0.03, 0.06, 0.06) and statsmodels `multipletests`.
- **CUPED:** θ equals the OLS slope of spend on history, on synthetic data and on the real data (rel. 1e-9).
- **Bootstrap:** the 95% percentile CI covers a known difference (0.5) in at least 34 of 40 synthetic replications, and the exported bootstrap CIs reproduce exactly when re-run.
- **Heterogeneity:**
  - Segment effects equal within-segment differences in means.
  - The joint Wald χ² matches statsmodels `wald_test`.
  - Segment SEs match `t_test` on the T + T×segment contrast, which includes the covariance term.
- **Outcome lock and rule 9:**
  - By-arm outcomes appear only in the four Sprint 2 files.
  - No unknown export exists.
  - No export key or code file contains targeting, policy, holdout or split patterns.

## Results as exported (dollars per customer unless stated)

**Primary (revenue per customer).** Holm family = H1, H2. The agreement check requires the bootstrap ÷ analytic width
ratio to be within 0.8–1.25, with the same sign pattern.

| | Contrast | Difference | Welch 95% CI | Bootstrap 95% CI | Width ratio | p | Holm p | Relative lift (95% CI) |
|---|---|---|---|---|---|---|---|---|
| H1 | Mens E-Mail vs No E-Mail | 0.7698 | [0.4851, 1.0545] | [0.4934, 1.0596] | 0.9945 | 1.16e-07 | 2.33e-07 | +1.179 [+0.544, +1.814] |
| H2 | Womens E-Mail vs No E-Mail | 0.4244 | [0.1690, 0.6799] | [0.1712, 0.6821] | 1.0001 | 0.00113 | 0.00113 | +0.650 [+0.149, +1.151] |
| H3 | Mens E-Mail vs Womens E-Mail | 0.3454 | [0.0326, 0.6583] | [0.0370, 0.6663] | 1.0057 | 0.0305 | outside family | +0.321 [−0.012, +0.653] |

All three agreement checks pass; every interval lies entirely above zero in both methods.

**Secondary (difference in proportions, Newcombe 95% CI, Holm within metric).**

| Metric | | Difference | Newcombe 95% CI | p | Holm p |
|---|---|---|---|---|---|
| Visit rate | H1 | 0.07659 | [0.06995, 0.08323] | 5.69e-112 | 1.14e-111 |
| Visit rate | H2 | 0.04523 | [0.03889, 0.05157] | 3.18e-44 | 3.18e-44 |
| Conversion rate | H1 | 0.00681 | [0.00501, 0.00864] | 1.52e-13 | 3.05e-13 |
| Conversion rate | H2 | 0.00311 | [0.00150, 0.00475] | 0.000157 | 0.000157 |

Spend among converters is exported as descriptive only (`descriptive_only: true`), with no test or interval.

**CUPED.** θ = 0.0012754870330541766. Variance reduction: No E-Mail 0.0044%, Mens E-Mail 0.0599%, Womens E-Mail 0.0541%.
Adjusted H1 is 0.7673 [0.4827, 1.0520] and adjusted H2 is 0.4223 [0.1669, 0.6777]. The signs agree with the
unadjusted estimates, which remain primary. The near-zero reduction was checked independently: pooled corr(spend,
history) = 0.02173, and each arm's reduction is at or below its within-arm r².

**Heterogeneity (joint Wald χ², HC3; Holm across 8).**

| Arm | Dimension | χ² | df | p | Holm p | Rejects |
|---|---|---|---|---|---|---|
| Mens E-Mail | prior_merchandise | 2.95 | 2 | 0.228 | 1.000 | no |
| Mens E-Mail | newbie | 1.73 | 1 | 0.189 | 1.000 | no |
| Mens E-Mail | channel | 2.22 | 2 | 0.330 | 1.000 | no |
| Mens E-Mail | zip_code | 0.05 | 2 | 0.977 | 1.000 | no |
| Womens E-Mail | prior_merchandise | 2.14 | 2 | 0.343 | 1.000 | no |
| Womens E-Mail | newbie | 5.62 | 1 | 0.018 | 0.142 | no |
| Womens E-Mail | channel | 3.58 | 2 | 0.167 | 1.000 | no |
| Womens E-Mail | zip_code | 3.08 | 2 | 0.215 | 1.000 | no |

0 of 8 interaction tests survive Holm correction. Segment estimates with CIs and sample sizes are in `heterogeneity.json`.

## Production smoke test

```
> npm --prefix C:\Dev\liftlab-email-experiment\web run smoke
Smoke test against https://liftlab-email-experiment.vercel.app
PASS  GET / returns 200  (status 200)
PASS  GET /plan returns 200  (status 200)
PASS  GET /checks returns 200  (status 200)
PASS  GET /how-its-built returns 200  (status 200)
PASS  GET /results returns 200  (status 200)
PASS  manifest.json loads  (status 200)
PASS  manifest dataset SHA-256 matches docs/data-source.md  (deployed 00a6a868e05a…, documented 00a6a868e05a…)
PASS  srm.json has a numeric p-value  (p_value 0.9036929575604196)
PASS  effects_primary.json H1 has a numeric Holm-adjusted p-value  (p_holm 2.3276299364509635e-7)
PASS  effects_primary.json H2 has a numeric Holm-adjusted p-value  (p_holm 0.0011293971023632473)
PASS  effects_primary.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  effects_secondary.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  cuped.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  heterogeneity.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
14/14 checks passed
```

## 390 px screenshots (Playwright, 390×844, mobile emulation, light and dark)

```
> npm --prefix C:\Dev\liftlab-email-experiment\web run screenshots      (against production)
PASS  / [light] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> home-390-light.png
PASS  /plan [light] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> plan-390-light.png
PASS  /checks [light] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> checks-390-light.png
PASS  /how-its-built [light] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> how-its-built-390-light.png
PASS  /results [light] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> results-390-light.png
PASS  / [dark] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> home-390-dark.png
PASS  /plan [dark] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> plan-390-dark.png
PASS  /checks [dark] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> checks-390-dark.png
PASS  /how-its-built [dark] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> how-its-built-390-dark.png
PASS  /results [dark] status 200, scrollWidth 390 / clientWidth 390, clipped scroll boxes 0 -> results-390-dark.png
```

Screenshots are in `ai-workflow/evidence/sprint-2/`. Claude Code also reviewed them visually; the defects found and
fixed are in the correction log.

## Other checks

- Chart palette (series 1 and 2, blue and orange) validated with the dataviz validator: all checks pass in light mode
  (surface `#ffffff`, worst CVD ΔE 24.7) and dark mode (surface `#181b20`, worst CVD ΔE 26.8). The bootstrap and
  adjusted series are also dashed, as a second encoding.
- Deployed `/` shows "Effects estimated · targeting pending", and deployed `/results` shows the Sprint 3 note.
- Sweep of tracked code outside `docs/`, `ai-workflow/` and tests for `train_test_split`, `StratifiedShuffleSplit`,
  `KFold`, `GradientBoost`, `qini`, `uplift_at_k`, `holdout` and `TwoModels`: none found.
