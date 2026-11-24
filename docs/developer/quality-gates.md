# Quality gates

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

`tools/check.sh` is the only definition of the gates. The pre-push hook and
the CI call the same script, so a green local run predicts a green CI run.
The seven gates and the staged output follow the projects mediatools and
patreon-downloader of the same author and the dev-conventions handover v8.

## The seven gates

| Stage | Gate | Tool | Pass condition | Configured in |
|---|---|---|---|---|
| [0] | privacy | `tools/privacy_scan.py` (rules as in mediatools) | no deny-list term (whole words) in tracked files, paths, PDF text, commit messages, tag annotations, identities; every author, committer and tagger uses a no-reply address or is allow-listed | local deny and allow list (below) |
| [1] | shell | shellcheck | no finding in `install.sh`, `tools/*.sh`, `.githooks/pre-push` | per-line `# shellcheck disable=SCxxxx  # <reason>` only |
| [2] | format | pycodestyle | PEP 8, 100 columns | `tools/check.sh` |
| [3] | lint | pylint + docparams + mccabe | score 10.00/10 for `src`, `tests`, `tools` | `[tool.pylint.*]` |
| [4] | types | mypy | `--strict`, no error | `[tool.mypy]` |
| [5] | security | bandit | no finding (B404, B603 skipped: argument lists, no shell) | `[tool.bandit]` |
| [6] | tests | pytest + pytest-cov + pytest-qt | all pass; branch coverage >= 90 %, precision 2; `ResourceWarning` is an error | `[tool.pytest.ini_options]`, `[tool.coverage.*]` |

shellcheck is a system package (`sudo` because apt writes below `/usr`):

~~~bash
sudo apt install shellcheck
~~~

## Tests never touch the real desktop

`tests/conftest.py` isolates every test run before the first test starts:

* Qt renders with the `offscreen` platform (forced, not only a default), so
  neither a display nor Xvfb is needed.
* `WAYLAND_DISPLAY` names a socket that does not exist; `DISPLAY` and
  `DBUS_SESSION_BUS_ADDRESS` are removed. Nothing can reach the running
  desktop or session bus.
* `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`,
  `XDG_CACHE_HOME`, `XDG_DOWNLOAD_DIR` and `XDG_RUNTIME_DIR` point into one
  temporary folder, removed when the run ends. Settings, logs, launcher
  entries and `~/Downloads` of the developer stay untouched.
* The developer's own `SCANBENCH_*` variables are removed.

Every wait for a child process has a time limit: `tests/child_wait.py`
(`finish`) kills a child that does not end in time and fails the test with
the child's last output; `subprocess.run` calls pass `timeout`; Qt waits
(`qtbot.waitSignal`, `waitUntil`) pass `timeout`. `tests/unit/test_isolation.py`
checks the isolation itself.

## Running

~~~bash
tools/check.sh                 # all gates
tools/check.sh --fast          # skip [6] tests while editing
tools/check.sh --only lint     # one gate
tools/check.sh --full          # complete tool output inline
tools/check.sh --json g.json   # machine-readable summary
CHECK_FULL=1 tools/check.sh    # full run even for a known tree
~~~

Normal user. The script activates the project's `.venv` itself if no venv is
active (and says so); instructions therefore do not start with
`source .venv/bin/activate`. It writes only below the repository:
`.gates/<timestamp>/<n>-<gate>.log` (ignored by git) and
`.git/checked-trees`.

## Each tree is checked in full once

After a complete green run (no `--fast`, no `--only`) `check.sh` stores a key
in `.git/checked-trees`: the tree of the working copy (uncommitted and
untracked files included, `.gitignore` honoured), the Python version and a
hash of the installed packages. When the same key comes again, only
`privacy` and `shell` run - the privacy scan also reads commit messages and
tags, which change without the tree - and the script says what it skipped:

~~~text
This tree passed all gates before (4b825dc642cb6eb9a060e54bf8d69288fbee4904).
format, lint, types, security and tests skipped - CHECK_FULL=1 forces them.
~~~

Reason: a release and the pre-push hook call `check.sh` several times for
the same code. `CHECK_FULL=1` forces a full run; CI (`CI=true`) always runs
in full. The last 50 keys are kept. Source: dev-conventions template
`templates/check-cache.sh`.

## Output

Each gate is a numbered stage with PASS or FAIL and its duration. A failing
gate prints a short summary (for lint: score and the first findings) and the
path of its full log; the remaining gates are shown as skipped. Real output of
a failing run during development of 0.1.0 (six gates at that time, before `shell`):

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

## Privacy gate: deny list and allow list

The scan follows the same rules as `tools/privacy_scan.py` of mediatools, so
one set of lists serves both projects. Both lists live outside the
repository - a list of the protected terms would itself reveal what it
protects. One entry per line, `#` starts a comment. Samples with invented
content: `examples/privacy/`.

| List | Location, first match wins | Content |
|---|---|---|
| deny list | `$SCANBENCH_PRIVACY_DENY`; `$XDG_CONFIG_HOME/scanbench/privacy/denylist.txt` (default `~/.config/scanbench/privacy/`); still read with a hint to rename: `$SCANBENCH_HOME/privacy/deny.txt`, `~/.config/scanbench/privacy/deny.txt` | forbidden terms, at least 3 characters: real name, host names, user names, IP addresses, private e-mail addresses, album and folder names |
| allow list | `$SCANBENCH_PRIVACY_ALLOW`; else `allowlist.txt` next to the deny list | allowed phrases in which a term is permitted (the term `level` inside `sea level`); an e-mail address alone on its line is accepted as identity |

Matching rules:

* Case is ignored; a term matches whole words only (`cat` does not match
  `concatenate`). Terms shorter than 3 characters are ignored.
* Allowed phrases are blanked out before the search. A phrase needs a word
  boundary only where it begins or ends with a letter or digit, so
  `top-level` does not cover `stop-level`, while `key=` may be followed by
  anything.
* Identities: every author, committer and tagger of the whole history must
  use a no-reply address (`*@users.noreply.github.com`, `noreply@github.com`,
  `noreply@anthropic.com`) or stand alone on a line of the allow list.
  Findings name the commit or tag and show the address masked
  (`p***@g***.com`). A no-reply address and a name equal to its login are
  not searched for terms; any other name is.
* Binary files are skipped; PDF text is extracted with `pdftotext` (package
  `poppler-utils`), otherwise the PDF is reported as not scanned.

Create both lists from the samples (normal user; `cp -n` never overwrites an
existing list, `chmod 600` makes them readable for you only), then replace
the invented entries by your own:

~~~bash
mkdir -p ~/.config/scanbench/privacy && \
cp -n examples/privacy/denylist.sample.txt ~/.config/scanbench/privacy/denylist.txt && \
cp -n examples/privacy/allowlist.sample.txt ~/.config/scanbench/privacy/allowlist.txt && \
chmod 600 ~/.config/scanbench/privacy/denylist.txt ~/.config/scanbench/privacy/allowlist.txt
~~~

The gate never passes silently: without terms it **fails** with exit status
2. Only in CI (`CI=true`), where no private list exists, it is skipped with a
notice.

## Pre-push hook

Activate once per clone (normal user, writes `.git/config` only):

~~~bash
git config core.hooksPath .githooks
~~~

The hook runs `tools/check.sh` when a branch is pushed; tag-only pushes and
branch deletions run nothing. `git push --no-verify` bypasses it in an
emergency; the CI still enforces the gates.
