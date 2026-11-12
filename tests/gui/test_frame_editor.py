"""GUI tests of the frame editor: selection details, grips and keyboard."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from pytestqt.qtbot import QtBot

from editor_helpers import MM, editor_with, grip, item, mouse
from scanbench.domain.frame_handle import FrameHandle
from scanbench.ui.frame_editor import NO_SELECTION


def test_selection_shows_details_and_grips(tmp_path: Path, qtbot: QtBot) -> None:
    """Selecting a frame shows its values and its grips.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot)
    view = editor.view
    assert editor.details.text() == NO_SELECTION
    frame = item(view, 0)
    assert not any(h.isVisible() for h in frame.handles)
    frame.setSelected(True)
    assert editor.details.text() == "Frame 1: 100 x 70 mm, skew +0.0°, saved as framed"
    assert all(h.isVisible() for h in frame.handles) and len(frame.handles) == 9


def test_drag_grips_resize_and_rotate(tmp_path: Path, qtbot: QtBot) -> None:
    """The right grip widens the frame; the orange grip rotates it, Shift snaps.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = editor_with(tmp_path, qtbot).view
    item(view, 0).setSelected(True)
    start = grip(view, FrameHandle.RIGHT).scenePos()
    target = QPointF(start.x() + 10 * MM * view.scale_factor, start.y())
    mouse(view, QEvent.Type.MouseButtonPress, start)
    mouse(view, QEvent.Type.MouseMove, target)
    mouse(view, QEvent.Type.MouseButtonRelease, target)
    assert view.regions[0].width / MM == pytest.approx(110, abs=1.5)
    assert view.selected_index() == 0
    turn_at = grip(view, FrameHandle.ROTATE).scenePos()
    centre = item(view, 0).polygon().boundingRect().center()
    beside = QPointF(centre.x() + (centre.y() - turn_at.y()), centre.y())
    mouse(view, QEvent.Type.MouseButtonPress, turn_at)
    mouse(view, QEvent.Type.MouseButtonRelease, beside, Qt.KeyboardModifier.ShiftModifier)
    assert view.regions[0].angle == pytest.approx(90)


def test_keyboard_moves_turns_and_deletes(tmp_path: Path, qtbot: QtBot) -> None:
    """Arrow keys move by a screen pixel, +/- turn, Delete removes; others pass through.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = editor_with(tmp_path, qtbot).view
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
    item(view, 0).setSelected(True)
    press(Qt.Key.Key_Right)
    press(Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
    press(Qt.Key.Key_Plus)
    press(Qt.Key.Key_Plus)
    press(Qt.Key.Key_Minus)
    press(Qt.Key.Key_A)
    region = view.regions[0]
    pixel = max(1.0, 1 / (view.transform().m11() * view.scale_factor))
    assert region.cx == pytest.approx(before.cx + pixel)
    assert region.cy == pytest.approx(before.cy + 10 * pixel)
    view.scale(40, 40)                              # zoomed far in: one scan pixel
    press(Qt.Key.Key_Left)
    assert view.regions[0].cx == pytest.approx(region.cx - 1)
    assert region.angle == pytest.approx(0.1)
    press(Qt.Key.Key_Delete)
    assert not view.regions


def test_plain_click_still_selects_and_moves(tmp_path: Path, qtbot: QtBot) -> None:
    """A press outside the grips goes to Qt (selection, moving).

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    view = editor_with(tmp_path, qtbot).view
    centre = item(view, 0).polygon().boundingRect().center()
    mouse(view, QEvent.Type.MouseButtonPress, centre)
    mouse(view, QEvent.Type.MouseMove, QPointF(centre.x() + 5, centre.y()))
    mouse(view, QEvent.Type.MouseButtonRelease, QPointF(centre.x() + 5, centre.y()))
    assert view.selected_index() == 0
