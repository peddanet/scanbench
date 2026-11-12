"""GUI tests of the editor toolbar: undo, zoom, guides, drawing, values, merging."""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QMenu
from pytestqt.qtbot import QtBot

from editor_helpers import MM, editor_with, item, mouse
from scenes import DPI, Placed
from scanbench.domain.crop_region import CropRegion
from scanbench.ui.frame_editor import FrameEditor
from scanbench.ui.frame_items import RegionItem
from scanbench.ui.frame_values_dialog import FrameValuesDialog
from scanbench.ui.guide_items import GuideItem
from scanbench.ui.region_menus import RegionMenus
from scanbench.ui.region_view import RegionView


def _trigger(menu: QMenu, text: str) -> None:
    """Trigger a menu entry by its text, also in submenus.

    Args:
        menu: The menu.
        text: Entry text.
    """
    for action in menu.actions():
        if action.menu() is not None:
            sub = action.menu()
            assert isinstance(sub, QMenu)
            if any(a.text() == text for a in sub.actions()):
                _trigger(sub, text)
                return
        if action.text() == text:
            action.trigger()
            return
    raise AssertionError(f"no entry {text!r}")


def _guides(view: RegionView) -> list[GuideItem]:
    """Return the guide lines in the scene.

    Args:
        view: The view.

    Returns:
        The guides.
    """
    return [i for i in view.scene().items() if isinstance(i, GuideItem)]


def test_undo_and_redo(tmp_path: Path, qtbot: QtBot) -> None:
    """Edits can be undone and redone; a new scan clears the history.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60)])
    actions = editor.tools.actions
    before = editor.view.regions[0]
    assert not actions["undo"].isEnabled() and not actions["redo"].isEnabled()
    editor.view.change(0, lambda r: CropRegion(r.cx + 10, r.cy, r.width, r.height))
    assert actions["undo"].isEnabled()
    actions["undo"].trigger()
    assert editor.view.regions[0] == before and actions["redo"].isEnabled()
    actions["redo"].trigger()
    assert editor.view.regions[0].cx == pytest.approx(before.cx + 10)
    editor.redo()                                   # nothing left: no change
    editor.show_scan(None, DPI, [])
    assert not actions["undo"].isEnabled() and editor.details.text() == ""


def test_zoom_tools_and_wheel(tmp_path: Path, qtbot: QtBot) -> None:
    """Zoom in, out, 100 %, fit and Ctrl + wheel change the view scale.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60)])
    zoom, actions = editor.tools.zoom, editor.tools.actions
    start = zoom.scale()
    actions["zoom_in"].trigger()
    assert zoom.scale() == pytest.approx(start * 1.25)
    assert not editor.view.mode.fit
    actions["zoom_out"].trigger()
    assert zoom.scale() == pytest.approx(start)
    actions["actual"].trigger()
    assert zoom.scale() * editor.view.scale_factor == pytest.approx(1.0)
    for _ in range(40):
        zoom.zoom_in()
    assert zoom.scale() == pytest.approx(16.0)
    actions["fit"].trigger()
    assert editor.view.mode.fit
    fitted = zoom.scale()
    point = QPointF(100, 100)

    def wheel(modifiers: Qt.KeyboardModifier) -> None:
        """Send a wheel step to the viewport.

        Args:
            modifiers: Keyboard modifiers.
        """
        event = QWheelEvent(point, point, QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                            modifiers, Qt.ScrollPhase.NoScrollPhase, False)
        zoom.eventFilter(editor.view.viewport(), event)
    wheel(Qt.KeyboardModifier.ControlModifier)
    assert zoom.scale() == pytest.approx(fitted * 1.25)
    wheel(Qt.KeyboardModifier.NoModifier)
    assert zoom.scale() == pytest.approx(fitted * 1.25)


def test_guides_add_move_and_remove(tmp_path: Path, qtbot: QtBot) -> None:
    """Guides are added, stay on their axis, and are removed in three ways.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60)])
    view, actions = editor.view, editor.tools.actions
    actions["h_guide"].trigger()
    actions["v_guide"].trigger()
    horizontal = next(g for g in _guides(view) if g.horizontal)
    vertical = next(g for g in _guides(view) if not g.horizontal)
    horizontal.setPos(QPointF(30, 40))
    assert horizontal.pos() == QPointF(0, 40) and not horizontal.outside()
    vertical.setPos(QPointF(-50, 99))
    assert vertical.pos() == QPointF(-50, 0) and vertical.outside()
    mouse(view, QEvent.Type.MouseButtonRelease, QPointF(5, 5))
    assert _guides(view) == [horizontal]
    menu = RegionMenus(view).menu_at(QPointF(view.mapFromScene(QPointF(20, 40))))
    assert menu is not None
    _trigger(menu, "Remove guide")
    assert not _guides(view)
    actions["h_guide"].trigger()
    actions["no_guides"].trigger()
    assert not _guides(view)
    editor.show_scan(None, DPI, [])
    actions["h_guide"].trigger()
    assert not _guides(view)


def test_draw_frame(tmp_path: Path, qtbot: QtBot) -> None:
    """In draw mode a drag makes a new selected frame; tiny drags are ignored.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60)])
    view = editor.view
    editor.tools.actions["draw"].setChecked(True)
    assert view.mode.draw
    scale = view.scale_factor
    start, end = QPointF(20 * MM * scale, 150 * MM * scale), QPointF(120 * MM * scale,
                                                                     220 * MM * scale)
    mouse(view, QEvent.Type.MouseButtonPress, start)
    mouse(view, QEvent.Type.MouseMove, end)
    mouse(view, QEvent.Type.MouseButtonRelease, end)
    assert len(view.regions) == 2 and view.selected_index() == 1
    drawn = view.regions[1]
    assert drawn.width / MM == pytest.approx(100, abs=2)
    assert drawn.height / MM == pytest.approx(70, abs=2)
    free = QPointF(180 * MM * scale, 270 * MM * scale)
    mouse(view, QEvent.Type.MouseButtonPress, free)
    mouse(view, QEvent.Type.MouseButtonRelease, QPointF(free.x() + 2, free.y() + 2))
    assert len(view.regions) == 2
    editor.set_draw_mode(False)
    assert not editor.tools.actions["draw"].isChecked() and not view.mode.draw
    editor.undo()
    assert len(view.regions) == 1


def test_exact_values(tmp_path: Path, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    """The values dialog sets width, height, skew and turn of one frame.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        monkeypatch: pytest helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60), Placed(100, 70, 80, 160)])
    editor.tools.actions["values"].trigger()          # nothing selected: no dialog
    dialog = FrameValuesDialog(editor.view.regions[0], DPI)
    qtbot.addWidget(dialog)
    assert dialog.width_mm.value() == pytest.approx(100, abs=0.1)

    def accept(self: FrameValuesDialog) -> int:
        """Change the values and accept.

        Args:
            self: The dialog.

        Returns:
            Accepted.
        """
        self.width_mm.setValue(102)
        self.height_mm.setValue(76)
        self.angle.setValue(-1.3)
        self.turn.setCurrentIndex(3)
        return int(FrameValuesDialog.DialogCode.Accepted.value)
    monkeypatch.setattr(FrameValuesDialog, "exec", accept)
    item(editor.view, 1).setSelected(True)
    editor.tools.actions["values"].trigger()
    region = editor.view.regions[1]
    assert region.width / MM == pytest.approx(102, abs=0.1)
    assert region.height / MM == pytest.approx(76, abs=0.1)
    assert region.angle == pytest.approx(-1.3) and region.quarter_turns == 3
    assert editor.view.regions[0] == Placed(100, 70, 80, 60).region()
    monkeypatch.setattr(FrameValuesDialog, "exec",
                        lambda _self: int(FrameValuesDialog.DialogCode.Rejected.value))
    menu = RegionMenus(editor.view).item_menu(1)
    _trigger(menu, "Exact values ...")
    assert editor.view.regions[1] == region


def test_merge_selected_frames(tmp_path: Path, qtbot: QtBot) -> None:
    """Two selected frames are merged into one enclosing frame.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60), Placed(100, 70, 80, 130)])
    view = editor.view
    single = RegionMenus(view).item_menu(0)
    assert not any(a.text().startswith("Merge") for a in single.actions())
    for index in (0, 1):
        item(view, index).setSelected(True)
    menu = RegionMenus(view).item_menu(0)
    _trigger(menu, "Merge 2 selected frames")
    assert len(view.regions) == 1
    joined = view.regions[0]
    assert joined.width / MM == pytest.approx(100, abs=1)
    assert joined.height / MM == pytest.approx(140, abs=1)
    assert isinstance(item(view, 0), RegionItem)


def test_live_image(qtbot: QtBot) -> None:
    """A partial scan is shown without frames.

    Args:
        qtbot: pytest-qt helper.
    """
    editor = FrameEditor("hint")
    qtbot.addWidget(editor)
    editor.show_live(np.full((40, 30, 3), 128, dtype=np.uint8))
    assert editor.view.pixmap_item is not None and editor.details.text() == "Scanning ..."


def test_previous_and_next_photo(tmp_path: Path, qtbot: QtBot) -> None:
    """Frames are stepped through in number order, wrapping around; badges show numbers.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot, [Placed(100, 70, 80, 60), Placed(100, 70, 80, 160)])
    actions = editor.tools.actions
    badge = item(editor.view, 1).badge
    assert badge.childItems()[0].text() == "2"     # type: ignore[attr-defined]
    actions["previous"].trigger()
    assert editor.view.selected_index() == 1 and editor.details.text().startswith("Frame 2")
    actions["next"].trigger()
    assert editor.view.selected_index() == 0
    actions["previous"].trigger()
    assert editor.view.selected_index() == 1
    editor.show_scan(None, DPI, [])
    actions["next"].trigger()
    assert editor.view.selected_index() == -1
