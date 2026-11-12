"""GUI tests of the print dialog, dialog helpers, device bar and workbench."""

import shutil
from pathlib import Path

import pytest
import shiboken6
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QWidget
from pytestqt.qtbot import QtBot

from fakes import FakeShell, failed, ok
from gui_helpers import CUPS_SCRIPT, idle
from scan_fakes import FakeScanner
from scanbench.domain.print_job import PrintJob
from scanbench.domain.scan_error import ScanError
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.ui import dialogs
from scanbench.ui.device_bar import DeviceBar
from scanbench.ui.main_window import MainWindow
from scanbench.ui.print_dialog import PrintDialog
from scanbench.ui.task_runner import TaskRunner, _Job, _Relay
from scanbench.ui.workbench import build_workbench


def test_print_dialog(qtbot: QtBot) -> None:
    """Default printer, important options first, only changes in the job.

    Args:
        qtbot: pytest-qt helper.
    """
    dialog = PrintDialog(CupsClient(FakeShell(script=CUPS_SCRIPT)), "Print", photos=True)
    qtbot.addWidget(dialog)
    assert dialog.printer.currentData() == "MX920"
    assert list(dialog.options.choices) == ["InputSlot", "PageSize"]
    dialog.options.choices["InputSlot"].setCurrentText("CDTray")
    dialog.copies.setValue(2)
    assert dialog.job() == PrintJob("MX920", 2, {"InputSlot": "CDTray", "fit-to-page": ""})
    dialog.printer.setCurrentIndex(1)
    assert dialog.job().printer == "Office"


@pytest.mark.parametrize("script,text", [
    ({("lpstat", "-e"): [ok("")]}, "No printer"),
    ({("lpstat",): [failed("down")]}, "down"),
    ({**CUPS_SCRIPT, ("lpoptions",): [failed("no ppd")]}, "no ppd"),
])
def test_print_dialog_problems(qtbot: QtBot, script: dict[tuple[str, ...], list[object]],
                               text: str) -> None:
    """Missing printers and CUPS errors are shown in the dialog.

    Args:
        qtbot: pytest-qt helper.
        script: CUPS answers.
        text: Expected part of the error text.
    """
    dialog = PrintDialog(CupsClient(FakeShell(script=script)), "x")  # type: ignore[arg-type]
    qtbot.addWidget(dialog)
    assert text in dialog.error.text() and not dialog.options.choices


def test_dialog_helpers(tmp_path: Path, qtbot: QtBot,
                        monkeypatch: pytest.MonkeyPatch) -> None:
    """File, folder and print questions wrap the Qt dialogs.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        monkeypatch: Replaces the modal dialogs.
    """
    widget = QWidget()
    qtbot.addWidget(widget)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: (str(tmp_path / "x"), ""))
    assert dialogs.save_pdf_as(widget, tmp_path) == tmp_path / "x.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: ("", ""))
    assert dialogs.save_pdf_as(widget, tmp_path) is None
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: str(tmp_path))
    assert dialogs.choose_folder(widget, tmp_path) == tmp_path
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: "")
    assert dialogs.choose_folder(widget, tmp_path) is None
    ask = dialogs.print_asker(CupsClient(FakeShell(script=CUPS_SCRIPT)))
    monkeypatch.setattr(PrintDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    job = ask(widget, "t", False)
    assert job is not None and job.printer == "MX920"
    monkeypatch.setattr(PrintDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    assert ask(widget, "t", False) is None


def test_device_bar_without_devices(qtbot: QtBot) -> None:
    """No device and failing discovery are reported.

    Args:
        qtbot: pytest-qt helper.
    """
    scanner = FakeScanner()
    scanner.devices = lambda include_test=False: []  # type: ignore[method-assign]
    runner = TaskRunner()
    device_bar = DeviceBar(scanner, runner)
    qtbot.addWidget(device_bar)
    messages: list[str] = []
    device_bar.message.connect(messages.append)
    device_bar.refresh()
    idle(qtbot, runner)
    assert device_bar.device() is None and device_bar.options() is None

    def broken(include_test: bool = False) -> list[object]:
        """Fail like a missing SANE installation.

        Args:
            include_test: Ignored.

        Raises:
            ScanError: Always.
        """
        raise ScanError(f"no SANE {include_test}")
    scanner.devices = broken  # type: ignore[assignment]
    device_bar.refresh()
    idle(qtbot, runner)
    assert messages[-1] == "no SANE False" and device_bar.refresh_button.isEnabled()


def test_main_window_about_and_unsaved_work(qtbot: QtBot,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
    """About box, and a switch that waits for unsaved work.

    Args:
        qtbot: pytest-qt helper.
        monkeypatch: Replaces the About box.
    """
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "about", lambda _p, _t, text: shown.append(text))
    window = MainWindow("1.2.3", confirm=lambda _w, _v: True, tabs=(QWidget(), QWidget()),
                        header=QWidget())
    qtbot.addWidget(window)
    window.show_about()
    assert "1.2.3" in shown[0]
    requested: list[str] = []
    window.switch_requested.connect(requested.append)
    unsaved = [True]
    window.unsaved = lambda: unsaved[0]
    window.offer_switch("2.0.0", automatic=False)
    window.show_message("still scanning")
    assert not requested
    unsaved[0] = False
    window.show_message("Saved")
    assert requested == ["2.0.0"]


@pytest.mark.skipif(shutil.which("scanimage") is None, reason="sane-utils not installed")
def test_workbench_builds_and_cleans_up(tmp_path: Path, qtbot: QtBot,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    """The factory wires everything; close removes the work files.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        monkeypatch: Enables the test device through the environment.
    """
    monkeypatch.setenv("SCANBENCH_TEST_DEVICE", "1")
    bench = build_workbench(AppPaths({"SCANBENCH_HOME": str(tmp_path)}, tmp_path))
    for widget in (bench.devices, bench.documents, bench.photos):
        qtbot.addWidget(widget)
    work = Path(bench.work.name)
    assert work.parent == tmp_path / "cache"
    bench.devices.refresh()
    idle(qtbot, bench.runner)
    assert bench.devices.combo.findData("test") >= 0
    bench.close()
    assert not work.exists()


def test_job_reports_result_error_and_survives_closed_receiver() -> None:
    """A job reports its result or error; a deleted relay is ignored."""
    relay = _Relay()
    seen: list[object] = []
    relay.done.connect(seen.append)
    relay.failed.connect(seen.append)
    _Job(lambda: 5, relay).run()
    _Job(lambda: 1 / 0, relay).run()
    _Job(lambda: (_ for _ in ()).throw(ScanError()), relay).run()
    assert seen == [5, "division by zero", "ScanError"]
    shiboken6.delete(relay)
    _Job(lambda: 5, relay).run()
