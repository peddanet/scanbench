"""A tool bar whose buttons wrap into further rows when the window is narrow."""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFrame, QLayout, QLayoutItem, QToolButton, QWidget

SPACING = 4
"""Gap between buttons in pixels."""


class FlowLayout(QLayout):
    """Lays out widgets left to right and starts a new row when the width ends.

    Unlike ``QToolBar`` nothing is hidden behind an overflow arrow.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the empty layout.

        Args:
            parent: Widget the layout belongs to.
        """
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 (Qt API)
        """Append an item (called by ``addWidget``).

        Args:
            item: The item.
        """
        self._items.append(item)

    def count(self) -> int:
        """Return the number of items.

        Returns:
            The count.
        """
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 (Qt API)
        """Return an item.

        Args:
            index: Position.

        Returns:
            The item, or None outside the range.
        """
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 (Qt API)
        """Remove and return an item.

        Args:
            index: Position.

        Returns:
            The item, or None outside the range.
        """
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def hasHeightForWidth(self) -> bool:  # noqa: N802 (Qt API)
        """The height depends on the width (number of rows).

        Returns:
            True.
        """
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 (Qt API)
        """Return the height needed at a width.

        Args:
            width: Available width.

        Returns:
            Height in pixels.
        """
        return self._arrange(QRect(0, 0, width, 0), move=False)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802 (Qt API)
        """Place the items inside a rectangle.

        Args:
            rect: Available area.
        """
        super().setGeometry(rect)
        self._arrange(rect, move=True)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        """Return the preferred size: all items in one row.

        Returns:
            The size.
        """
        width = sum(i.sizeHint().width() + SPACING for i in self._items)
        height = max((i.sizeHint().height() for i in self._items), default=0)
        return QSize(width, height)

    def minimumSize(self) -> QSize:  # noqa: N802 (Qt API)
        """Return the smallest size: the widest item.

        Returns:
            The size.
        """
        width = max((i.minimumSize().width() for i in self._items), default=0)
        height = max((i.minimumSize().height() for i in self._items), default=0)
        return QSize(width, height)

    def _arrange(self, rect: QRect, move: bool) -> int:
        """Compute (and optionally apply) the positions row by row.

        Args:
            rect: Available area.
            move: Apply the geometry to the items.

        Returns:
            Total height of all rows.
        """
        x, y, row_height = rect.x(), rect.y(), 0
        for item in self._items:
            size = item.sizeHint()
            if x + size.width() > rect.right() + 1 and x > rect.x():
                x, y, row_height = rect.x(), y + row_height + SPACING, 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), size))
            x += size.width() + SPACING
            row_height = max(row_height, size.height())
        return y + row_height - rect.y()


class FlowBar(QWidget):
    """Tool buttons for actions in a wrapping layout (replacement for ``QToolBar``)."""

    def __init__(self) -> None:
        """Create the empty bar."""
        super().__init__()
        self.flow = FlowLayout(self)

    def addAction(self, action: QAction) -> None:  # type: ignore[override]  # noqa: N802
        """Add a button for an action.

        Args:
            action: The action; text, tooltip, state and checkability are shown.
        """
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setAutoRaise(False)          # visible as a button, not as a label
        self.flow.addWidget(button)

    # Qt naming, like QToolBar.addSeparator
    def addSeparator(self) -> None:  # noqa: N802  # pylint: disable=invalid-name
        """Add a thin vertical line between groups of buttons."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.flow.addWidget(line)
