"""Tests of the progress read from the update output."""

from scanbench.ui.update_progress import UpdateProgress

OUTPUT = """==== scanbench update ====
-- [1] read release state from GitHub
       released: 0.2.4; active here: 0.2.4
       pending: 0.2.5
-- [2] 0.2.5: branch hotfix/0.2.5 from main, apply patches
-- [3] 0.2.5: quality gates (local)
==== scanbench quality gates  2026-11-12 02:11:33 ====
-- [0] privacy   privacy_scan.py                  PASS    0.1 s
-- [1] format    pycodestyle, 100 columns         PASS    0.3 s
-- [2] lint      pylint + docparams + mccabe      PASS    9.5 s"""


def test_steps_gates_and_percent() -> None:
    """Steps, pending archives and gate lines move the progress."""
    progress = UpdateProgress()
    assert progress.percent() == 0 and progress.text() == "Step 0 of 2: starting"
    changed = [progress.feed(line) for line in OUTPUT.splitlines()]
    assert changed.count(True) == 7
    assert progress.total == 7 and progress.step == 3 and progress.gates == 3
    assert progress.text() == "Step 3 of 7: 0.2.5: quality gates (local) - 3 of 6 gates"
    assert progress.percent() == 36
    progress.feed("       pending: none")
    progress.feed("-- [9] install v0.2.5 into a new venv and switch to it")
    assert progress.total == 9 and progress.percent() == 89
