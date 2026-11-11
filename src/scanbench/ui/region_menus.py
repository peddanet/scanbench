"""Context menus of the frame editor (Command objects as menu actions)."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QMenu

from scanbench.domain.crop_region import CropRegion
from scanbench.domain.paper_format import A4, PHOTO_PRESETS
from scanbench.ui.frame_items import RegionItem

if TYPE_CHECKING:
    from scanbench.ui.region_view import RegionView


class RegionMenus:
    """Build the menus of a frame and of free space, and run their commands."""

    def __init__(self, view: "RegionView") -> None:
        """Store the view the commands act on.

        Args:
            view: The frame editor.
        """
        self._view = view

    def remove(self, index: int) -> None:
        """Delete a frame.

        Args:
            index: Region index.
        """
        self._view.set_regions([r for i, r in enumerate(self._view.regions) if i != index])

    def add(self, centre: QPointF, width_mm: float, height_mm: float) -> None:
        """Add a frame of a given size around a scene point and select it.

        Args:
            centre: Centre in scene coordinates.
            width_mm: Width in millimetres.
            height_mm: Height in millimetres.
        """
        view = self._view
        mm = view.dpi / 25.4
        region = CropRegion(centre.x() / view.scale_factor, centre.y() / view.scale_factor,
                            width_mm * mm, height_mm * mm).clamped(*view.frame_size)
        view.set_regions([*view.regions, region], len(view.regions))

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
        menu.addAction("Delete frame").triggered.connect(lambda: self.remove(index))
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
                lambda _=False, p=paper: self.add(centre, p.height_mm, p.width_mm))
        middle = QPointF(view.frame_size[0] / 2 * view.scale_factor,
                         view.frame_size[1] / 2 * view.scale_factor)
        menu.addAction("Add frame: whole page").triggered.connect(
            lambda: self.add(middle, A4.width_mm, A4.height_mm))
        menu.addAction("Delete all frames").triggered.connect(lambda: view.set_regions([]))
        return menu

    def menu_at(self, position: QPointF) -> QMenu | None:
        """Return the context menu for a view position.

        Args:
            position: Position in view coordinates.

        Returns:
            The menu, or None when no scan is shown.
        """
        view = self._view
        if view.pixmap_item is None:
            return None
        item = view.itemAt(position.toPoint())
        while item is not None and not isinstance(item, RegionItem):
            item = item.parentItem()
        if isinstance(item, RegionItem):
            return self.item_menu(item.index)
        return self.background_menu(view.mapToScene(position.toPoint()))
