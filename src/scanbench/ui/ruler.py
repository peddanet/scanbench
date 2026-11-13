"""Rulers (centimetre scale) along the frame editor; guides are dragged out of them."""

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent, QPainter, QPaintEvent, QPalette
from PySide6.QtWidgets import QWidget

from scanbench.ui.guide_items import GuideItem, add_guide
from scanbench.ui.region_view import RegionView

THICKNESS = 22
"""Height of the top ruler and width of the left one in pixels."""

STEPS_MM = {1: 10, 2: 10, 5: 50, 10: 50, 20: 100, 50: 200, 100: 500}
"""Distance of the small ticks -> distance of the labelled ticks, in mm; the
smallest step whose ticks are at least ``MIN_TICK_PX`` apart wins."""

MIN_TICK_PX = 5
"""Smallest distance between two ticks on screen."""


class Ruler(QWidget):
    """A ruler at the top (horizontal) or left (vertical) edge of the scan view.

    As in GIMP, pressing the mouse on the ruler and dragging into the scan
    pulls out a guide line: from the top ruler a horizontal one, from the
    left ruler a vertical one. Released outside the scan, the guide is not
    kept.
    """

    def __init__(self, view: RegionView, horizontal: bool) -> None:
        """Create the ruler and follow the view's zoom and scrolling.

        Args:
            view: The scan view.
            horizontal: True for the top ruler.
        """
        super().__init__()
        self.view = view
        self.horizontal = horizontal
        self.guide: GuideItem | None = None
        if horizontal:
            self.setFixedHeight(THICKNESS)
        else:
            self.setFixedWidth(THICKNESS)
        self.setCursor(Qt.CursorShape.SplitVCursor if horizontal
                       else Qt.CursorShape.SplitHCursor)
        self.setToolTip("Scale in cm. Drag into the scan to add a "
                        + ("horizontal" if horizontal else "vertical") + " guide line")
        for scroll in (view.horizontalScrollBar(), view.verticalScrollBar()):
            scroll.valueChanged.connect(self.update)
            scroll.rangeChanged.connect(self.update)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        """Return the preferred size.

        Returns:
            Thickness across, anything along.
        """
        return QSize(100, THICKNESS) if self.horizontal else QSize(THICKNESS, 100)

    def _mm_per_scene(self) -> float:
        """Return millimetres per scene unit of the view.

        Returns:
            The factor, or 0 while no scan is shown.
        """
        view = self.view
        if not view.picture.shown() or view.dpi <= 0:
            return 0.0
        return 25.4 / view.dpi / view.scale_factor

    def _scene(self, offset: int) -> float:
        """Return the scene coordinate under a position along the ruler.

        Args:
            offset: Pixel along the ruler.

        Returns:
            Scene x (top ruler) or y (left ruler).
        """
        point = QPoint(offset, 0) if self.horizontal else QPoint(0, offset)
        inside = self.view.viewport().mapFromGlobal(self.mapToGlobal(point))
        scene = self.view.mapToScene(inside)
        return scene.x() if self.horizontal else scene.y()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt API)
        """Draw the ticks and the centimetre labels.

        Args:
            event: The paint event.
        """
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Button))
        painter.setPen(self.palette().color(QPalette.ColorRole.ButtonText))
        length = self.width() if self.horizontal else self.height()
        factor = self._mm_per_scene()
        if factor > 0:
            start, end = self._scene(0) * factor, self._scene(length) * factor
            px_per_mm = length / max(end - start, 1e-6)
            step = next((s for s in STEPS_MM if s * px_per_mm >= MIN_TICK_PX), max(STEPS_MM))
            first = int(start // step) * step
            for mm in range(first, int(end) + step, step):
                self._tick(painter, (mm - start) * px_per_mm, mm, step)
        painter.end()

    def _tick(self, painter: QPainter, at: float, mm: int, step: int) -> None:
        """Draw one tick; ticks on whole labelled centimetres are long.

        Args:
            painter: Active painter.
            at: Position along the ruler in pixels.
            mm: Millimetre value of the tick.
            step: Distance of the small ticks in mm.
        """
        major = mm % STEPS_MM[step] == 0
        size = THICKNESS - 2 if major else THICKNESS // 3
        pos = round(at)
        if self.horizontal:
            painter.drawLine(pos, THICKNESS - size, pos, THICKNESS)
        else:
            painter.drawLine(THICKNESS - size, pos, THICKNESS, pos)
        if major:
            text = str(mm // 10)                     # labels in centimetres
            box = (QRect(pos + 2, 0, 40, THICKNESS // 2 + 2) if self.horizontal
                   else QRect(1, pos + 1, THICKNESS - 2, THICKNESS // 2 + 2))
            font = painter.font()
            font.setPointSizeF(7)
            painter.setFont(font)
            painter.drawText(box, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, text)

    def _place(self, global_point: QPoint) -> bool:
        """Move the dragged guide to a screen point.

        Args:
            global_point: Mouse position on the screen.

        Returns:
            True if the point lies over the scan view.
        """
        viewport = self.view.viewport()
        inside = viewport.mapFromGlobal(global_point)
        scene = self.view.mapToScene(inside)
        if self.guide is not None:
            self.guide.setPos(QPointF(0, scene.y()) if self.horizontal
                              else QPointF(scene.x(), 0))
        return viewport.rect().contains(inside)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Pull a new guide out of the ruler.

        Args:
            event: The event.
        """
        if event.button() != Qt.MouseButton.LeftButton or not self.view.picture.shown():
            event.ignore()
            return
        self.guide = add_guide(self.view.scene(), self.horizontal)
        self._place(event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Let the guide follow the mouse.

        Args:
            event: The event.
        """
        self._place(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Keep the guide if it was dropped on the scan.

        Args:
            event: The event.
        """
        guide = self.guide
        if guide is None:
            return
        over = self._place(event.globalPosition().toPoint())
        self.guide = None
        if not over or guide.outside():
            self.view.scene().removeItem(guide)
