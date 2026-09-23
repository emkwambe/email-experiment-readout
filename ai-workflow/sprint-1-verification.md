# Sprint 1: verification evidence

Commands run by Claude Code at the end of Sprint 1 (2026-09-23), with their output pasted as printed. The statistics
quoted here are copies of what the commands printed. The source of truth is the JSON in `web/public/data/`.

## Environment preflight

```
> py -0p
 -V:3.13 *        C:\Program Files\Python313\python.exe
 -V:3.12          C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe
 -V:3.11          C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe
> node --version        v22.18.0
> vercel --version      Vercel CLI 58.4.4
> gh auth status        Logged in to github.com account emkwambe (keyring)
```

Python 3.12 was missing at the start of the sprint and was installed with winget (see the correction log).

## Pipeline

```
> C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m liftlab.run --stage sprint1
{
  "manifest": {
    "commit_sha": "88c6236646ca569a78d4dc0b5c72255edf0476f2",
    "working_tree_dirty": false,
    "dataset_sha256": "00a6a868e05a9ffe7382da51629f6d6dce88c5acfc945e79d314ebc78fd3a2c0",
    "generated_utc": "2026-09-23T23:18:14Z",
    "script": "python -m liftlab.run --stage sprint1",
    "seed": 20260923,
    "stage": "sprint1"
  },
  "summary": {
    "integrity_passed": true,
    "srm_p_value": 0.9036929575604196,
    "srm_halt": false,
    "balance_n_flagged": 0,
    "halted": false
  }
}
exit=0
```

## Tests

```
> C:\dev\liftlab-email-experiment\analysis\.venv\Scripts\python.exe -m pytest C:\dev\liftlab-email-experiment\analysis\tests -q
...........................................                              [100%]
43 passed in 1.86s
```

The outcome-lock guard (`tests/test_outcome_lock.py`) was also mutation-checked against the real exports. When the
`basis: assumed_parameters` marker was removed from the power rows, it flagged 12 of 12. When one balance covariate
was renamed to `spend`, it flagged `rows`.

## Production smoke test

```
> npm --prefix C:\dev\liftlab-email-experiment\web run smoke
Smoke test against https://liftlab-email-experiment.vercel.app
PASS  GET / returns 200  (status 200)
PASS  GET /plan returns 200  (status 200)
PASS  GET /checks returns 200  (status 200)
PASS  GET /how-its-built returns 200  (status 200)
PASS  manifest.json loads  (status 200)
PASS  manifest dataset SHA-256 matches docs/data-source.md  (deployed 00a6a868e05a…, documented 00a6a868e05a…)
PASS  srm.json has a numeric p-value  (p_value 0.9036929575604196)
7/7 checks passed
```

## Manual checks

- The deployed `/plan` includes the 2026-09-23 Deviations entry, which confirms the build-time copy of the plan was uploaded.
- The deployed `/checks` shows "Zip code class: Suburban" with a footnote giving the source spelling "Surburban".
  `balance.json` keeps `zip_code=Surburban`, and a test asserts this.
- Headless Edge screenshots of `/checks` at 1100 px and 540 px: no horizontal overflow at 540 px. Headless Edge
  enforces a minimum window width of about 500 px, so a true 390 px phone viewport could not be captured this way.
