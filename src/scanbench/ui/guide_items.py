"""Horizontal and vertical guide lines over the scan."""

from typing import Any

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsScene

GUIDE_Z = 50.0
"""Guides lie above the scan and the frames."""

GRAB = 4.0
"""Half width of the area around a guide that reacts to the mouse."""


class GuideItem(QGraphicsLineItem):
    """A guide across the whole scan; it moves only across its own direction.

    Drag it to the place you need; drag it out of the scan to remove it.
    """

    def __init__(self, horizontal: bool, scene: QGraphicsScene) -> None:
        """Create a guide through the middle of the scene.

        Args:
            horizontal: True for a horizontal line, False for a vertical one.
            scene: The scene; its rectangle gives the length.
        """
        rect = scene.sceneRect()
        line = (QLineF(rect.left(), 0, rect.right(), 0) if horizontal
                else QLineF(0, rect.top(), 0, rect.bottom()))
        super().__init__(line)
        self.horizontal = horizontal
        pen = QPen(QColor(230, 0, 140), 1, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)       # one screen pixel at every zoom
        self.setPen(pen)
        self.setZValue(GUIDE_Z)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setCursor(Qt.CursorShape.SplitVCursor if horizontal
                       else Qt.CursorShape.SplitHCursor)
        self.setToolTip("Guide: drag to move, drag out of the scan or right-click to remove")
        centre = rect.center()
        self.setPos(QPointF(0, centre.y()) if horizontal else QPointF(centre.x(), 0))

    def shape(self) -> QPainterPath:
        """Make the thin line easy to grab: a few scene units wide.

        Returns:
            The grab area.
        """
        # not boundingRect(): for a cosmetic pen Qt derives it from shape()
        line = self.line()
        path = QPainterPath()
        path.addRect(QRectF(line.p1(), line.p2()).normalized()
                     .adjusted(-GRAB, -GRAB, GRAB, GRAB))
        return path

    def boundingRect(self) -> QRectF:  # noqa: N802 (Qt API)
        """Return the area to repaint: the grab area.

        Returns:
            The rectangle.
        """
        return self.shape().boundingRect()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange,  # noqa: N802 (Qt API)
                   value: Any) -> Any:
        """Keep the guide moving across its own direction only.

        Args:
            change: Kind of change.
            value: New value.

        Returns:
            The value Qt continues with.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange \
                and isinstance(value, QPointF):
            return QPointF(0, value.y()) if self.horizontal else QPointF(value.x(), 0)
        return super().itemChange(change, value)

    def outside(self) -> bool:
        """Whether the guide was dragged out of the scan.

        Returns:
            True if it should be removed.
        """
        rect = self.scene().sceneRect() if self.scene() is not None else None
        if rect is None:
            return False
        position = self.pos().y() if self.horizontal else self.pos().x()
        low, high = (rect.top(), rect.bottom()) if self.horizontal else (rect.left(),
                                                                         rect.right())
        return not low <= position <= high


def add_guide(scene: QGraphicsScene, horizontal: bool) -> GuideItem:
    """Add a guide through the middle of the scan.

    Args:
        scene: The scene.
        horizontal: Direction of the line.

    Returns:
        The new guide.
    """
    guide = GuideItem(horizontal, scene)
    scene.addItem(guide)
    return guide


def remove_guides(scene: QGraphicsScene, only_outside: bool = False) -> int:
    """Remove guides.

    Args:
        scene: The scene.
        only_outside: Remove only guides dragged out of the scan.

    Returns:
        Number of removed guides.
    """
    guides = [i for i in scene.items() if isinstance(i, GuideItem)
              and (not only_outside or i.outside())]
    for guide in guides:
        scene.removeItem(guide)
    return len(guides)
