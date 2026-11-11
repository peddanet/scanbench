"""GUI tests; run offscreen through pytest-qt."""

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from scanbench import cli as cli_module
from scanbench.app_info import APP_ID, APP_NAME
from scanbench.ui.gui_application import GuiApplication
from scanbench.ui.main_window import TAB_TITLES, MainWindow


def test_main_window_shows_tabs_and_version(qtbot: QtBot) -> None:
    """The window has one tab per use case and the version in the status bar.

    Args:
        qtbot: pytest-qt helper that owns the widgets.
    """
    window = MainWindow("1.0.0")
    qtbot.addWidget(window)
    titles = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert titles == list(TAB_TITLES)
    assert window.statusBar().currentMessage() == "scanbench 1.0.0"


def test_configure_sets_identity(qapp: QApplication) -> None:
    """Name, desktop file name and a non-empty window icon are set.

    Args:
        qapp: The QApplication of the test session.
    """
    GuiApplication.configure(qapp)
    assert qapp.applicationName() == APP_NAME
    assert qapp.desktopFileName() == APP_ID
    assert not qapp.windowIcon().isNull()


@pytest.mark.usefixtures("qapp")
def test_run_shows_window_and_returns_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() reuses the existing application and returns the loop status.

    Args:
        monkeypatch: Replaces attributes for the test.
    """
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    gui = GuiApplication("1.0.0")
    assert gui.run(["scanbench"]) == 0
    assert gui.window is not None and gui.window.isVisible()
    gui.window.close()


@pytest.mark.usefixtures("qapp")
def test_run_gui_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    """The lazy GUI starter of the CLI runs the application.

    Args:
        monkeypatch: Replaces attributes for the test.
    """
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    assert cli_module._run_gui("1.0.0", ["scanbench"]) == 0  # pylint: disable=protected-access
