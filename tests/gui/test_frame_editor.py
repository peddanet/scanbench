"""GUI tests of the frame editor: selection details, grips and keyboard."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from scan_fakes import write_png
from scenes import DPI, Placed, scan
from scanbench.domain.frame_handle import FrameHandle
from scanbench.ui.frame_editor import NO_SELECTION, FrameEditor
from scanbench.ui.frame_items import HandleItem, RegionItem
from scanbench.ui.region_view import RegionView

MM = DPI / 25.4


def _editor(tmp_path: Path, qtbot: QtBot) -> FrameEditor:
    """Show a page with one 100 x 70 mm photo.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.

    Returns:
        The editor.
    """
    editor = FrameEditor("hint")
    qtbot.addWidget(editor)
    editor.resize(700, 900)
    editor.show()
    path = write_png(tmp_path / "page.png", scan([Placed(100, 70, 80, 60)]), DPI)
    editor.show_scan(path, DPI, [Placed(100, 70, 80, 60).region()])
    return editor


def _item(view: RegionView, index: int) -> RegionItem:
    """Return the item of a frame.

    Args:
        view: The view.
        index: Frame index.

    Returns:
        The item.
    """
    return next(i for i in view.scene().items() if isinstance(i, RegionItem) and i.index == index)


def _mouse(view: RegionView, kind: QEvent.Type, scene: QPointF,
           modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> None:
    """Send a left-button mouse event at a scene point.

    Args:
        view: The view.
        kind: Press, move or release.
        scene: Position in scene coordinates.
        modifiers: Keyboard modifiers.
    """
    local = QPointF(view.mapFromScene(scene))
    event = QMouseEvent(kind, local, local, Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, modifiers)
    {QEvent.Type.MouseButtonPress: view.mousePressEvent,
     QEvent.Type.MouseMove: view.mouseMoveEvent,
     QEvent.Type.MouseButtonRelease: view.mouseReleaseEvent}[kind](event)


def _grip(view: RegionView, handle: FrameHandle) -> HandleItem:
    """Return a grip of the selected frame.

    Args:
        view: The view.
        handle: Which grip.

    Returns:
        The grip item.
    """
    return next(h for h in _item(view, view.selected_index()).handles if h.handle is handle)


def test_selection_shows_details_and_grips(tmp_path: Path, qtbot: QtBot) -> None:
    """Selecting a frame shows its values and its grips.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = _editor(tmp_path, qtbot)
    view = editor.view
    assert editor.details.text() == NO_SELECTION
    item = _item(view, 0)
    assert not any(h.isVisible() for h in item.handles)
    item.setSelected(True)
    assert editor.details.text() == "Frame 1: 100 x 70 mm, skew +0.0°, saved as framed"
    assert all(h.isVisible() for h in item.handles) and len(item.handles) == 9


def test_drag_grips_resize_and_rotate(tmp_path: Path, qtbot: QtBot) -> None:
    """The right grip widens the frame; the orange grip rotates it, Shift snaps.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = _editor(tmp_path, qtbot).view
    _item(view, 0).setSelected(True)
    start = _grip(view, FrameHandle.RIGHT).scenePos()
    target = QPointF(start.x() + 10 * MM * view.scale_factor, start.y())
    _mouse(view, QEvent.Type.MouseButtonPress, start)
    _mouse(view, QEvent.Type.MouseMove, target)
    _mouse(view, QEvent.Type.MouseButtonRelease, target)
    assert view.regions[0].width / MM == pytest.approx(110, abs=1.5)
    assert view.selected_index() == 0
    grip = _grip(view, FrameHandle.ROTATE).scenePos()
    centre = _item(view, 0).polygon().boundingRect().center()
    beside = QPointF(centre.x() + (centre.y() - grip.y()), centre.y())
    _mouse(view, QEvent.Type.MouseButtonPress, grip)
    _mouse(view, QEvent.Type.MouseButtonRelease, beside, Qt.KeyboardModifier.ShiftModifier)
    assert view.regions[0].angle == pytest.approx(90)


def test_keyboard_moves_turns_and_deletes(tmp_path: Path, qtbot: QtBot) -> None:
    """Arrow keys move, +/- turn, Delete removes; other keys pass through.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = _editor(tmp_path, qtbot).view
    before = view.regions[0]

    def press(key: Qt.Key, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) \
            -> None:
        """Send a key press to the view.

        Args:
            key: The key.
            modifiers: Keyboard modifiers.
        """
        view.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, modifiers))
    press(Qt.Key.Key_Right)
    assert view.regions[0] == before            # nothing selected: no change
    _item(view, 0).setSelected(True)
    press(Qt.Key.Key_Right)
    press(Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    press(Qt.Key.Key_Plus)
    press(Qt.Key.Key_Plus)
    press(Qt.Key.Key_Minus)
    press(Qt.Key.Key_A)
    region = view.regions[0]
    assert region.cx == pytest.approx(before.cx + MM)
    assert region.cy == pytest.approx(before.cy + 10 * MM)
    assert region.angle == pytest.approx(0.1)
    press(Qt.Key.Key_Delete)
    assert not view.regions


def test_plain_click_still_selects_and_moves(tmp_path: Path, qtbot: QtBot) -> None:
    """A press outside the grips goes to Qt (selection, moving).

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = _editor(tmp_path, qtbot).view
    centre = _item(view, 0).polygon().boundingRect().center()
    _mouse(view, QEvent.Type.MouseButtonPress, centre)
    _mouse(view, QEvent.Type.MouseMove, QPointF(centre.x() + 5, centre.y()))
    _mouse(view, QEvent.Type.MouseButtonRelease, QPointF(centre.x() + 5, centre.y()))
    assert view.selected_index() == 0
