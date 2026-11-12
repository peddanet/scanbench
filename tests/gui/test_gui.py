"""GUI tests; run offscreen through pytest-qt."""

import shutil
import sys
from pathlib import Path

import pytest
from scan_fakes import OPTIONS, page, write_png
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from pytestqt.qtbot import QtBot

from scanbench import __version__
from scanbench import cli as cli_module
from scanbench.app_info import APP_ID, APP_NAME
from scanbench.domain.version import Version
from scanbench.application.document_session import Page
from scanbench.application.photo_session import PhotoScan
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.device_info import DeviceInfo
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.scanimage_backend import ScanimageBackend
from scanbench.ui import main_window as main_window_module
from scanbench.ui.gui_application import GuiApplication
from scanbench.ui.main_window import TAB_TITLES, MainWindow
from scanbench.ui.release_watcher import ReleaseWatcher
from scanbench.ui.update_dialog import UpdateDialog

_RUNNING = Version.parse(__version__)
NEWER = Version(_RUNNING.major, _RUNNING.minor, _RUNNING.patch + 1)


def _install(paths: AppPaths, version: Version) -> None:
    """Pretend that install.sh activated a release.

    Args:
        paths: Paths of the installation.
        version: Release to activate.
    """
    layout = paths.release
    (layout.root / "venvs" / str(version) / "bin").mkdir(parents=True, exist_ok=True)
    if layout.venv_link.is_symlink():
        layout.venv_link.unlink()
    layout.venv_link.symlink_to(f"venvs/{version}")


def test_main_window_shows_tabs_and_version(qtbot: QtBot) -> None:
    """The window has one tab per use case and the version in the status bar.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
    """
    window = MainWindow("1.0.0")
    qtbot.addWidget(window)
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert titles == list(TAB_TITLES)
    assert window.version_label.text() == "scanbench 1.0.0"
    assert window.windowTitle() == "scanbench 1.0.0"


def test_switch_waits_while_busy(qtbot: QtBot) -> None:
    """A switch offered during a job happens when the job ends.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
    """
    window = MainWindow("1.0.0", confirm=lambda _w, _v: False)
    qtbot.addWidget(window)
    requested: list[str] = []
    window.switch_requested.connect(requested.append)
    window.set_busy(True)
    window.offer_switch("2.0.0", automatic=True)
    assert not requested and not window.banner.isHidden()
    assert "when the running job is done" in window.banner.label.text()
    window.set_busy(False)
    assert requested == ["2.0.0"] and window.banner.isHidden()
    window.offer_switch("3.0.0", automatic=False)
    assert requested == ["2.0.0"]
    assert "restart to use it" in window.statusBar().currentMessage()


def test_switch_now_cancels_the_job(qtbot: QtBot) -> None:
    """Switch now asks to cancel the job and switches without a question when idle.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
    """
    window = MainWindow("1.0.0", confirm=lambda _w, _v: False)
    qtbot.addWidget(window)
    requested: list[str] = []
    cancels: list[bool] = []
    window.switch_requested.connect(requested.append)
    window.cancel_requested.connect(lambda: cancels.append(True))
    window.set_busy(True)
    window.offer_switch("2.0.0", automatic=False)
    window.banner.button.click()
    assert cancels == [True] and not requested
    window.set_busy(False)
    assert requested == ["2.0.0"]
    window.unsaved = lambda: True
    window.offer_switch("3.0.0", automatic=True)
    assert "saved or discarded" in window.banner.label.text()
    window.banner.take()
    window.banner.button.click()                    # nothing waits: only a cancel request
    assert len(cancels) == 2


def test_ask_switch_uses_message_box(monkeypatch: pytest.MonkeyPatch, qtbot: QtBot) -> None:
    """The default confirmation is a Yes/No question.

    Args:
        monkeypatch: Replaces the message box.
        qtbot: pytest-qt helper that owns the widgets.
    """
    yes = QMessageBox.StandardButton.Yes
    monkeypatch.setattr(QMessageBox, "question", lambda *a: yes)
    widget = QWidget()
    qtbot.addWidget(widget)
    assert main_window_module.ask_switch(widget, "2.0.0")


def test_watcher_reports_newer_release_once(tmp_path: Path, qtbot: QtBot) -> None:
    """Only a newer release is reported, and only once.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper that owns the widgets.
    """
    paths = AppPaths({"SCANBENCH_HOME": str(tmp_path)}, tmp_path)
    watcher = ReleaseWatcher(paths.release.venv_link, Version(1, 0, 0), interval_ms=60_000)
    seen: list[str] = []
    watcher.new_release.connect(seen.append)
    watcher.check()
    _install(paths, Version(1, 0, 0))
    watcher.check()
    _install(paths, Version(1, 1, 0))
    with qtbot.waitSignal(watcher.new_release, timeout=1000):
        watcher.check()
    watcher.check()
    assert seen == ["1.1.0"]
    paths.release.venv_link.unlink()
    paths.release.venv_link.symlink_to("venvs/odd")
    assert watcher.installed() is None


@pytest.mark.parametrize("command,status", [("echo stage output", 0), ("exit 3", 3)])
def test_update_dialog_streams_output(qtbot: QtBot, command: str, status: int) -> None:
    """The dialog shows the child's output and its result.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
        command: Shell command standing in for the update.
        status: Expected exit status.
    """
    dialog = UpdateDialog(shutil.which("sh") or "/bin/sh", ["-c", command])
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.process.finished, timeout=5000):
        dialog.start()
    assert dialog.buttons.isEnabled()
    if status == 0:
        assert "stage output" in dialog.log.toPlainText()
        assert dialog.status.text().startswith("DONE")
    else:
        assert "exit status 3" in dialog.status.text()


def test_configure_sets_identity(qapp: QApplication) -> None:
    """Name, desktop file name and a non-empty window icon are set.

    Args:
        qapp: The QApplication of the test session.
    """
    GuiApplication.configure(qapp)
    assert qapp.applicationName() == APP_NAME
    assert qapp.desktopFileName() == APP_ID
    assert not qapp.windowIcon().isNull()


def test_release_window_switches_after_update(tmp_path: Path, qtbot: QtBot,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    """A release window watches, offers switches and restarts into the new release.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: Waits for the initial scanner search.
        monkeypatch: Replaces process start, quit and the dialog start.
    """
    paths = AppPaths({"SCANBENCH_HOME": str(tmp_path)}, tmp_path)
    started: list[str] = []

    def start_detached(program: str, args: list[str]) -> tuple[bool, int]:
        """Record a detached start instead of starting a process.

        Args:
            program: Program to start.
            args: Its arguments.

        Returns:
            Success and a fake process id.
        """
        del args
        started.append(program)
        return True, 0

    monkeypatch.setattr(QProcess, "startDetached", start_detached)
    monkeypatch.setattr(QApplication, "quit", lambda: None)
    monkeypatch.setattr(UpdateDialog, "start", lambda self: None)
    gui = GuiApplication("1.0.0", paths, is_release=True)
    window = gui.show()
    assert gui.workbench is not None
    runner = gui.workbench.runner
    # The search may reach real network scanners on a developer machine.
    qtbot.waitUntil(lambda: not runner.busy() and not window.is_busy(), timeout=60000)
    window._confirm = lambda _w, _v: True  # pylint: disable=protected-access
    assert gui.restart("x") is False
    dialog = gui.open_update()
    assert dialog.process.state() == QProcess.ProcessState.NotRunning
    _install(paths, NEWER)
    (paths.release.stable_launcher).write_text("", encoding="utf-8")
    gui._on_new_release(str(NEWER))  # pylint: disable=protected-access
    assert started == [str(paths.release.stable_launcher)]
    dialog.succeeded.emit()
    assert len(started) == 2
    window.close()
    gui.close()


def _switch_with_open_work(paths: AppPaths, qtbot: QtBot) -> None:
    """Open a window with work in both tabs and switch to the next release.

    The first start fails (the handover is removed), the second succeeds.

    Args:
        paths: Installation directories.
        qtbot: Waits for the scanner search.
    """
    paths.release.stable_launcher.parent.mkdir(parents=True, exist_ok=True)
    paths.release.stable_launcher.write_text("", encoding="utf-8")
    old = GuiApplication("1.0.0", paths, is_release=False)
    window = old.show()
    bench = old.workbench
    assert bench is not None
    qtbot.waitUntil(lambda: not bench.runner.busy(), timeout=60000)
    scan_file = write_png(Path(bench.work.name) / "photos" / "scan.png", page(200), 100)
    bench.photos.resume(PhotoScan(scan_file, 100, [CropRegion(20, 20, 30, 30, 1.5, 1)]))
    page_file = write_png(Path(bench.work.name) / "documents" / "p.png", page(90), 100)
    bench.documents.resume([Page(page_file, 100, 2, 1)])
    window.tabs.setCurrentIndex(1)
    bench.devices.combo.setCurrentIndex(1)                  # fake:2
    qtbot.waitUntil(lambda: not bench.runner.busy(), timeout=60000)
    assert old.restart("2.0.0") is False and not old.handover().directory.exists()
    assert old.restart("2.0.0") is True and old.handover().directory.exists()
    window.close()
    old.close()


def test_switch_hands_over_the_open_work(tmp_path: Path, qtbot: QtBot,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    """The next window continues with tab, waiting photo scan and document pages.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: Waits for the scanner searches.
        monkeypatch: Replaces process start and quit.
    """
    paths = AppPaths({"SCANBENCH_HOME": str(tmp_path)}, tmp_path)
    results = [False, True]
    monkeypatch.setattr(QProcess, "startDetached", lambda _p, _a: (results.pop(0), 0))
    monkeypatch.setattr(QApplication, "quit", lambda: None)
    # independent of the scanners of the machine running the tests
    scanners = [DeviceInfo("fake:1", "Fake", "One", "flatbed scanner"),
                DeviceInfo("fake:2", "Fake", "Two", "flatbed scanner")]
    monkeypatch.setattr(ScanimageBackend, "devices", lambda _self, _test=False: scanners)
    monkeypatch.setattr(ScanimageBackend, "options", lambda _self, _device: OPTIONS)
    _switch_with_open_work(paths, qtbot)
    new = GuiApplication("2.0.0", paths, is_release=False)
    new_window = new.show()
    assert new.workbench is not None
    qtbot.waitUntil(lambda: not new.workbench.runner.busy(), timeout=60000)   # type: ignore
    assert new_window.tabs.currentIndex() == 1
    assert new.workbench.devices.device() == "fake:2"
    taken = new.workbench.photos.pending()
    assert taken is not None and taken.regions == [CropRegion(20, 20, 30, 30, 1.5, 1)]
    assert taken.path.exists() and taken.path.parent.parent == Path(new.workbench.work.name)
    pages = new.workbench.documents.scanned_pages()
    assert [(p.quarter_turns, p.batch) for p in pages] == [(2, 1)]
    assert not new.handover().directory.exists()
    new_window.close()
    new.close()


@pytest.mark.usefixtures("qapp")
def test_run_shows_window_and_returns_status(tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
    """run() reuses the existing application and returns the loop status.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Replaces attributes for the test.
    """
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    gui = GuiApplication("1.0.0", AppPaths({}, tmp_path), is_release=False)
    assert gui.run(["scanbench"]) == 0
    assert gui.window is not None and gui.window.isVisible() and gui.watcher is None
    assert gui.workbench is None   # closed by run()
    gui.window.close()


@pytest.mark.usefixtures("qapp")
def test_run_gui_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The lazy GUI starter of the CLI runs the application.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Replaces attributes for the test.
    """
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    paths = AppPaths({}, tmp_path)
    assert cli_module._run_gui("1.0.0", paths, False) == 0  # pylint: disable=protected-access


def test_update_dialog_keeps_the_line_order(qtbot: QtBot) -> None:
    """A Python child's own lines arrive before the output of its children.

    0.2.x showed the gate output at once and the update steps only at the end,
    because Python buffers a pipe in blocks.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
    """
    code = ("import subprocess; print('-- [1] step'); "
            "subprocess.run(['echo', '== gate'], check=True); print('-- [2] step')")
    dialog = UpdateDialog(sys.executable, ["-c", code])
    qtbot.addWidget(dialog)
    assert dialog.process.processEnvironment().value("PYTHONUNBUFFERED") == "1"
    with qtbot.waitSignal(dialog.process.finished, timeout=5000):
        dialog.start()
    assert dialog.log.toPlainText().splitlines()[1:] == ["-- [1] step", "== gate", "-- [2] step"]
