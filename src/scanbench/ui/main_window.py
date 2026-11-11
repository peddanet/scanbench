"""Main window: one tab per use case, filled in later milestones."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QWidget

TAB_TITLES = ("Documents", "Photo album")
"""Titles of the use-case tabs, in display order."""


class MainWindow(QMainWindow):
    """Top-level window with a tab per use case and a status bar.

    The tabs are placeholders in milestone M0; document scanning arrives in
    M2 and the photo album in M3 (see docs/concept).
    """

    def __init__(self, version_text: str) -> None:
        """Build the widgets.

        Args:
            version_text: Version shown in the status bar.
        """
        super().__init__()
        self.setWindowTitle("scanbench")
        self.resize(960, 640)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._placeholder("Document scanning arrives in milestone M2."),
                         TAB_TITLES[0])
        self.tabs.addTab(self._placeholder("Photo-album scanning arrives in milestone M3."),
                         TAB_TITLES[1])
        self.setCentralWidget(self.tabs)
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
