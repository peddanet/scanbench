"""Tests for the command line."""

import sys
from pathlib import Path

import pytest

import scanbench
from scanbench import cli as cli_module
from scanbench.cli import Cli
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.version_info import VersionInfo


class Recorder:
    """Collects printed lines and GUI starts."""

    def __init__(self) -> None:
        """Start with empty records."""
        self.lines: list[str] = []
        self.gui_calls: list[tuple[str, list[str]]] = []

    def out(self, line: str) -> None:
        """Record one printed line.

        Args:
            line: The printed line.
        """
        self.lines.append(line)

    def gui(self, version: str, argv: list[str]) -> int:
        """Record a GUI start and report success.

        Returns:
            Always 0.

        Args:
            version: Version text passed to the GUI.
            argv: Command line passed to the GUI.
        """
        self.gui_calls.append((version, argv))
        return 0


def _cli(tmp_path: Path, rec: Recorder) -> Cli:
    """Create a Cli writing below tmp_path."""
    version = VersionInfo(tmp_path / "site-packages" / "scanbench", "1.0.0")
    return Cli(AppPaths({}, tmp_path), version, rec.gui, rec.out)


def test_default_and_gui_command_start_gui(tmp_path: Path) -> None:
    """Without a command and with "gui" the GUI starts.

    Args:
        tmp_path: Temporary directory of the test.
    """
    rec = Recorder()
    cli = _cli(tmp_path, rec)
    assert cli.run([]) == 0
    assert cli.run(["gui"]) == 0
    assert rec.gui_calls == [("1.0.0", ["scanbench"])] * 2


def test_doctor_prints_report(tmp_path: Path) -> None:
    """The doctor command prints the report and returns its status.

    Args:
        tmp_path: Temporary directory of the test.
    """
    rec = Recorder()
    status = _cli(tmp_path, rec).run(["doctor"])
    assert status in (0, 1)
    assert rec.lines[0] == "scanbench 1.0.0"


def test_install_and_uninstall_desktop(tmp_path: Path) -> None:
    """Desktop commands report the touched files.

    Args:
        tmp_path: Temporary directory of the test.
    """
    rec = Recorder()
    cli = _cli(tmp_path, rec)
    assert cli.run(["install-desktop"]) == 0
    assert cli.run(["uninstall-desktop"]) == 0
    assert [line.split(":")[0] for line in rec.lines] == ["written"] * 2 + ["removed"] * 2


def test_desktop_entry_points_into_the_venv(tmp_path: Path) -> None:
    """The Exec key names the launcher of the active venv, not the system Python.

    Args:
        tmp_path: Temporary directory of the test.
    """
    _cli(tmp_path, Recorder()).run(["install-desktop"])
    desktop = next((tmp_path / ".local/share/applications").glob("*.desktop"))
    assert f"Exec={Path(sys.prefix) / 'bin' / 'scanbench'}\n" in desktop.read_text(encoding="utf-8")


def test_version_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--version prints the version text and exits.

    Args:
        tmp_path: Temporary directory of the test.
        capsys: Captures standard output.
    """
    with pytest.raises(SystemExit):
        _cli(tmp_path, Recorder()).run(["--version"])
    assert capsys.readouterr().out == "scanbench 1.0.0\n"


def test_main_wires_real_objects(monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    """main() builds the real collaborators; the source tree is marked.

    Args:
        monkeypatch: Replaces attributes for the test.
        capsys: Captures standard output.
    """
    monkeypatch.setattr(sys, "argv", ["scanbench", "doctor"])
    assert cli_module.main() in (0, 1)
    first = capsys.readouterr().out.splitlines()[0]
    assert first.startswith(f"scanbench {scanbench.__version__}")


def test_main_starts_gui(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() with no arguments hands over to the GUI runner.

    Args:
        monkeypatch: Replaces attributes for the test.
    """
    rec = Recorder()
    monkeypatch.setattr(cli_module, "_run_gui", rec.gui)
    assert cli_module.main([]) == 0
    assert [argv for _, argv in rec.gui_calls] == [["scanbench"]]
