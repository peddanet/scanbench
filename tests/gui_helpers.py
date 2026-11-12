"""Helpers for the GUI tests of the scanning tabs."""

from pathlib import Path

from PySide6.QtWidgets import QMenu, QWidget
from pytestqt.qtbot import QtBot

from fakes import FakeShell, ok
from scan_fakes import FakeScanner
from scanbench.domain.print_job import PrintJob
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.ui.device_bar import DeviceBar
from scanbench.ui.dialogs import Dialogs
from scanbench.ui.progress_panel import ProgressPanel
from scanbench.ui.tab_context import TabContext
from scanbench.ui.task_runner import TaskRunner

CUPS_SCRIPT = {
    ("lpstat", "-e"): [ok("MX920\nOffice\n")],
    ("lpstat", "-d"): [ok("system default destination: MX920\n")],
    ("lpoptions",): [ok("PageSize/Media Size: *A4 4x6.Borderless Letter 5x7\n"
                        "InputSlot/Paper Source: *Auto PhotoTray CDTray\n")],
    ("lp",): [ok("request id is MX920-3 (1 file(s))\n")],
}
"""CUPS with two printers; the MX920 is the default and has a photo tray."""


class Answers:
    """Modal dialogs that return prepared answers and record the questions."""

    def __init__(self, job: PrintJob | None = None, path: Path | None = None) -> None:
        """Store the answers.

        Args:
            job: Answer of the print dialog.
            path: Answer of the file and folder dialogs.
        """
        self.job = job
        self.path = path
        self.questions: list[str] = []

    def ask_print(self, parent: QWidget, title: str, photos: bool) -> PrintJob | None:
        """Answer the print question.

        Args:
            parent: Ignored.
            title: Recorded.
            photos: Ignored.

        Returns:
            The prepared job.
        """
        del parent, photos
        self.questions.append(title)
        return self.job

    def ask_path(self, parent: QWidget, start: Path) -> Path | None:
        """Answer a file or folder question.

        Args:
            parent: Ignored.
            start: Recorded.

        Returns:
            The prepared path.
        """
        del parent
        self.questions.append(str(start))
        return self.path

    def dialogs(self) -> Dialogs:
        """Return the dialogs bundle.

        Returns:
            Dialogs answering from this object.
        """
        return Dialogs(self.ask_print, self.ask_path, self.ask_path)


def idle(qtbot: QtBot, runner: TaskRunner) -> None:
    """Wait until all background jobs are done (twice: jobs may start jobs).

    Args:
        qtbot: pytest-qt helper.
        runner: The runner.
    """
    for _ in range(2):
        qtbot.waitUntil(lambda: not runner.busy(), timeout=60000)


def context(qtbot: QtBot, scanner: FakeScanner, answers: Answers) -> TabContext:
    """Create a tab context with the fake device already selected.

    Args:
        qtbot: pytest-qt helper.
        scanner: Fake scanner.
        answers: Dialog answers.

    Returns:
        The context; CUPS answers from CUPS_SCRIPT.
    """
    runner = TaskRunner()
    device_bar = DeviceBar(scanner, runner)
    qtbot.addWidget(device_bar)
    device_bar.refresh()
    idle(qtbot, runner)
    return TabContext(device_bar, runner, CupsClient(FakeShell(script=CUPS_SCRIPT)),
                      answers.dialogs(), ProgressPanel())


def trigger(widget: QWidget, text: str) -> None:
    """Trigger an action of the newest context menu below a widget.

    Args:
        widget: Owner of the menu.
        text: Action text (also searched in sub-menus).

    Raises:
        AssertionError: If no menu has the action.
    """
    for menu in reversed(widget.findChildren(QMenu)):
        for action in menu.actions():
            if action.text() == text:
                action.trigger()
                return
    raise AssertionError(f"no action {text!r}")
