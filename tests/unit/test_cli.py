"""Tests for the command line."""

import sys
from pathlib import Path

import pytest
from fakes import FakeShell, failed, ok

import scanbench
from scanbench import cli as cli_module
from scanbench.application.first_publication import FirstPublication
from scanbench.application.update_service import UpdateService
from scanbench.cli import Cli
from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.version_info import VersionInfo


class Recorder:
    """Collects printed lines and GUI starts."""

    def __init__(self) -> None:
        """Start with empty records."""
        self.lines: list[str] = []
        self.gui_calls: list[tuple[str, bool]] = []
        self.answers: list[str] = []

    def out(self, line: str) -> None:
        """Record one printed line.

        Args:
            line: The printed line.
        """
        self.lines.append(line)

    def gui(self, version: str, paths: AppPaths, is_release: bool) -> int:
        """Record a GUI start and report success.

        Args:
            version: Version text passed to the GUI.
            paths: Paths passed to the GUI (not recorded).
            is_release: Whether an installed release runs.

        Returns:
            Always 0.
        """
        del paths
        self.gui_calls.append((version, is_release))
        return 0

    def ask(self, question: str) -> str:
        """Answer a question with the next prepared answer.

        Args:
            question: The question.

        Returns:
            The answer.
        """
        self.lines.append(question)
        return self.answers.pop(0)


def _cli(tmp_path: Path, rec: Recorder) -> Cli:
    """Create a Cli writing below tmp_path."""
    version = VersionInfo(tmp_path / "site-packages" / "scanbench", "1.0.0")
    return Cli(AppPaths({}, tmp_path), version, rec.gui, rec.out, rec.ask)


def test_default_and_gui_command_start_gui(tmp_path: Path) -> None:
    """Without a command and with "gui" the GUI starts.

    Args:
        tmp_path: Temporary directory of the test.
    """
    rec = Recorder()
    cli = _cli(tmp_path, rec)
    assert cli.run([]) == 0
    assert cli.run(["gui"]) == 0
    assert rec.gui_calls == [("1.0.0", True)] * 2


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
    _cli(tmp_path, Recorder()).run(["install-desktop"])  # SCANBENCH_HOME unset in tests
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
    assert [release for _, release in rec.gui_calls] == [False]


def test_update_and_publish_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """update and publish build their workflows and return their status.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Replaces the workflow runs.
    """
    monkeypatch.setattr(UpdateService, "run", lambda self: 3)
    monkeypatch.setattr(FirstPublication, "run", lambda self: 4)
    cli = _cli(tmp_path, Recorder())
    assert cli.run(["update", "--yes", "--clone", str(tmp_path)]) == 3
    assert cli.run(["publish", "--repo", "o/r"]) == 4


def _pending(*versions: str) -> list[PatchArchive]:
    """Create archives for the chooser tests.

    Args:
        *versions: Version texts.

    Returns:
        The archives.
    """
    return [PatchArchive(Version.parse(v), Path(f"scanbench-{v}-patch.tar.gz"), 0)
            for v in versions]


def test_chooser(tmp_path: Path) -> None:
    """--yes takes all, --upto limits, otherwise the user is asked.

    Args:
        tmp_path: Temporary directory of the test.
    """
    rec = Recorder()
    cli = _cli(tmp_path, rec)
    pending = _pending("0.1.1", "0.1.2", "0.1.3")
    choose = cli._choose  # pylint: disable=protected-access
    parse = cli.parser().parse_args
    assert len(choose(parse(["update", "--yes"]))(pending)) == 3
    assert len(choose(parse(["update", "--upto", "0.1.2"]))(pending)) == 2
    rec.answers = ["0.1.1", ""]
    assert len(choose(parse(["update"]))(pending)) == 1
    assert len(choose(parse(["update"]))(pending)) == 3
    assert rec.lines[-1] == "Apply up to version [0.1.3]: "


def test_install_desktop_exec_and_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--exec, SCANBENCH_HOME and SCANBENCH_BIN end up in the Exec key.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the variables.
    """
    monkeypatch.setenv("SCANBENCH_HOME", "/opt/sb.d")
    monkeypatch.setenv("SCANBENCH_BIN", "/opt/bin")
    _cli(tmp_path, Recorder()).run(["install-desktop", "--exec", "/opt/sb.d/venv/bin/scanbench"])
    desktop = next((tmp_path / ".local/share/applications").glob("*.desktop"))
    text = desktop.read_text(encoding="utf-8")
    assert ("Exec=env SCANBENCH_BIN=/opt/bin SCANBENCH_HOME=/opt/sb.d "
            "/opt/sb.d/venv/bin/scanbench\n") in text


def _scanning_cli(tmp_path: Path, rec: Recorder, shell: FakeShell) -> Cli:
    """Create a Cli whose scanner and printer commands use a fake shell.

    Args:
        tmp_path: Temporary directory of the test.
        rec: Recorder of the output.
        shell: Fake shell.

    Returns:
        The Cli.
    """
    cli = _cli(tmp_path, rec)
    cli.shell = shell
    return cli


def test_devices_command(tmp_path: Path) -> None:
    """Scanners are listed with their options; errors and empty lists fail.

    Args:
        tmp_path: Temporary directory of the test.
    """
    options = "    --mode Gray|Color [Gray]\n    --source Flatbed [Flatbed]\n"
    shell = FakeShell(script={("scanimage", "-f"): [ok("a:1|Canon|MX920|multi\n")],
                              ("scanimage", "-d"): [ok(options)]})
    rec = Recorder()
    assert _scanning_cli(tmp_path, rec, shell).run(["devices"]) == 0
    assert rec.lines == ["Canon MX920 (a:1)", "  sources:     Flatbed",
                         "  modes:       Gray, Color", "  resolutions: -"]
    assert _scanning_cli(tmp_path, rec, FakeShell()).run(["devices"]) == 1
    assert "no scanner" in rec.lines[-1]
    broken = FakeShell(script={("scanimage",): [failed("boom")]})
    assert _scanning_cli(tmp_path, rec, broken).run(["devices", "--test"]) == 1
    assert "boom" in rec.lines[-1]


def test_printers_command(tmp_path: Path) -> None:
    """Printers are listed with options; errors and empty lists fail.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shell = FakeShell(script={("lpstat", "-e"): [ok("MX920\n")],
                              ("lpstat", "-d"): [ok("system default destination: MX920")],
                              ("lpoptions",): [ok("InputSlot/Source: *Auto CDTray\n")]})
    rec = Recorder()
    assert _scanning_cli(tmp_path, rec, shell).run(["printers"]) == 0
    assert rec.lines[0] == "MX920  (default)" and "CDTray" in rec.lines[1]
    assert _scanning_cli(tmp_path, rec, FakeShell()).run(["printers"]) == 1
    assert "no printer" in rec.lines[-1]
    broken = FakeShell(script={("lpstat",): [failed("no cupsd")]})
    assert _scanning_cli(tmp_path, rec, broken).run(["printers"]) == 1
    assert "no cupsd" in rec.lines[-1]
