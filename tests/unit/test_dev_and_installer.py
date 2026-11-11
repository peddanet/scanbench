"""Tests for DevEnvironment, ReleaseInstaller and ReleaseLayout."""

import os
from pathlib import Path

import pytest
from fakes import FakeShell, failed

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.dev_environment import DevEnvironment
from scanbench.infrastructure.release_installer import ReleaseInstaller


class RecordingShells:
    """Factory that hands out FakeShells and remembers them."""

    def __init__(self, gate_status: int = 0) -> None:
        """Start without shells.

        Args:
            gate_status: Exit status of tools/check.sh.
        """
        self.shells: list[FakeShell] = []
        self.gate_status = gate_status

    def __call__(self, cwd: Path, env: dict[str, str] | None = None) -> FakeShell:
        """Create a shell.

        Args:
            cwd: Working directory.
            env: Environment.

        Returns:
            The fake shell.
        """
        result = failed() if self.gate_status else None
        script = {(str(cwd / "tools" / "check.sh"),): [result]} if result else {}
        shell = FakeShell(cwd, script, env)  # type: ignore[arg-type]
        self.shells.append(shell)
        return shell


def test_prepare_creates_venv_once(tmp_path: Path) -> None:
    """The venv is created only if missing; the clone is always reinstalled.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shells = RecordingShells()
    dev = DevEnvironment(tmp_path, shells)  # type: ignore[arg-type]
    dev.prepare()
    assert shells.shells[0].calls[0] == ("python3", "-m", "venv", str(tmp_path / ".venv"))
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    dev.prepare()
    assert shells.shells[1].calls[0][1:] == ("install", "--quiet", "-e", ".[dev]")


def test_gates_use_dev_venv(tmp_path: Path) -> None:
    """The gates run with the dev venv first on PATH; failure raises.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shells = RecordingShells()
    DevEnvironment(tmp_path, shells).gates()  # type: ignore[arg-type]
    env = shells.shells[0].env or {}
    assert env["PATH"].startswith(str(tmp_path / ".venv" / "bin") + os.pathsep)
    with pytest.raises(UpdateError, match="quality gates failed"):
        DevEnvironment(tmp_path, RecordingShells(1)).gates()  # type: ignore[arg-type]


def test_installer_active_version_and_install(tmp_path: Path) -> None:
    """The venv link names the active release; install runs install.sh.

    Args:
        tmp_path: Temporary directory of the test.
    """
    paths = AppPaths({"SCANBENCH_HOME": str(tmp_path / "sb")}, tmp_path)
    shell = FakeShell(tmp_path / "clone")
    installer = ReleaseInstaller(paths, shell)
    assert installer.active_version() is None
    layout = paths.release
    (layout.root / "venvs" / "0.2.0").mkdir(parents=True)
    layout.venv_link.symlink_to("venvs/0.2.0")
    assert installer.active_version() == Version(0, 2, 0)
    assert layout.stable_launcher == layout.root / "venv" / "bin" / "scanbench"
    assert layout.archive_store.name == "releases"
    assert layout.lock_file.name == "update.lock"
    installer.install(Version(0, 2, 0))
    assert shell.calls[-1] == ("bash", str(tmp_path / "clone" / "install.sh"), "v0.2.0")
    layout.venv_link.unlink()
    layout.venv_link.symlink_to("venvs/broken")
    assert installer.active_version() is None


def test_installer_failure(tmp_path: Path) -> None:
    """A failing install.sh raises.

    Args:
        tmp_path: Temporary directory of the test.
    """
    clone = tmp_path / "clone"
    shell = FakeShell(clone, {("bash",): [failed()]})
    with pytest.raises(UpdateError, match="installation of v1.0.0 failed"):
        ReleaseInstaller(AppPaths({}, tmp_path), shell).install(Version(1, 0, 0))
