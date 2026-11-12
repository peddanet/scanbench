"""Context menus of the frame editor (Command objects as menu actions)."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QMenu

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.paper_format import A4, PHOTO_PRESETS
from scanbench.ui.frame_items import RegionItem
from scanbench.ui.frame_values_dialog import FrameValuesDialog
from scanbench.ui.guide_items import GuideItem

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

    def split(self, index: int, across: bool) -> None:
        """Replace a frame by its two halves; the first half is selected.

        Args:
            index: Region index.
            across: True for top and bottom, False for left and right.
        """
        view = self._view
        first, second = frame_edit.split(view.regions[index], across)
        regions = list(view.regions)
        regions[index:index + 1] = [first, second]
        view.set_regions(regions, index)

    def _add_presets(self, menu: QMenu, centre: QPointF) -> None:
        """Add the submenu "Add frame here" with the photo sizes.

        Args:
            menu: Menu to extend.
            centre: Click position in scene coordinates.
        """
        add = menu.addMenu("Add frame here")
        for paper in PHOTO_PRESETS:
            add.addAction(paper.name).triggered.connect(
                lambda _=False, p=paper: self.add(centre, p.height_mm, p.width_mm))

    def item_menu(self, index: int, centre: QPointF | None = None) -> QMenu:
        """Build the context menu of a frame.

        Args:
            index: Region index.
            centre: Click position in scene coordinates, for "Add frame here".

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
        menu.addAction("Exact values ...").triggered.connect(lambda: self.edit_values(index))
        fit = menu.addMenu("Fit to size")
        for paper in PHOTO_PRESETS:
            fit.addAction(paper.name).triggered.connect(
                lambda _=False, p=paper: view.change(index, lambda r: r.fitted(p, view.dpi)))
        menu.addSeparator()
        menu.addAction("Split into top and bottom").triggered.connect(
            lambda: self.split(index, True))
        menu.addAction("Split into left and right").triggered.connect(
            lambda: self.split(index, False))
        if centre is not None:
            self._add_presets(menu, centre)
        chosen = self.selected_indices()
        if len(chosen) > 1 and index in chosen:
            menu.addAction(f"Merge {len(chosen)} selected frames").triggered.connect(
                lambda: self.merge(chosen))
        menu.addAction("Delete frame").triggered.connect(lambda: self.remove(index))
        return menu

    def selected_indices(self) -> list[int]:
        """Return the indices of all selected frames.

        Returns:
            Sorted indices.
        """
        return sorted(i.index for i in self._view.scene().selectedItems()
                      if isinstance(i, RegionItem))

    def merge(self, indices: list[int]) -> None:
        """Replace several frames by one enclosing frame.

        Args:
            indices: Frames to join (at least two).
        """
        view = self._view
        joined = frame_edit.merged([view.regions[i] for i in indices])
        rest = [r for i, r in enumerate(view.regions) if i not in indices]
        view.set_regions([*rest, joined.clamped(*view.frame_size)], len(rest))

    def background_menu(self, centre: QPointF) -> QMenu:
        """Build the context menu outside the frames.

        Args:
            centre: Click position in scene coordinates.

        Returns:
            The menu.
        """
        view = self._view
        menu = QMenu(view)
        self._add_presets(menu, centre)
        middle = QPointF(view.frame_size[0] / 2 * view.scale_factor,
                         view.frame_size[1] / 2 * view.scale_factor)
        menu.addAction("Add frame: whole page").triggered.connect(
            lambda: self.add(middle, A4.width_mm, A4.height_mm))
        menu.addAction("Delete all frames").triggered.connect(lambda: view.set_regions([]))
        return menu

    def edit_values(self, index: int) -> None:
        """Ask for exact width, height, skew and turn of a frame.

        Args:
            index: Region index.
        """
        view = self._view
        dialog = FrameValuesDialog(view.regions[index], view.dpi, view)
        if dialog.exec() == FrameValuesDialog.DialogCode.Accepted:
            view.change(index, lambda _r: dialog.region())

    def guide_menu(self, guide: GuideItem) -> QMenu:
        """Build the context menu of a guide.

        Args:
            guide: The guide.

        Returns:
            The menu.
        """
        menu = QMenu(self._view)
        menu.addAction("Remove guide").triggered.connect(
            lambda: self._view.scene().removeItem(guide))
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
        if isinstance(item, GuideItem):
            return self.guide_menu(item)
        while item is not None and not isinstance(item, RegionItem):
            item = item.parentItem()
        if isinstance(item, RegionItem):
            return self.item_menu(item.index, view.mapToScene(position.toPoint()))
        return self.background_menu(view.mapToScene(position.toPoint()))
