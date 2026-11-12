"""Graphics items of the frame editor: the frame and its grips."""

from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPolygonItem,
                               QGraphicsRectItem, QGraphicsSimpleTextItem)

from scanbench.domain.frame_handle import FrameHandle

TOP_MARK = ("↑", "←", "↓", "→")
"""Arrow per quarter turn: which side of the frame becomes the top of the photo."""

BADGE_PAD = 5
"""Space left and right of the photo number in its box, in screen pixels."""

HANDLE_SIZE = 12
"""Diameter of a grip in screen pixels (independent of the zoom)."""

_CURSORS = {
    FrameHandle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    FrameHandle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    FrameHandle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    FrameHandle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    FrameHandle.TOP: Qt.CursorShape.SizeVerCursor,
    FrameHandle.BOTTOM: Qt.CursorShape.SizeVerCursor,
    FrameHandle.LEFT: Qt.CursorShape.SizeHorCursor,
    FrameHandle.RIGHT: Qt.CursorShape.SizeHorCursor,
    FrameHandle.ROTATE: Qt.CursorShape.CrossCursor,
}


def number_badge(number: int, parent: QGraphicsItem) -> QGraphicsRectItem:
    """Create the photo number in a filled box, same size at every zoom.

    Args:
        number: Number shown (1-based, as in the album index).
        parent: The frame.

    Returns:
        The badge; its top-left corner is placed by the caller.
    """
    badge = QGraphicsRectItem(parent)
    badge.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
    text = QGraphicsSimpleTextItem(str(number), badge)
    font = text.font()
    font.setPointSize(14)
    font.setBold(True)
    text.setFont(font)
    text.setBrush(QBrush(QColor(255, 255, 255)))
    box = text.boundingRect()
    text.setPos(BADGE_PAD, 0)
    badge.setRect(0, 0, box.width() + 2 * BADGE_PAD, box.height())
    badge.setBrush(QBrush(QColor(0, 110, 210)))
    badge.setPen(QPen(QColor(255, 255, 255), 1))
    return badge


class HandleItem(QGraphicsEllipseItem):
    """A grip of the selected frame; keeps its screen size at every zoom."""

    def __init__(self, handle: FrameHandle, position: QPointF, parent: QGraphicsItem) -> None:
        """Create the grip.

        Args:
            handle: Which grip.
            position: Centre in scene coordinates.
            parent: The frame item.
        """
        half = HANDLE_SIZE / 2
        super().__init__(-half, -half, HANDLE_SIZE, HANDLE_SIZE, parent)
        self.handle = handle
        self.setPos(position)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        rotate = handle is FrameHandle.ROTATE
        self.setBrush(QBrush(QColor(255, 160, 0) if rotate else QColor(255, 255, 255)))
        self.setPen(QPen(QColor(0, 120, 215), 2))
        self.setCursor(_CURSORS[handle])
        self.setToolTip("Drag to rotate; hold Shift for 0.5° steps" if rotate
                        else "Drag to resize")


class RegionItem(QGraphicsPolygonItem):
    """One photo frame; selectable, movable, with grips while selected."""

    def __init__(self, index: int, polygon: QPolygonF, quarter_turns: int) -> None:
        """Draw the frame with its number and top mark.

        Args:
            index: Position in the region list.
            polygon: Corners in scene coordinates.
            quarter_turns: Turns of the result, for the top mark.
        """
        super().__init__(polygon)
        self.index = index
        self.setPen(QPen(QColor(0, 160, 255), 3))
        self.setBrush(QBrush(QColor(0, 160, 255, 40)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setToolTip("Click to select, drag to move, drag the grips to resize or rotate; "
                        "right-click for more. The arrow points to the side that becomes "
                        "the top.")
        mark = QGraphicsSimpleTextItem(TOP_MARK[quarter_turns % 4], self)
        font = mark.font()
        font.setPointSize(28)
        font.setBold(True)
        mark.setFont(font)
        mark.setBrush(QBrush(QColor(255, 255, 255)))
        mark.setPen(QPen(QColor(0, 0, 0), 1))
        centre = polygon.boundingRect().center()
        box = mark.boundingRect()
        mark.setPos(centre.x() - box.width() / 2, centre.y() - box.height() / 2)
        corner = min(polygon.toList(), key=lambda p: p.x() + p.y())
        self.badge = number_badge(index + 1, self)
        self.badge.setPos(corner)
        self.handles: list[HandleItem] = []

    def add_handles(self, positions: dict[FrameHandle, QPointF]) -> None:
        """Create the grips; they are visible while the frame is selected.

        Args:
            positions: Scene position per grip.
        """
        for handle, position in positions.items():
            item = HandleItem(handle, position, self)
            item.setVisible(self.isSelected())
            self.handles.append(item)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange,  # noqa: N802 (Qt API)
                   value: Any) -> Any:
        """Show the grips only while the frame is selected.

        Args:
            change: Kind of change.
            value: New value.

        Returns:
            The value Qt continues with.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            for handle in self.handles:
                handle.setVisible(bool(value))
        return super().itemChange(change, value)
