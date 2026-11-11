"""Graphics items of the frame editor: the frame and its grips."""

from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPen, QPolygonF
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPolygonItem,
                               QGraphicsSimpleTextItem)

from scanbench.domain.frame_handle import FrameHandle

TOP_MARK = ("↑", "←", "↓", "→")
"""Arrow per quarter turn: which side of the frame becomes the top of the photo."""

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
        label = QGraphicsSimpleTextItem(f"{index + 1} {TOP_MARK[quarter_turns % 4]}", self)
        font = label.font()
        font.setPointSize(28)
        font.setBold(True)
        label.setFont(font)
        label.setBrush(QBrush(QColor(255, 255, 255)))
        label.setPen(QPen(QColor(0, 0, 0), 1))
        centre = polygon.boundingRect().center()
        box = label.boundingRect()
        label.setPos(centre.x() - box.width() / 2, centre.y() - box.height() / 2)
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
