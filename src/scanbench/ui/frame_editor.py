"""Frame editor: toolbar, region view, details line and hint."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QGraphicsView, QLabel, QVBoxLayout, QWidget

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.frame_history import FrameHistory
from scanbench.ui.flow_bar import FlowBar
from scanbench.ui.guide_items import add_guide, remove_guides
from scanbench.ui.qt_images import to_qimage
from scanbench.ui.region_menus import RegionMenus
from scanbench.ui.region_view import RegionView
from scanbench.ui.zoom_control import ZoomControl

NO_SELECTION = "Click a frame to see its size, skew and orientation."
"""Details text while no frame is selected."""

TOOLS = (
    ("undo", "Undo", QKeySequence.StandardKey.Undo, "Undo the last frame change"),
    ("redo", "Redo", QKeySequence.StandardKey.Redo, "Redo the undone change"),
    ("zoom_in", "Zoom in", QKeySequence.StandardKey.ZoomIn, "Zoom in (also Ctrl + wheel)"),
    ("zoom_out", "Zoom out", QKeySequence.StandardKey.ZoomOut, "Zoom out"),
    ("fit", "Fit", "Ctrl+0", "Show the whole scan"),
    ("actual", "100 %", "Ctrl+1", "One scan pixel per screen pixel"),
    ("draw", "Draw frame", "D", "Drag on the scan to draw a new frame (Esc to stop)"),
    ("h_guide", "Horizontal guide", "H", "Add a horizontal guide line; drag it into place"),
    ("v_guide", "Vertical guide", "V", "Add a vertical guide line; drag it into place"),
    ("no_guides", "Remove guides", None, "Remove all guide lines"),
    ("values", "Exact values ...", "E", "Width, height, skew and turn of the selected frame"),
    ("previous", "Previous photo", "PgUp", "Select the frame with the next lower number"),
    ("next", "Next photo", "PgDown", "Select the frame with the next higher number"),
)
"""Toolbar actions: key, text, shortcut, tooltip."""


@dataclass
class EditorTools:
    """The toolbar and what it controls.

    Attributes:
        toolbar: The tool buttons; they wrap into a second row when narrow.
        actions: Actions by key.
        zoom: Zoom controller.
    """

    toolbar: FlowBar
    actions: dict[str, QAction]
    zoom: ZoomControl


class FrameEditor(QWidget):
    """The region view with tools, a line describing the selected frame and a hint.

    Every frame change is recorded, so it can be undone and redone; the
    history starts anew with every scan.
    """

    def __init__(self, hint: str) -> None:
        """Build the widgets.

        Args:
            hint: Initial hint text.
        """
        super().__init__()
        self.view = RegionView()
        self.details = QLabel()
        self.hint = QLabel(hint)
        self.hint.setWordWrap(True)
        self.history = FrameHistory()
        self._replaying = False
        self.tools = EditorTools(FlowBar(), {}, ZoomControl(self.view))
        self._build_tools()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tools.toolbar)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.details)
        layout.addWidget(self.hint)
        self.view.frame_selected.connect(self.describe)
        self.view.regions_changed.connect(self._changed)
        self.describe(-1)

    def _build_tools(self) -> None:
        """Create the toolbar actions and connect them."""
        handlers = {
            "undo": self.undo, "redo": self.redo, "zoom_in": self.tools.zoom.zoom_in,
            "zoom_out": self.tools.zoom.zoom_out, "fit": self.tools.zoom.fit,
            "actual": self.tools.zoom.actual_size, "draw": self.set_draw_mode,
            "h_guide": lambda: self._guide(True), "v_guide": lambda: self._guide(False),
            "no_guides": lambda: remove_guides(self.view.scene()),
            "values": self._edit_values, "previous": lambda: self.select_photo(-1),
            "next": lambda: self.select_photo(1)}
        for key, text, shortcut, tip in TOOLS:
            action = QAction(text, self)
            action.setToolTip(f"{tip} ({QKeySequence(shortcut).toString()})" if shortcut
                              else tip)
            if shortcut is not None:
                action.setShortcut(QKeySequence(shortcut))
                action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            if key == "draw":
                action.setCheckable(True)
                action.toggled.connect(self.set_draw_mode)
            else:
                action.triggered.connect(handlers[key])
            self.tools.toolbar.addAction(action)
            self.addAction(action)
            self.tools.actions[key] = action
            if key in ("redo", "actual", "draw", "no_guides", "values"):
                self.tools.toolbar.addSeparator()
        # Esc ends draw mode; it is enabled only then, so that otherwise Esc
        # cancels a running job (shortcut of the progress panel)
        stop = QAction(self)
        stop.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        stop.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        stop.triggered.connect(lambda: self.tools.actions["draw"].setChecked(False))
        stop.setEnabled(False)
        self.addAction(stop)
        self.tools.actions["stop_draw"] = stop
        self._update_actions()

    def _guide(self, horizontal: bool) -> None:
        """Add a guide line if a scan is shown.

        Args:
            horizontal: Direction of the guide.
        """
        if self.view.picture.shown():
            add_guide(self.view.scene(), horizontal)

    def _edit_values(self) -> None:
        """Open the exact-values dialog for the selected frame."""
        index = self.view.selected_index()
        if index >= 0:
            RegionMenus(self.view).edit_values(index)

    def select_photo(self, step: int) -> None:
        """Select the previous or next frame and bring it into view.

        Args:
            step: -1 for the previous, 1 for the next frame (wraps around).
        """
        view = self.view
        count = len(view.regions)
        if not count:
            return
        current = view.selected_index()
        index = (current + step) % count if current >= 0 else (0 if step > 0 else count - 1)
        view.set_regions(view.regions, index, notify=False)
        chosen = view.scene().selectedItems()
        if chosen:
            view.ensureVisible(chosen[0])

    def set_draw_mode(self, on: bool) -> None:
        """Switch the drawing of new frames on or off.

        Args:
            on: True to draw frames by dragging.
        """
        self.view.mode.draw = bool(on)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag if on
                              else QGraphicsView.DragMode.RubberBandDrag)
        self.view.viewport().setCursor(Qt.CursorShape.CrossCursor if on
                                       else Qt.CursorShape.ArrowCursor)
        action = self.tools.actions.get("draw")
        if action is not None and action.isChecked() != bool(on):
            action.setChecked(bool(on))
        stop = self.tools.actions.get("stop_draw")
        if stop is not None:
            stop.setEnabled(bool(on))

    def _changed(self, regions: list[CropRegion]) -> None:
        """Record a user change and update the details line.

        Args:
            regions: Frames after the change.
        """
        if not self._replaying:
            self.history.record(regions)
        self._update_actions()
        self.describe(self.view.selected_index())

    def _replay(self, state: tuple[CropRegion, ...] | None) -> None:
        """Show frames from the history without recording them again.

        Args:
            state: Frames to show, or None if there is no step.
        """
        if state is None:
            return
        self._replaying = True
        try:
            self.view.set_regions(list(state))
        finally:
            self._replaying = False

    def undo(self) -> None:
        """Undo the last frame change."""
        self._replay(self.history.undo())

    def redo(self) -> None:
        """Redo the last undone frame change."""
        self._replay(self.history.redo())

    def _update_actions(self) -> None:
        """Enable undo and redo only when there is a step."""
        self.tools.actions["undo"].setEnabled(self.history.can_undo())
        self.tools.actions["redo"].setEnabled(self.history.can_redo())

    def describe(self, index: int) -> None:
        """Show size, skew and orientation of a frame.

        Args:
            index: Frame index, -1 for none.
        """
        regions = self.view.regions
        if 0 <= index < len(regions):
            self.details.setText(f"Frame {index + 1}: "
                                 f"{frame_edit.summary(regions[index], self.view.dpi)}")
        else:
            self.details.setText(NO_SELECTION if regions else "")

    def show_live(self, pixels: NDArray[np.uint8]) -> None:
        """Show the page while it is being scanned, without frames.

        Args:
            pixels: The page so far.
        """
        self.view.show_scan(to_qimage(pixels), self.view.dpi, [])
        self.details.setText("Scanning ...")

    def show_scan(self, path: Path | None, dpi: int, regions: list[CropRegion]) -> None:
        """Show a scan (or nothing); the undo history starts anew.

        Args:
            path: Full-frame scan, or None.
            dpi: Its resolution.
            regions: Proposed frames.
        """
        self.view.show_scan(path, dpi, regions)
        self.history.reset(regions)
        self._update_actions()
        self.describe(-1)
