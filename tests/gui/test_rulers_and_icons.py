"""GUI tests of the rulers (guides pulled out of them) and the tool symbols."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from editor_helpers import editor_with
from scanbench.ui.frame_editor import FrameEditor
from scanbench.ui.guide_items import GuideItem
from scanbench.ui.ruler import Ruler
from scanbench.ui.tool_icons import DRAWINGS, THEME_NAMES, drawn, tool_icon


def _rulers(editor: FrameEditor) -> tuple[Ruler, Ruler]:
    """Return the top and the left ruler of an editor.

    Args:
        editor: The frame editor.

    Returns:
        Top ruler, left ruler.
    """
    rulers = editor.findChildren(Ruler)
    top = next(r for r in rulers if r.horizontal)
    left = next(r for r in rulers if not r.horizontal)
    return top, left


def _send(widget: Ruler, kind: QEvent.Type, global_point: QPoint) -> None:
    """Send a left-button mouse event with a screen position to a ruler.

    Args:
        widget: The ruler.
        kind: Press, move or release.
        global_point: Position on the screen.
    """
    local = QPointF(widget.mapFromGlobal(global_point))
    buttons = (Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease
               else Qt.MouseButton.LeftButton)
    event = QMouseEvent(kind, local, QPointF(global_point), Qt.MouseButton.LeftButton,
                        buttons, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(widget, event)


def _guides(editor: FrameEditor) -> list[GuideItem]:
    """Return the guide lines of the editor.

    Args:
        editor: The frame editor.

    Returns:
        The guides.
    """
    return [i for i in editor.view.scene().items() if isinstance(i, GuideItem)]


def test_pull_guides_out_of_the_rulers(tmp_path: Path, qtbot: QtBot) -> None:
    """Dragging from a ruler into the scan leaves a guide; outside it does not.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    editor = editor_with(tmp_path, qtbot)
    top, left = _rulers(editor)
    viewport = editor.view.viewport()
    target = viewport.mapToGlobal(QPoint(150, 220))
    _send(top, QEvent.Type.MouseButtonPress, top.mapToGlobal(QPoint(150, 5)))
    _send(top, QEvent.Type.MouseMove, target)
    _send(top, QEvent.Type.MouseButtonRelease, target)
    guides = _guides(editor)
    assert len(guides) == 1 and guides[0].horizontal
    assert guides[0].pos().y() == pytest.approx(editor.view.mapToScene(QPoint(150, 220)).y())
    _send(left, QEvent.Type.MouseButtonPress, left.mapToGlobal(QPoint(5, 100)))
    _send(left, QEvent.Type.MouseButtonRelease, left.mapToGlobal(QPoint(5, 100)))  # on ruler
    assert len(_guides(editor)) == 1
    _send(left, QEvent.Type.MouseButtonPress, left.mapToGlobal(QPoint(5, 100)))
    _send(left, QEvent.Type.MouseButtonRelease, viewport.mapToGlobal(QPoint(300, 100)))
    assert sorted(g.horizontal for g in _guides(editor)) == [False, True]
    _send(left, QEvent.Type.MouseButtonRelease, viewport.mapToGlobal(QPoint(1, 1)))  # no drag
    top.grab()                                       # paints ticks and labels
    left.grab()
    assert top.sizeHint().height() == left.sizeHint().width()


def test_rulers_without_a_scan(qtbot: QtBot) -> None:
    """Without a scan the rulers are empty and pull out nothing.

    Args:
        qtbot: pytest-qt helper.
    """
    editor = FrameEditor("hint")
    qtbot.addWidget(editor)
    editor.show()
    top, _left = _rulers(editor)
    top.grab()
    _send(top, QEvent.Type.MouseButtonPress, top.mapToGlobal(QPoint(10, 5)))
    assert not _guides(editor)


def test_tool_symbols(qtbot: QtBot) -> None:
    """Every tool has a symbol; theme names fall back to drawn ones.

    Args:
        qtbot: pytest-qt helper.
    """
    del qtbot
    editor_keys = set(DRAWINGS)
    assert set(THEME_NAMES) <= editor_keys
    for key in editor_keys:
        assert not drawn(key).isNull() and not tool_icon(key).isNull()
