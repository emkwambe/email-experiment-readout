# Correction Log

This log records every place where AI-generated work (Claude Code or Claude Chat) was wrong, incomplete, or overconfident, and how the error was caught. It exists because the value of AI-assisted analysis depends on the verification around it, and that verification should be visible.

Each entry is added in the same commit as its fix.

## Entry format

**YYYY-MM-DD · Sprint N · short title**
- **What was produced:** what the AI generated.
- **What was wrong:** the specific error.
- **How it was caught:** which test, check, gate, or human review found it.
- **Fix:** what changed; commit SHA.
- **Lesson / guard added:** a new test or rule, if any, that prevents recurrence.

## Entries

**2026-09-23 · Sprint 1 · CLAUDE.md specified a Python runtime that was not installed**
- **What was produced:** During planning, Claude Chat wrote CLAUDE.md with `py -3.12 -m venv ...` as the environment setup command.
- **What was wrong:** Nobody checked which Python runtimes were installed. The machine had only 3.13 and 3.11, so `py -3.12` failed with "No suitable Python runtime found."
- **How it was caught:** Claude Code ran `py -0p` at the start of Sprint 1 Step 2, stopped, and reported the failure instead of switching to another Python version.
- **Fix:** Python 3.12.10 was installed with `winget install -e --id Python.Python.3.12`, and `py -0p` confirmed it was registered. The spec was left unchanged. Committed with the Step 2 scaffold.
- **Lesson / guard added:** Every future sprint file must include an environment preflight step (`py -0p`, `node -v`, `vercel --version`, `gh auth status`) before any setup commands.

**2026-09-23 · Sprint 1 · Editable install line in requirements.txt resolved against the wrong directory**
- **What was produced:** Claude Code added `-e .` to `analysis\requirements.txt` so that the one CLAUDE.md install command would also install the `liftlab` package.
- **What was wrong:** pip resolves relative paths in a requirements file against the current working directory, not the file's location. CLAUDE.md forbids `cd`, so the command tried to install `C:\Users\HP` as a project and failed.
- **How it was caught:** Before committing, Claude Code ran the install from a directory outside the repo and got `does not appear to be a Python project`.
- **Fix:** Removed `-e .` from `requirements.txt`. Added one absolute-path command to the CLAUDE.md Commands section: `python.exe -m pip install -e C:\dev\liftlab-email-experiment\analysis`. Both commands were re-verified from outside the repo, and `import liftlab` succeeded. Committed with the Step 2 scaffold.
- **Lesson / guard added:** Test setup commands from a directory other than the repo root, because a relative path can pass by accident when run from the repo.

**2026-09-23 · Sprint 1 · Unverified explanation of the dataset hash difference**
- **What was produced:** Claude Code's draft of `docs\data-source.md` said the local file's SHA-256 differed from the canonical MineThatData CSV "because the canonical file uses CRLF line endings and the loader re-serialises the data with pandas."
- **What was wrong:** Only half of that was right. Claude Code then compared the files directly and found the loader changes nothing: the local file is byte-identical to the decompressed scikit-uplift mirror. The byte differences are between the mirror and the canonical file: CRLF line endings, and integer-valued `spend` written as `0.0` in the mirror. The first explanation had not been checked.
- **How it was caught:** Before committing, Claude Code checked its own claim. It stripped CR from the canonical file and diffed it against the local file (they still differed on `0` vs `0.0`), then hashed the decompressed mirror (`00a6a868…`, the same as the local file).
- **Fix:** The cross-check is now computed in code (`liftlab.load.cross_check`): mirror byte identity, the canonical file's SHA-256, and parsed-content identity. The doc renders those results, and the prose explanation matches what was observed. Committed with the Step 3 loader.
- **Lesson / guard added:** Any claim in a generated doc about why two artifacts differ must be backed by a check the code runs, not stated from inference.
