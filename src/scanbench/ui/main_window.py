"""Main window: one tab per use case, update menu, safe release switching."""

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QTabWidget, QVBoxLayout, QWidget

from scanbench.app_info import APP_NAME
from scanbench.ui.switch_banner import SwitchBanner

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
    window becomes idle again. Without tabs (tests, no workbench) the window
    shows placeholders.
    """

    update_requested = Signal()
    """The user chose "Update ..." in the menu."""

    switch_requested = Signal(str)
    """The window is idle and the switch to the given release may happen."""

    cancel_requested = Signal()
    """The user asked to switch now: the running job should be cancelled."""

    def __init__(self, version_text: str, confirm: Confirm = ask_switch,
                 tabs: Sequence[QWidget] = (), header: QWidget | None = None) -> None:
        """Build the widgets.

        Args:
            version_text: Version shown in the status bar.
            confirm: Question used before a switch the user did not start.
            tabs: Widgets for the tabs in ``TAB_TITLES`` order.
            header: Widget above the tabs (scanner selection).
        """
        super().__init__()
        self.resize(960, 640)
        self._confirm = confirm
        self._busy = 0
        # Reports work a restart would lose, e.g. an unconfirmed photo scan.
        self.unsaved: Callable[[], bool] = lambda: False
        self.banner = SwitchBanner()
        self.banner.switch_now.connect(self._switch_now)
        self._version_text = version_text
        self.tabs = QTabWidget()
        pages = list(tabs) or [self._placeholder("No scanner support loaded.")
                               for _ in TAB_TITLES]
        for page, title in zip(pages, TAB_TITLES):
            self.tabs.addTab(page, title)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.banner)
        if header is not None:
            layout.addWidget(header)
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        menu = self.menuBar().addMenu("&scanbench")
        menu.addAction("&Update ...").triggered.connect(self.update_requested)
        menu.addAction("&About scanbench").triggered.connect(self.show_about)
        menu.addAction("&Quit").triggered.connect(self.close)
        self.setWindowTitle(f"scanbench {version_text}")
        # stays visible on the right; status texts appear on the left
        self.version_label = QLabel(f"scanbench {version_text}")
        self.version_label.setToolTip("Version of this window")
        self.statusBar().addPermanentWidget(self.version_label)

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

    def about_text(self) -> str:
        """Return the text of the About box.

        Returns:
            Name, version and purpose as rich text.
        """
        return (f"<b>{APP_NAME} {self._version_text}</b><p>Document and photo-album "
                "scanning for Linux, built on SANE, Ghostscript and CUPS.</p>"
                "<p><a href='https://github.com/peddanet/scanbench'>"
                "github.com/peddanet/scanbench</a></p>")

    def show_about(self) -> None:
        """Show the About box."""
        QMessageBox.about(self, f"About {APP_NAME}", self.about_text())

    def show_message(self, text: str) -> None:
        """Show a status text and carry out a waiting switch if now possible.

        Every tab command ends with a status text, so this is the moment
        when unsaved work may have been saved or discarded.

        Args:
            text: The text.
        """
        self.statusBar().showMessage(text)
        self._try_pending()

    def _try_pending(self) -> None:
        """Carry out a waiting switch when the window is idle."""
        if not self.is_busy() and self.banner.pending is not None:
            pending = self.banner.take()
            if pending is not None:
                self.offer_switch(*pending)

    def busy_reason(self) -> str:
        """Describe why a switch has to wait.

        Returns:
            The end of the sentence "The window switches when ...".
        """
        if self._busy > 0:
            return "the running job is done (or press Switch now)"
        return "the open work is saved or discarded"

    def _switch_now(self) -> None:
        """Cancel the running job and switch as soon as the window is idle."""
        if self.banner.pending is not None:
            self.banner.pending = (self.banner.pending[0], True)
        self.cancel_requested.emit()
        self._try_pending()

    def is_busy(self) -> bool:
        """Whether a job runs or a restart would lose unsaved work.

        Returns:
            True while a job (scan, save, print) runs or work is unsaved.
        """
        return self._busy > 0 or self.unsaved()

    def set_busy(self, busy: bool) -> None:
        """Mark the start or end of a job; carry out a waiting switch when idle.

        Args:
            busy: True when a job starts, False when it ends.
        """
        self._busy = max(0, self._busy + (1 if busy else -1))
        self._try_pending()

    def offer_switch(self, version: str, automatic: bool) -> None:
        """Switch to a newly installed release at the next safe moment.

        Args:
            version: The installed release.
            automatic: True if the user started the update in this window;
                then no question is asked.
        """
        if self.is_busy():
            self.banner.wait_for(version, automatic, self.busy_reason())
            return
        if automatic or self._confirm(self, version):
            self.switch_requested.emit(version)
        else:
            self.statusBar().showMessage(f"scanbench {version} installed; restart to use it")
