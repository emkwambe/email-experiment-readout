# Sprint 3: verification evidence

Commands run by Claude Code during Sprint 3 (2026-09-24 UTC), with their output pasted as printed. The statistics
below are copies of values in the committed JSON. `targeting.json` comes from the single holdout evaluation in
`c989424`; the other exports were regenerated from a clean tree at `92877e9` and committed in `b856d89`. After this file was committed, the exports were regenerated once more so that `timeline.json` lists it. That changed only the manifests and the workflow-file list; see `git log` for the final export commit and the `v1.0` tag.

## Timeline (commits in order)

| Commit | What |
|---|---|
| `4c93de8` | Step 0: preflight, evidence image policy (WebP, 300 KB limit), H3 and CUPED notes |
| `363e98b` | **Deviations entry for Sections 9–10**, committed before any split existed |
| `faeccea` | Split module and holdout guard (no model code) |
| `3731c5a` | **Split sealed**: holdout index SHA-256 `cbe0ca3086bbcdc82c7dcbc2d3680359916dfe31d5817f7632542cd6e6843002` |
| `dff58b9` / `f78b57c` | Training-split models and rule selection, then its exports (holdout untouched) |
| `0c12642` | `evaluate.py`, tested on synthetic outcomes only |
| `c9894241` | **Holdout evaluation (single use)**: contains only `targeting.json` |
| `080304a` / `03fe930` | Section 10 application (`decision.json`) |
| `bbeb180` / `e128110` | Readout pages, git timeline, correction statistics. `bbeb180` was committed with one failing (stale-export) test; see the correction log. |
| `92877e9` / `b856d89` | Screenshot-review fixes, smoke checks, generated README blocks; exports from a clean tree |

## Environment preflight (Step 0.1)

```
> py -0p
 -V:3.13 *        C:\Program Files\Python313\python.exe
 -V:3.12          C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe
 -V:3.11          C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe
> node -v               v22.18.0
> vercel --version      Vercel CLI 58.4.4
> gh auth status        ✓ Logged in to github.com account emkwambe (keyring)
```

## Holdout discipline

- The split (44,800 train / 19,200 holdout, stratified by arm) was committed in `3731c5a` before `models.py` existed.
- `SplitData.holdout()` raises `HoldoutAccessError` for any caller other than `liftlab/evaluate.py`. Tests call it
  directly, through a helper, and from code compiled as `liftlab/models.py`, and it raises every time.
- The evaluation ran once, on a clean tree:
  ```
  > python -m liftlab.evaluate            (at 0c12642, 53.7 s)
  {"winner": {"highest_net_value": "P1", "best_blanket": "P1", "winner": "P1", "targeting_beat_blanket": false,
   "reason": "P1 (a blanket policy) has the highest holdout net value."}, "hajek_sign_flags": []}
  > python -m liftlab.evaluate --verify
  verify: recomputed evaluation MATCHES the committed targeting.json
  > python -m liftlab.evaluate
  REFUSED: targeting.json exists; the holdout is evaluated once (Deviations 2026-09-24, 1g). Use --verify to reproduce it.
  ```
- Rerunning the training stage is deterministic: `training.json` changed only in its manifest fields.

## Training split (Step 3)

- Every arm chose depth 3, learning rate 0.05, 100 iterations and min leaf 200, the most regularized corner of the grid.
- Out-of-fold Qini (mildly optimistic): Mens −0.0274, Womens +0.0217 dollars per customer.
- P3 CV net value per customer: prior_merchandise +1.3673, newbie +1.3673, channel +1.3249, zip_code +1.3445.
  - prior_merchandise and newbie tie exactly because both rules send Mens to every segment. The tie-break (dimension order) selected prior_merchandise, so P3 is identical to P1.
- P4 k chosen by CV: 100% for both arms, so P4a ≡ P1 and P4b ≡ P2.
- P5 out-of-fold action shares at $0.10: Mens 64.0%, Womens 26.5%, None 9.5%.

## Holdout results (nominal IPW, 2,000 paired bootstrap resamples, dollars per customer, cost $0.10)

| Policy | Sends to | Net value vs P0 [95% CI] | Incremental revenue vs P0 [95% CI] | vs best blanket (P1) [95% CI] | Hájek incremental |
|---|---|---|---|---|---|
| P0 | 0.0% | +0.0000 | +0.0000 | — | +0.0000 |
| P1 | 100.0% | +0.3696 [−0.2173, +0.9283] | +0.4696 [−0.1173, +1.0283] | — | +0.4701 |
| P2 | 100.0% | +0.2013 [−0.2948, +0.7060] | +0.3013 [−0.1948, +0.8060] | — | +0.2974 |
| P3 | 100.0% | +0.3696 [−0.2173, +0.9283] | +0.4696 [−0.1173, +1.0283] | +0.0000 [+0.0000, +0.0000] (identical to P1) | +0.4701 |
| P4a | 100.0% | +0.3696 [−0.2173, +0.9283] | +0.4696 [−0.1173, +1.0283] | +0.0000 [+0.0000, +0.0000] (identical to P1) | +0.4701 |
| P4b | 100.0% | +0.2013 [−0.2948, +0.7060] | +0.3013 [−0.1948, +0.8060] | −0.1682 [−0.7851, +0.3841] | +0.2974 |
| P5 | 93.8% | +0.3163 [−0.2333, +0.8565] | +0.4102 [−0.1395, +0.9503] | −0.0532 [−0.3951, +0.2559] | +0.4095 |

- **Winner (rule 1d): P1.** Targeting did not beat blanket sending.
- **Hájek check:** no sign disagreements.
- **P5 holdout assignment:** Mens 69.6%, Womens 24.2%, None 6.2%.
- **Holdout Qini:** Mens −0.0437, Womens −0.0055 dollars per customer.
- **Holdout net value vs P0 by k (descriptive):**
  - Mens 10→100%: −0.078, −0.079, −0.033, +0.046, +0.051, +0.084, +0.212, +0.282, +0.302, +0.370.
  - Womens: +0.120, +0.075, −0.014, +0.065, +0.127, +0.187, +0.172, +0.110, +0.107, +0.201.
- **Cost grid, net value vs P0:**

  | Cost | P1 | P2 | P5 (sends to) |
  |---|---|---|---|
  | $0.01 | +0.460 | +0.291 | +0.384 (95%) |
  | $0.25 | +0.220 | +0.051 | +0.161 (90.5%) |
  | $0.50 | −0.030 | −0.199 | −0.169 (78.2%) |

- **Note:** on the holdout alone, every policy's 95% interval against sending nothing includes zero. The holdout covers 30% of customers and the IPW policy-value estimator is noisier than a difference in means. The "send" status therefore rests on the pre-registered full-sample Section 6 estimate (rule 1e), and the holdout decides only which policy to use (rule 1d).

## Decision (Section 10, full-sample Welch intervals)

| Email | Status at $0.10 | Break-even at estimate | Break-even at lower bound (bootstrap LB) | Min. margin at estimate / lower bound (supplementary) |
|---|---|---|---|---|
| Mens E-Mail | send | $0.7698 | $0.4851 ($0.4934) | 13.0% / 20.6% |
| Womens E-Mail | send | $0.4244 | $0.1690 ($0.1712) | 23.6% / 59.2% |

Generated recommendation (from `decision.json`):

> Send the Mens E-Mail to every customer: in the full experiment it added $0.77 of revenue per customer (95% CI $0.49 to $1.05), against an assumed send cost of $0.10 per email; on the untouched holdout, no targeting policy beat sending to everyone.

## Independent verification (Step 6, as tests)

- **IPW policy value on synthetic data:** the 95% CI covers the known true net value (2.6) in at least 16 of 20 replications, and the point estimate is within 0.03 at n = 300,000.
- **DuckDB SQL from the raw CSV,** restricted to the holdout inside `evaluate.py` and returning aggregates only: V(P0), V(P1) and V(P2) match `targeting.json` to 1e-9.
- **Consistency with Section 6:** P1's holdout increment CI [−0.1173, +1.0283] overlaps the full-sample H1 CI [0.4851, 1.0545].
- **Break-even costs and margins** match hand computation from the JSON inputs; every template branch fills all its placeholders.
- **Holdout guard:** raises for calls from test code, from helpers, and from code compiled as `liftlab/models.py`.
- **`meta.py` stays read-only:** it imports nothing from pandas, numpy or `liftlab` (static and import-time checks) and opens nothing under `data/` (runtime spy).

```
> python -m pytest analysis\tests -q
123 passed in 58.97s
```

## Production smoke test

```
> npm --prefix C:\Dev\liftlab-email-experiment\web run smoke
Smoke test against https://liftlab-email-experiment.vercel.app
PASS  GET / returns 200  (status 200)
PASS  GET /plan returns 200  (status 200)
PASS  GET /checks returns 200  (status 200)
PASS  GET /how-its-built returns 200  (status 200)
PASS  GET /results returns 200  (status 200)
PASS  GET /targeting returns 200  (status 200)
PASS  manifest.json loads  (status 200)
PASS  manifest dataset SHA-256 matches docs/data-source.md  (deployed 00a6a868e05a…, documented 00a6a868e05a…)
PASS  srm.json has a numeric p-value  (p_value 0.9036929575604196)
PASS  effects_primary.json H1 has a numeric Holm-adjusted p-value  (p_holm 2.3276299364509635e-7)
PASS  effects_primary.json H2 has a numeric Holm-adjusted p-value  (p_holm 0.0011293971023632473)
PASS  manifest.json lists every export  (13 files)
PASS  integrity.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  srm.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  balance.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  power.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  effects_primary.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  effects_secondary.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  cuped.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  heterogeneity.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  split.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  training.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  decision.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  timeline.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  targeting.json manifest dataset SHA-256 matches docs/data-source.md  (status 200, 00a6a868e05a…)
PASS  decision.json has a recommendation object  (P1)
PASS  decision.json break-even costs are numeric  (0.7698, 0.4851, 0.4244, 0.1690)
PASS  timeline.json includes the pre-registration SHA 48c63f4
PASS  targeting.json has the winner  (P1)
PASS  targeting.json has the evaluation code commit SHA  (0c12642)
PASS  holdout evaluation commit SHA is published (timeline.json)  (c989424)
31/31 checks passed
```

## 390 px screenshots (Playwright, 390×844, mobile emulation, light and dark, against production)

All 12 page/theme combinations pass: status 200, scrollWidth 390 / clientWidth 390, no clipped scroll boxes.
The WebP set is in `ai-workflow/evidence/sprint-3/`; the largest image is 201,460 bytes, under the 300 KB limit
enforced by `tests/test_evidence.py`.

Claude Code reviewed desktop and 390 px captures before deploying and fixed:
- targeted policies identical to P1 that were shown only as "+$0.00";
- a wrapped break-even marker label;
- a duplicated "supplementary" label;
- crowded axis ticks on the policy chart.

## v1.0.1 addendum (patch release, tag `v1.0.1` at `5491933`)

### What changed

- **Readout Section 5 (funnel) corrected.** The v1.0 sentence "the emails brought many more customers to the site than they turned into buyers" was contradicted by the data and has been removed, along with the landing-experience question.
  - `effects_secondary.json` now exports delta-method relative lifts for visits and purchases, labelled supplementary and not pre-registered.
  - It also exports purchase rate among visitors per arm, marked `descriptive_only` with the post-treatment selection caveat.
  - Section 5 is generated from those fields. Both emails lifted visits and purchases. For both, the point estimate of the purchase lift exceeds the visit lift (Mens +119% vs +72%; Womens +54% vs +43%), but the intervals overlap, so the ordering is stated as not statistically established.
  - Purchase rate among visitors (descriptive only): 5.4% with no email, 6.9% Mens, 5.8% Womens.
- **Section 3** now states that the holdout exists to compare targeting against blanket sending, not to re-confirm the email effect, which rests on the pre-registered full-sample test.
- **Sources lines.** Every interpretive sentence on `/` (Sections 2, 3, 5 and 6) is generated conditionally from exported fields and followed by a "Sources" line naming those fields.

### Correction-log entries added

1. **Funnel interpretation on the readout was contradicted by the data.**
   - Origin: Claude Chat.
   - Why it lasted: it survived three sprints because the tests verified numbers, not the conclusions drawn from them.
   - Caught by: human review of the live readout.
   - Guard: every interpretive sentence cites its exported fields, and review checks each one.
2. **Correction-log parser silently dropped entries not labelled "Sprint N"** (see below).
   - Origin: Claude Code.
   - Caught by: Claude Code's review of the regenerated README block.
   - Guard: an independent heading-count test.

The log now has 16 entries: 12 from Claude Code, 4 from Claude Chat.

### The `c199d84` undercount and its fix

The Sprint 3 parser in `liftlab/meta.py` matched only `· Sprint N ·` headings, so the first v1.0.1 entry (`· v1.0.1 ·`) was skipped. Commit `c199d84` (v1.0.1 exports) therefore published 14 correction-log entries in `timeline.json`, `/how-its-built` and the README, when the log had 15. The existing consistency test compared the export with the same parser, so it passed.

Commit `90b33eb` fixed it:
- the heading pattern accepts any phase label;
- entries carry a `phase` field;
- `test_every_log_heading_is_parsed` counts headings with an independent pattern;
- `test_parser_accepts_release_phase` covers release labels.

The statistics were regenerated in `90b33eb` and again from a clean tree in `5491933`.

### Commits

| Commit | What |
|---|---|
| `761a3ee` | Funnel correction, sourced sentences, correction-log entry 1 |
| `c199d84` | Exports from a clean tree (carries the undercount) |
| `90b33eb` | Parser fix, independent count test, correction-log entry 2 |
| `5491933` | Exports from a clean tree at `90b33eb`; tagged `v1.0.1` |

Every commit was gated on pytest's own exit code (`set -euo pipefail` and `PIPESTATUS[0]`).

### Test and smoke results

```
> python -m pytest analysis\tests -q        (at 5491933)
127 passed in 76.18s (0:01:16)
> npm --prefix C:\Dev\liftlab-email-experiment\web run smoke
31/31 checks passed
```

- The deployed `/` shows "Both emails lifted visits and purchases: every interval lies above zero." and the holdout-purpose sentence. The old "turned into buyers" and landing-experience text is absent.
- The 390 px check (all 6 pages × light and dark) passes against the local v1.0.1 build: no page overflow and no clipped scroll boxes. Those PNGs are in the gitignored `ai-workflow/evidence/full/`; no new WebPs were committed for the patch.

### Holdout evaluation unchanged

`web/public/data/targeting.json` was not modified by any v1.0.1 commit. `git log -1 --format=%h -- web/public/data/targeting.json` returns `c989424`, the single-use holdout evaluation commit, and the smoke test confirms its manifest dataset hash.
