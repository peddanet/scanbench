"""Preview of a full-frame scan with freely editable photo frames."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (QContextMenuEvent, QKeyEvent, QMouseEvent, QPainter, QPixmap,
                           QPolygonF, QResizeEvent)
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.frame_handle import FrameHandle
from scanbench.ui.frame_items import HandleItem, RegionItem
from scanbench.ui.region_menus import RegionMenus

MAX_PREVIEW = 1600
"""Longest edge of the preview pixmap; full-resolution scans are scaled down."""

ROTATE_GAP_PX = 28
"""Distance of the rotation grip above the frame, in screen pixels."""

SNAP_DEGREES = 0.5
"""Angle step while Shift is held during rotation."""


class RegionView(QGraphicsView):
    """Show a scan and let the user correct the proposed photo frames.

    Regions are kept in scan pixels; the view draws them scaled onto the
    preview. The selected frame has grips: sides and corners resize it (the
    opposite side stays), the orange grip above the top edge rotates it.
    Keyboard on the selected frame: arrows move by 1 mm (Shift: 10 mm),
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
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self._drag: tuple[FrameHandle, int, list[CropRegion]] | None = None
        # A bound method is disconnected before the scene dies with the view.
        self.scene().selectionChanged.connect(self._selection_changed)

    def _selection_changed(self) -> None:
        """Report the selected frame."""
        self.frame_selected.emit(self.selected_index())

    def show_scan(self, path: Path | None, dpi: int, regions: list[CropRegion]) -> None:
        """Show a scan with its regions, or clear the view.

        Args:
            path: Full-frame scan, or None to clear.
            dpi: Resolution of the scan.
            regions: Regions in scan pixels.
        """
        self.scene().clear()
        self.pixmap_item = None
        self.regions = list(regions)
        self.dpi = dpi
        if path is None:
            return
        full = QPixmap(str(path))
        self.frame_size = (full.width(), full.height())
        self.scale_factor = min(1.0, MAX_PREVIEW / max(1, full.width(), full.height()))
        preview = full.scaled(round(full.width() * self.scale_factor),
                              round(full.height() * self.scale_factor),
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        self.pixmap_item = self.scene().addPixmap(preview)
        self.scene().setSceneRect(self.pixmap_item.boundingRect())
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._draw(self.regions)

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

    def set_regions(self, regions: list[CropRegion], selected: int = -1) -> None:
        """Replace the regions and report the change.

        Args:
            regions: New regions in scan pixels.
            selected: Index to select afterwards, -1 for none.
        """
        self.regions = list(regions)
        self._draw(self.regions, selected)
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

    def _dragged(self, drag: tuple[FrameHandle, int, list[CropRegion]], position: QPointF,
                 shift: bool) -> list[CropRegion]:
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

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Start a grip drag, or let Qt select and move frames.

        Args:
            event: The event.
        """
        item = self.itemAt(event.position().toPoint())
        frame = item.parentItem() if isinstance(item, HandleItem) else None
        if isinstance(item, HandleItem) and isinstance(frame, RegionItem) \
                and event.button() == Qt.MouseButton.LeftButton:
            self._drag = (item.handle, frame.index, list(self.regions))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Preview a grip drag.

        Args:
            event: The event.
        """
        if self._drag is None:
            super().mouseMoveEvent(event)
            return
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        self._draw(self._dragged(self._drag, event.position(), shift), self._drag[1])

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Finish a grip drag or take over frames dragged to a new place.

        Args:
            event: The event.
        """
        if self._drag is not None:
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            preview, index = self._dragged(self._drag, event.position(), shift), self._drag[1]
            self._drag = None
            self.set_regions(preview, index)
            return
        super().mouseReleaseEvent(event)
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
        edit = None if index < 0 else _key_edit(event, self.dpi)
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
        if self.pixmap_item is not None:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._draw(self.regions, self.selected_index())


def _key_edit(event: QKeyEvent, dpi: int) -> Callable[[CropRegion], CropRegion] | str | None:
    """Translate a key into a frame edit.

    Args:
        event: The key event.
        dpi: Resolution of the scan.

    Returns:
        An edit function, ``"delete"``, or None for keys without meaning.
    """
    step = (10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1) / 25.4 * dpi
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
