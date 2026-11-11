"""Page thumbnails with a large preview and page commands."""

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QTransform
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QWidget

from scanbench.application.document_session import DocumentSession, Page

THUMB = 160
"""Edge length of the page thumbnails in pixels."""

EMPTY_TEXT = "Scanned pages appear here."
"""Preview text while there is no page."""


def page_pixmap(page: Page, size: int) -> QPixmap:
    """Load a page scaled and turned for display.

    Args:
        page: The page.
        size: Maximum edge length.

    Returns:
        The pixmap (null if the file cannot be read).
    """
    pixmap = QPixmap(str(page.path))
    if pixmap.isNull():
        return pixmap
    pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    return pixmap.transformed(QTransform().rotate(90 * page.quarter_turns))


class PageList(QWidget):
    """Show the pages of a document session and edit their order and rotation.

    The session is the single source of truth: every command changes the
    session and the list is redrawn from it.
    """

    changed = Signal()
    """The pages or the selection changed."""

    def __init__(self, session: DocumentSession) -> None:
        """Build list and preview.

        Args:
            session: Pages of the document.
        """
        super().__init__()
        self._session = session
        self.dirty = False      # pages changed since the last save
        self.list = QListWidget()
        self.list.setIconSize(QSize(THUMB, THUMB))
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview = QLabel(EMPTY_TEXT)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumWidth(360)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list, 1)
        layout.addWidget(self.preview, 2)
        self.list.currentRowChanged.connect(self._show_preview)
        self.list.customContextMenuRequested.connect(self.context_menu)

    def row(self) -> int:
        """Return the selected row.

        Returns:
            Row index, -1 if none.
        """
        return self.list.currentRow()

    def redraw(self, current: int = -1, edited: bool = True) -> None:
        """Rebuild the list from the session.

        Args:
            current: Row to select afterwards.
            edited: Whether the pages changed (marks the document unsaved).
        """
        if edited:
            self.dirty = bool(self._session.pages)
        self.list.blockSignals(True)
        self.list.clear()
        for number, page in enumerate(self._session.pages, start=1):
            self.list.addItem(QListWidgetItem(QIcon(page_pixmap(page, THUMB)), f"Page {number}"))
        self.list.blockSignals(False)
        self.list.setCurrentRow(min(current, self.list.count() - 1))
        self._show_preview(self.list.currentRow())

    def _show_preview(self, row: int) -> None:
        """Show the selected page large.

        Args:
            row: Selected row, -1 for none.
        """
        if 0 <= row < len(self._session.pages):
            size = max(200, min(self.preview.width(), self.preview.height()))
            self.preview.setPixmap(page_pixmap(self._session.pages[row], size))
        else:
            self.preview.clear()
            self.preview.setText(EMPTY_TEXT)
        self.changed.emit()

    def rotate(self, steps: int) -> None:
        """Turn the selected page.

        Args:
            steps: Quarter turns, positive clockwise.
        """
        row = self.row()
        if row >= 0:
            self._session.rotate(row, steps)
            self.redraw(row)

    def move_page(self, delta: int) -> None:
        """Move the selected page.

        Args:
            delta: -1 up, +1 down.
        """
        row = self.row()
        if row >= 0:
            self.redraw(self._session.move(row, delta))

    def delete(self) -> None:
        """Delete the selected page."""
        row = self.row()
        if row >= 0:
            self._session.remove(row)
            self.redraw(row)

    def context_menu(self, position: QPoint) -> QMenu | None:
        """Offer page commands at the mouse position.

        Args:
            position: Position in list coordinates.

        Returns:
            The shown menu, or None without selection.
        """
        if self.row() < 0:
            return None
        menu = QMenu(self)
        menu.addAction("Rotate right (90°)").triggered.connect(lambda: self.rotate(1))
        menu.addAction("Rotate left (90°)").triggered.connect(lambda: self.rotate(-1))
        menu.addAction("Upside down (180°)").triggered.connect(lambda: self.rotate(2))
        menu.addSeparator()
        menu.addAction("Delete page").triggered.connect(self.delete)
        menu.popup(self.list.viewport().mapToGlobal(position))
        return menu
