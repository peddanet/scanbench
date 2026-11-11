"""Main window: one tab per use case, update menu, safe release switching."""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QTabWidget, QWidget

TAB_TITLES = ("Documents", "Photo album")
"""Titles of the use-case tabs, in display order."""

Confirm = Callable[[QWidget, str], bool]
"""Asks the user whether to switch to the given release now."""


def ask_switch(parent: QWidget, version: str) -> bool:
    """Ask with a message box whether to restart into a new release.

    Args:
        parent: Parent widget of the message box.
        version: Newly installed release.

    Returns:
        True if the user agrees.
    """
    answer = QMessageBox.question(
        parent, "scanbench", f"scanbench {version} is installed. Switch to it now?")
    return answer == QMessageBox.StandardButton.Yes


class MainWindow(QMainWindow):
    """Top-level window with a tab per use case, menu and status bar.

    Release switching happens only at a safe moment: while a job runs
    (``set_busy(True)``), an offered switch waits and is carried out when the
    window becomes idle again. The tabs are placeholders until milestones
    M2 (documents) and M3 (photo album).
    """

    update_requested = Signal()
    """The user chose "Update ..." in the menu."""

    switch_requested = Signal(str)
    """The window is idle and the switch to the given release may happen."""

    def __init__(self, version_text: str, confirm: Confirm = ask_switch) -> None:
        """Build the widgets.

        Args:
            version_text: Version shown in the status bar.
            confirm: Question used before a switch the user did not start.
        """
        super().__init__()
        self.setWindowTitle("scanbench")
        self.resize(960, 640)
        self._confirm = confirm
        self._busy = 0
        self._pending: tuple[str, bool] | None = None
        self.tabs = QTabWidget()
        self.tabs.addTab(self._placeholder("Document scanning arrives in milestone M2."),
                         TAB_TITLES[0])
        self.tabs.addTab(self._placeholder("Photo-album scanning arrives in milestone M3."),
                         TAB_TITLES[1])
        self.setCentralWidget(self.tabs)
        menu = self.menuBar().addMenu("&scanbench")
        self.update_action = menu.addAction("&Update ...")
        self.update_action.triggered.connect(self.update_requested)
        menu.addAction("&Quit").triggered.connect(self.close)
        self.statusBar().showMessage(f"scanbench {version_text}")

    @staticmethod
    def _placeholder(text: str) -> QWidget:
        """Create a centred label for a tab that has no content yet.

        Args:
            text: Message to show.

        Returns:
            The label widget.
        """
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def is_busy(self) -> bool:
        """Whether a job (scan, save, export) is running.

        Returns:
            True while at least one job runs.
        """
        return self._busy > 0

    def set_busy(self, busy: bool) -> None:
        """Mark the start or end of a job; carry out a waiting switch when idle.

        Args:
            busy: True when a job starts, False when it ends.
        """
        self._busy = max(0, self._busy + (1 if busy else -1))
        if not self.is_busy() and self._pending is not None:
            version, automatic = self._pending
            self._pending = None
            self.offer_switch(version, automatic)

    def offer_switch(self, version: str, automatic: bool) -> None:
        """Switch to a newly installed release at the next safe moment.

        Args:
            version: The installed release.
            automatic: True if the user started the update in this window;
                then no question is asked.
        """
        if self.is_busy():
            self._pending = (version, automatic)
            self.statusBar().showMessage(f"scanbench {version} installed; switching "
                                         "after the current job")
            return
        if automatic or self._confirm(self, version):
            self.switch_requested.emit(version)
        else:
            self.statusBar().showMessage(f"scanbench {version} installed; restart to use it")
