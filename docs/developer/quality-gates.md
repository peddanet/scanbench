# Quality gates

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

`tools/check.sh` is the only definition of the gates. The pre-push hook and
the CI call the same script, so a green local run predicts a green CI run.
The six gates and the staged output follow the projects mediatools and
patreon-downloader of the same author.

## The six gates

| Stage | Gate | Tool | Pass condition | Configured in |
|---|---|---|---|---|
| [0] | privacy | `tools/privacy_scan.py` | no deny-list term in tracked files, paths, PDF text, commit messages | local deny list (below) |
| [1] | format | pycodestyle | PEP 8, 100 columns | `tools/check.sh` |
| [2] | lint | pylint + docparams + mccabe | score 10.00/10 for `src`, `tests`, `tools` | `[tool.pylint.*]` |
| [3] | types | mypy | `--strict`, no error | `[tool.mypy]` |
| [4] | security | bandit | no finding (B404, B603 skipped: argument lists, no shell) | `[tool.bandit]` |
| [5] | tests | pytest + pytest-cov + pytest-qt | all pass; branch coverage >= 90 %, precision 2; `ResourceWarning` is an error | `[tool.pytest.ini_options]`, `[tool.coverage.*]` |

GUI tests run with the Qt `offscreen` platform (set in `tests/conftest.py`),
so neither a display nor Xvfb is needed.

## Running

~~~bash
tools/check.sh                 # all gates
tools/check.sh --fast          # skip [5] tests while editing
tools/check.sh --only lint     # one gate
tools/check.sh --full          # complete tool output inline
tools/check.sh --json g.json   # machine-readable summary
~~~

Normal user, inside the activated development venv. The script writes only
below the repository: `.gates/<timestamp>/<n>-<gate>.log` (ignored by git).

## Output

Each gate is a numbered stage with PASS or FAIL and its duration. A failing
gate prints a short summary (for lint: score and the first findings) and the
path of its full log; the remaining gates are shown as skipped. Real output of
a failing run during development of 0.1.0:

~~~text
==== scanbench quality gates  2026-11-11 01:58:27 ============================
-- [0] privacy   privacy_scan.py                  PASS    0.0 s
-- [1] format    pycodestyle, 100 columns         PASS    0.1 s
-- [2] lint      pylint + docparams + mccabe      PASS   12.3 s
-- [3] types     mypy --strict                    FAIL    3.0 s
       tests/unit/test_cli.py:122: error: "append" of "list" does not return a value
       Found 1 error in 1 file (checked 26 source files)
       2 lines in total; full output: .gates/2026-11-11_01-58-27/3-types.log
-- [4] security  skipped (stopped at first failure)
-- [5] tests     skipped (stopped at first failure)
==== RESULT: FAIL at [3] types, 4 stage(s) run, 15.5 s =======================
~~~

In GitHub Actions the full output of each gate is additionally printed inside
a collapsible log group.

## Privacy gate and the deny list

The deny list lives outside the repository, one term per line, case
insensitive, `#` starts a comment. Location, first match wins:

1. `$SCANBENCH_PRIVACY_DENY`
2. `$SCANBENCH_HOME/privacy/deny.txt`
3. `~/.config/scanbench/privacy/deny.txt`

~~~bash
mkdir -p ~/.config/scanbench/privacy
${EDITOR:-nano} ~/.config/scanbench/privacy/deny.txt
~~~

Typical entries: the scanner's IP address, host names, user names, album and
folder names. Prefer specific terms; common words block ordinary code.
Without a list the gate passes neutrally, which is the case in CI. PDF text
is extracted with `pdftotext` (package `poppler-utils`) if installed.

## Pre-push hook

Activate once per clone (normal user, writes `.git/config` only):

~~~bash
git config core.hooksPath .githooks
~~~

The hook runs `tools/check.sh` when a branch is pushed; tag-only pushes and
branch deletions run nothing. `git push --no-verify` bypasses it in an
emergency; the CI still enforces the gates.
