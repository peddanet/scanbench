"""Preview of a full-frame scan with freely editable photo frames."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QContextMenuEvent, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap,
                           QPolygonF, QResizeEvent)
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.frame_handle import FrameHandle
from scanbench.ui.frame_items import HandleItem, PictureItem, RegionItem, SketchBand
from scanbench.ui.guide_items import remove_guides
from scanbench.ui.qt_images import read_preview
from scanbench.ui.region_menus import RegionMenus

MAX_PREVIEW = 1600
"""Longest edge of the preview pixmap; full-resolution scans are scaled down."""

ROTATE_GAP_PX = 28
"""Distance of the rotation grip above the frame, in screen pixels."""

SNAP_DEGREES = 0.5
"""Angle step while Shift is held during rotation."""

Drag = tuple[FrameHandle, int, list[CropRegion]]
"""Grabbed grip, frame index and the frames when the drag started."""


@dataclass
class ViewMode:
    """Modes the user switches in the toolbar.

    Attributes:
        fit: Keep the whole scan fitted into the view.
        draw: Dragging on free space draws a new frame.
    """

    fit: bool = True
    draw: bool = False


@dataclass
class Gesture:
    """The mouse gesture in progress.

    Attributes:
        drag: Grip drag, or None.
        sketch: Start point and rubber band of a frame being drawn, or None.
    """

    drag: Drag | None = None
    sketch: tuple[QPointF, SketchBand] | None = None


class RegionView(QGraphicsView):
    """Show a scan and let the user correct the proposed photo frames.

    With ``mode.draw`` on, dragging on free space draws a new frame.

    Regions are kept in scan pixels; the view draws them scaled onto the
    preview. The selected frame has grips: sides and corners resize it (the
    opposite side stays), the orange grip above the top edge rotates it.
    Keyboard on the selected frame: arrows move by one screen pixel (Shift: ten),
    ``+``/``-`` turn by 0.1°, Delete removes it. Each change emits
    ``regions_changed``; selecting emits ``frame_selected``.
    """

    regions_changed = Signal(list)
    """The list of regions after a user change."""

    frame_selected = Signal(int)
    """Index of the selected frame, -1 for none."""

    def __init__(self) -> None:
        """Create an empty scene."""
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.regions: list[CropRegion] = []
        self.dpi = 300
        self.scale_factor = 1.0
        self.frame_size = (0, 0)
        # One picture item for the whole life of the view: replacing its pixmap
        # avoids deleting graphics items under Python wrappers (see show_scan).
        self.picture = PictureItem()
        self.scene().addItem(self.picture)
        self.mode = ViewMode()
        self._gesture = Gesture()
        # A bound method is disconnected before the scene dies with the view.
        self.scene().selectionChanged.connect(self._selection_changed)

    def _selection_changed(self) -> None:
        """Report the selected frame."""
        self.frame_selected.emit(self.selected_index())

    def show_scan(self, path: Path | QImage | None, dpi: int,
                  regions: list[CropRegion]) -> None:
        """Show a scan with its regions, or clear the view.

        Args:
            path: Scan file (``OSError`` if unreadable; the view stays empty),
                an image (e.g. the page while it is scanned), or None to clear.
            dpi: Resolution of the scan.
            regions: Regions in scan pixels.
        """
        self._clear()
        self.regions = list(regions)
        self.dpi = dpi
        self.picture.setPixmap(QPixmap())     # stays empty if there is nothing to show
        if path is None:
            self.scene().setSceneRect(QRectF())
            return
        if isinstance(path, QImage):
            image, self.frame_size = path, (path.width(), path.height())
        else:
            image, self.frame_size = read_preview(path, MAX_PREVIEW)
        self.scale_factor = min(1.0, MAX_PREVIEW / max(1, *self.frame_size))
        self.picture.setPixmap(QPixmap.fromImage(image).scaled(
            round(self.frame_size[0] * self.scale_factor),
            round(self.frame_size[1] * self.scale_factor),
            Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.scene().setSceneRect(self.picture.boundingRect())
        self.mode.fit = True
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._draw(self.regions)

    def _clear(self) -> None:
        """Remove frames, guides and a half-drawn frame; keep the picture item.

        Not ``QGraphicsScene.clear()``: it deleted items in C++ while Python
        still held them, and releasing them crashed 0.2.5 (segmentation fault).
        """
        self._gesture = Gesture()
        scene = self.scene()
        scene.blockSignals(True)
        scene.clearSelection()
        for item in scene.items():
            if item.parentItem() is None and item is not self.picture:
                scene.removeItem(item)
        scene.blockSignals(False)
        self.frame_selected.emit(-1)

    def _scene_point(self, x: float, y: float) -> QPointF:
        """Convert scan pixels into scene coordinates.

        Args:
            x: Scan x.
            y: Scan y.

        Returns:
            The scene point.
        """
        return QPointF(x * self.scale_factor, y * self.scale_factor)

    def _rotate_gap(self) -> float:
        """Return the gap of the rotation grip in scan pixels.

        Returns:
            ``ROTATE_GAP_PX`` screen pixels converted to scan pixels.
        """
        zoom = max(self.transform().m11(), 1e-6)
        return ROTATE_GAP_PX / zoom / self.scale_factor

    def _draw(self, regions: list[CropRegion], selected: int = -1) -> None:
        """Replace the frame items by items for the given regions.

        Args:
            regions: Regions to draw.
            selected: Index to select afterwards, -1 for none.
        """
        self.scene().blockSignals(True)
        for item in self.scene().items():
            if isinstance(item, RegionItem):
                self.scene().removeItem(item)
        gap = self._rotate_gap()
        for index, region in enumerate(regions):
            polygon = QPolygonF([self._scene_point(x, y) for x, y in region.corners()])
            item = RegionItem(index, polygon, region.quarter_turns)
            self.scene().addItem(item)
            item.setSelected(index == selected)
            item.add_handles({h: self._scene_point(*frame_edit.handle_point(region, h, gap))
                              for h in FrameHandle})
        self.scene().blockSignals(False)
        self.frame_selected.emit(self.selected_index())

    def selected_index(self) -> int:
        """Return the index of the selected frame.

        Returns:
            The index, or -1 if none or several are selected.
        """
        chosen = [i for i in self.scene().selectedItems() if isinstance(i, RegionItem)]
        return chosen[0].index if len(chosen) == 1 else -1

    def set_regions(self, regions: list[CropRegion], selected: int = -1,
                    notify: bool = True) -> None:
        """Replace the regions and report the change.

        Args:
            regions: New regions in scan pixels.
            selected: Index to select afterwards, -1 for none.
            notify: Emit ``regions_changed``; False only redraws (e.g. after zooming).
        """
        self.regions = list(regions)
        self._draw(self.regions, selected)
        if notify:
            self.regions_changed.emit(list(self.regions))

    def change(self, index: int, edit: Callable[[CropRegion], CropRegion]) -> None:
        """Apply an edit to one region; it stays selected.

        Args:
            index: Region index.
            edit: Function returning the changed region.
        """
        regions = list(self.regions)
        regions[index] = edit(regions[index]).clamped(*self.frame_size)
        self.set_regions(regions, index)

    def _dragged(self, drag: Drag, position: QPointF, shift: bool) -> list[CropRegion]:
        """Return the regions with the grabbed grip moved to a view position.

        Args:
            drag: Grip, frame index and the regions when the drag started.
            position: Mouse position in view coordinates.
            shift: Whether Shift is held (angle steps while rotating).

        Returns:
            The previewed regions.
        """
        handle, index, regions = drag
        point = self.mapToScene(position.toPoint())
        x, y = point.x() / self.scale_factor, point.y() / self.scale_factor
        region = regions[index]
        if handle is FrameHandle.ROTATE:
            region = frame_edit.rotated_towards(region, x, y, SNAP_DEGREES if shift else 0.0)
        else:
            minimum = frame_edit.MIN_SIDE_MM / 25.4 * self.dpi
            region = frame_edit.resized(region, handle, x, y, minimum)
        preview = list(regions)
        preview[index] = region.clamped(*self.frame_size)
        return preview

    def _finish_sketch(self, band: SketchBand) -> None:
        """Turn the rubber band into a new, selected frame (if it is big enough).

        Args:
            band: The rubber band item.
        """
        rect = band.rect()
        self.scene().removeItem(band)
        minimum = frame_edit.MIN_SIDE_MM / 25.4 * self.dpi
        width, height = rect.width() / self.scale_factor, rect.height() / self.scale_factor
        if min(width, height) < minimum:
            return
        centre = rect.center()
        region = CropRegion(centre.x() / self.scale_factor, centre.y() / self.scale_factor,
                            width, height).clamped(*self.frame_size)
        self.set_regions([*self.regions, region], len(self.regions))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Start a grip drag, or let Qt select and move frames.

        Args:
            event: The event.
        """
        item = self.itemAt(event.position().toPoint())
        frame = item.parentItem() if isinstance(item, HandleItem) else None
        left = event.button() == Qt.MouseButton.LeftButton
        if isinstance(item, HandleItem) and isinstance(frame, RegionItem) and left:
            self._gesture.drag = (item.handle, frame.index, list(self.regions))
            event.accept()
            return
        if self.mode.draw and left and self.picture.shown():
            start = self.mapToScene(event.position().toPoint())
            band = SketchBand(start)
            self.scene().addItem(band)
            self._gesture.sketch = (start, band)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Preview a grip drag.

        Args:
            event: The event.
        """
        gesture = self._gesture
        if gesture.sketch is not None:
            start, band = gesture.sketch
            band.setRect(QRectF(start, self.mapToScene(event.position().toPoint())).normalized())
            return
        if gesture.drag is None:
            super().mouseMoveEvent(event)
            return
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        self._draw(self._dragged(gesture.drag, event.position(), shift), gesture.drag[1])

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Finish a grip drag or take over frames dragged to a new place.

        Args:
            event: The event.
        """
        gesture = self._gesture
        if gesture.sketch is not None:
            self._finish_sketch(gesture.sketch[1])
            gesture.sketch = None
            return
        if gesture.drag is not None:
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            index = gesture.drag[1]
            preview = self._dragged(gesture.drag, event.position(), shift)
            gesture.drag = None
            self.set_regions(preview, index)
            return
        super().mouseReleaseEvent(event)
        remove_guides(self.scene(), only_outside=True)
        moved = [i for i in self.scene().items()
                 if isinstance(i, RegionItem) and not i.pos().isNull()]
        if moved:
            regions = list(self.regions)
            for item in moved:
                old = regions[item.index]
                regions[item.index] = replace(
                    old, cx=old.cx + item.pos().x() / self.scale_factor,
                    cy=old.cy + item.pos().y() / self.scale_factor).clamped(*self.frame_size)
            self.set_regions(regions, moved[0].index if len(moved) == 1 else -1)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        """Move, turn or delete the selected frame with the keyboard.

        Args:
            event: The event.
        """
        index = self.selected_index()
        # one screen pixel, so zooming in makes the steps finer (at least one scan pixel)
        pixel = max(1.0, 1.0 / max(self.transform().m11() * self.scale_factor, 1e-9))
        edit = None if index < 0 else _key_edit(event, pixel)
        if edit is None:
            super().keyPressEvent(event)
        elif isinstance(edit, str):     # "delete"
            RegionMenus(self).remove(index)
        else:
            self.change(index, edit)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802 (Qt API)
        """Show the context menu.

        Args:
            event: The event.
        """
        menu = RegionMenus(self).menu_at(QPointF(event.pos()))
        if menu is not None:
            menu.popup(event.globalPos())

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        """Keep the whole scan visible.

        Args:
            event: The event.
        """
        super().resizeEvent(event)
        if self.picture.shown() and self.mode.fit:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._draw(self.regions, self.selected_index())


def _key_edit(event: QKeyEvent, pixel: float) -> Callable[[CropRegion], CropRegion] | str | None:
    """Translate a key into a frame edit.

    Args:
        event: The key event.
        pixel: Scan pixels per screen pixel; an arrow key moves by this,
            with Shift by ten times this.

    Returns:
        An edit function, ``"delete"``, or None for keys without meaning.
    """
    step = (10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1) * pixel
    shifts = {Qt.Key.Key_Left: (-step, 0.0), Qt.Key.Key_Right: (step, 0.0),
              Qt.Key.Key_Up: (0.0, -step), Qt.Key.Key_Down: (0.0, step)}
    key = Qt.Key(event.key())
    if key in shifts:
        dx, dy = shifts[key]
        return lambda r: frame_edit.moved(r, dx, dy)
    turns = {Qt.Key.Key_Plus: 0.1, Qt.Key.Key_Equal: 0.1, Qt.Key.Key_Minus: -0.1}
    if key in turns:
        degrees = turns[key]
        return lambda r: frame_edit.turned_by(r, degrees)
    if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
        return "delete"
    return None
