"""Tests for Shell, UpdateLock, CommandResult and Progress."""

from pathlib import Path

import pytest

from scanbench.application.progress import Progress
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell
from scanbench.infrastructure.update_lock import UpdateLock


def test_run_captures_and_checks(tmp_path: Path) -> None:
    """Output is captured; a failure raises with the command in the message.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shell = Shell(tmp_path)
    assert shell.run("echo", "hi").stdout == "hi\n"
    assert shell.run("cat", stdin="data").stdout == "data"
    assert not shell.run("false", check=False).ok
    with pytest.raises(UpdateError, match="'false' failed"):
        shell.run("false")


def test_missing_program(tmp_path: Path) -> None:
    """An unknown program is reported before anything runs.

    Args:
        tmp_path: Temporary directory of the test.
    """
    with pytest.raises(UpdateError, match="not found on PATH"):
        Shell(tmp_path).run("scanbench-no-such-program")


def test_read_retries_then_fails(tmp_path: Path) -> None:
    """Reading calls are retried with pauses and fail after the last attempt.

    Args:
        tmp_path: Temporary directory of the test.
    """
    pauses: list[float] = []
    shell = Shell(tmp_path, sleep=pauses.append)
    with pytest.raises(UpdateError, match="failed 3 times"):
        shell.read("false", attempts=3, delay=2.0)
    assert pauses == [2.0, 2.0]
    assert shell.read("true").ok


def test_live_returns_status(tmp_path: Path) -> None:
    """Live commands return their exit status.

    Args:
        tmp_path: Temporary directory of the test.
    """
    assert Shell(tmp_path).live("true") == 0
    assert Shell(tmp_path).live("false") == 1


def test_lock_is_exclusive(tmp_path: Path) -> None:
    """A second update cannot take the lock while the first holds it.

    Args:
        tmp_path: Temporary directory of the test.
    """
    path = tmp_path / "sub" / "update.lock"
    with UpdateLock(path):
        with pytest.raises(UpdateError, match="another update"):
            with UpdateLock(path):
                pass
    with UpdateLock(path):
        pass


def test_progress_numbers_steps_and_summarises() -> None:
    """Steps are numbered; the summary lists CI runs or a placeholder."""
    lines: list[str] = []
    progress = Progress(lines.append)
    progress.summary("EMPTY")
    assert any("no CI run" in line for line in lines)
    progress.step("first")
    progress.step("second")
    progress.ci("CI 1/3", "pull request", "https://example.org/1")
    progress.summary("DONE")
    assert "-- [2] second" in lines
    assert lines[-1].startswith("==== DONE ")


def test_missing_working_directory(tmp_path: Path) -> None:
    """A missing working directory is reported as UpdateError, not as a traceback.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shell = Shell(tmp_path / "missing")
    with pytest.raises(UpdateError, match="could not start"):
        shell.run("true")
    with pytest.raises(UpdateError, match="could not start"):
        shell.live("true")
