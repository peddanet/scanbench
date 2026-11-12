"""Helpers for GUI tests of the frame editor."""

from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from pytestqt.qtbot import QtBot

from scan_fakes import write_png
from scenes import DPI, Placed, scan
from scanbench.domain.frame_handle import FrameHandle
from scanbench.ui.frame_editor import FrameEditor
from scanbench.ui.frame_items import HandleItem, RegionItem
from scanbench.ui.region_view import RegionView

MM = DPI / 25.4


def editor_with(tmp_path: Path, qtbot: QtBot, frames: list[Placed] | None = None) -> FrameEditor:
    """Show a page with photos and their frames.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        frames: Photos on the page; default one 100 x 70 mm photo.

    Returns:
        The editor.
    """
    frames = frames or [Placed(100, 70, 80, 60)]
    editor = FrameEditor("hint")
    qtbot.addWidget(editor)
    editor.resize(700, 900)
    editor.show()
    path = write_png(tmp_path / "page.png", scan(frames), DPI)
    editor.show_scan(path, DPI, [f.region() for f in frames])
    return editor


def item(view: RegionView, index: int) -> RegionItem:
    """Return the item of a frame.

    Args:
        view: The view.
        index: Frame index.

    Returns:
        The item.
    """
    return next(i for i in view.scene().items() if isinstance(i, RegionItem) and i.index == index)


def mouse(view: RegionView, kind: QEvent.Type, scene: QPointF,
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


def grip(view: RegionView, handle: FrameHandle) -> HandleItem:
    """Return a grip of the selected frame.

    Args:
        view: The view.
        handle: Which grip.

    Returns:
        The grip item.
    """
    return next(h for h in item(view, view.selected_index()).handles if h.handle is handle)
