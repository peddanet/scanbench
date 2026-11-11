"""Preview of a full-frame scan with editable photo frames."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QContextMenuEvent, QMouseEvent, QPainter, QPen,
                           QPixmap, QPolygonF, QResizeEvent)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPixmapItem, QGraphicsPolygonItem,
                               QGraphicsScene, QGraphicsSimpleTextItem, QGraphicsView, QMenu)

from scanbench.domain.crop_region import CropRegion
from scanbench.domain.paper_format import A4, PHOTO_PRESETS

MAX_PREVIEW = 1600
"""Longest edge of the preview pixmap; full-resolution scans are scaled down."""

TOP_MARK = ("↑", "←", "↓", "→")
"""Arrow per quarter turn: which side of the frame becomes the top of the photo."""


class RegionItem(QGraphicsPolygonItem):
    """One photo frame; selectable and movable with the mouse."""

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
        self.setToolTip("Right-click: rotate, straighten, fit to a size, delete. "
                        "The arrow points to the side that becomes the top.")
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


class RegionView(QGraphicsView):
    """Show a scan and let the user correct the proposed photo frames.

    Regions are kept in scan pixels; the view draws them scaled onto the
    preview. Each change emits ``regions_changed`` with the new list.
    """

    regions_changed = Signal(list)
    """The list of regions after a user change."""

    def __init__(self) -> None:
        """Create an empty scene."""
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.regions: list[CropRegion] = []
        self.dpi = 300
        self.scale_factor = 1.0
        self.frame_size = (0, 0)
        self.pixmap_item: QGraphicsPixmapItem | None = None

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
        self._draw()
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw(self) -> None:
        """Replace the frame items by items for the current regions."""
        for item in self.scene().items():
            if isinstance(item, RegionItem):
                self.scene().removeItem(item)
        for index, region in enumerate(self.regions):
            polygon = QPolygonF([QPointF(x * self.scale_factor, y * self.scale_factor)
                                 for x, y in region.corners()])
            self.scene().addItem(RegionItem(index, polygon, region.quarter_turns))

    def set_regions(self, regions: list[CropRegion]) -> None:
        """Replace the regions and report the change.

        Args:
            regions: New regions in scan pixels.
        """
        self.regions = list(regions)
        self._draw()
        self.regions_changed.emit(list(self.regions))

    def change(self, index: int, edit: Callable[[CropRegion], CropRegion]) -> None:
        """Apply an edit to one region.

        Args:
            index: Region index.
            edit: Function returning the changed region.
        """
        regions = list(self.regions)
        regions[index] = edit(regions[index]).clamped(*self.frame_size)
        self.set_regions(regions)

    def remove(self, index: int) -> None:
        """Delete a region.

        Args:
            index: Region index.
        """
        self.set_regions([r for i, r in enumerate(self.regions) if i != index])

    def add(self, centre: QPointF, width_mm: float, height_mm: float) -> None:
        """Add a landscape frame of a given size around a scene point.

        Args:
            centre: Centre in scene coordinates.
            width_mm: Width in millimetres.
            height_mm: Height in millimetres.
        """
        mm = self.dpi / 25.4
        region = CropRegion(centre.x() / self.scale_factor, centre.y() / self.scale_factor,
                            width_mm * mm, height_mm * mm).clamped(*self.frame_size)
        self.set_regions([*self.regions, region])

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802 (Qt API)
        """Show the context menu.

        Args:
            event: The event.
        """
        menu = RegionMenus(self).menu_at(QPointF(event.pos()))
        if menu is not None:
            menu.popup(event.globalPos())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        """Take over frames the user dragged to a new place.

        Args:
            event: The event.
        """
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
            self.set_regions(regions)

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 (Qt API)
        """Keep the whole scan visible.

        Args:
            event: The event.
        """
        super().resizeEvent(event)
        if self.pixmap_item is not None:
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class RegionMenus:
    """Context menus of the frame editor (Command objects as menu actions)."""

    def __init__(self, view: RegionView) -> None:
        """Store the view the commands act on.

        Args:
            view: The frame editor.
        """
        self._view = view

    def item_menu(self, index: int) -> QMenu:
        """Build the context menu of a frame.

        Args:
            index: Region index.

        Returns:
            The menu.
        """
        view = self._view
        menu = QMenu(view)
        menu.addAction("Rotate 90° clockwise").triggered.connect(
            lambda: view.change(index, lambda r: r.turned(1)))
        menu.addAction("Rotate 90° counter-clockwise").triggered.connect(
            lambda: view.change(index, lambda r: r.turned(-1)))
        menu.addAction("Rotate 180°").triggered.connect(
            lambda: view.change(index, lambda r: r.turned(2)))
        menu.addAction("Align horizontally (remove skew)").triggered.connect(
            lambda: view.change(index, CropRegion.straightened))
        fit = menu.addMenu("Fit to size")
        for paper in PHOTO_PRESETS:
            fit.addAction(paper.name).triggered.connect(
                lambda _=False, p=paper: view.change(index, lambda r: r.fitted(p, view.dpi)))
        menu.addSeparator()
        menu.addAction("Delete frame").triggered.connect(lambda: view.remove(index))
        return menu

    def background_menu(self, centre: QPointF) -> QMenu:
        """Build the context menu outside the frames.

        Args:
            centre: Click position in scene coordinates.

        Returns:
            The menu.
        """
        view = self._view
        menu = QMenu(view)
        add = menu.addMenu("Add frame here")
        for paper in PHOTO_PRESETS:
            add.addAction(paper.name).triggered.connect(
                lambda _=False, p=paper: view.add(centre, p.height_mm, p.width_mm))
        middle = QPointF(view.frame_size[0] / 2 * view.scale_factor,
                         view.frame_size[1] / 2 * view.scale_factor)
        menu.addAction("Add frame: whole page").triggered.connect(
            lambda: view.add(middle, A4.width_mm, A4.height_mm))
        menu.addAction("Delete all frames").triggered.connect(lambda: view.set_regions([]))
        return menu

    def menu_at(self, position: QPointF) -> QMenu | None:
        """Return the context menu for a view position.

        Args:
            position: Position in view coordinates.

        Returns:
            The menu, or None when no scan is shown.
        """
        if self._view.pixmap_item is None:
            return None
        item = self._view.itemAt(position.toPoint())
        while item is not None and not isinstance(item, RegionItem):
            item = item.parentItem()
        if isinstance(item, RegionItem):
            return self.item_menu(item.index)
        return self.background_menu(self._view.mapToScene(position.toPoint()))
