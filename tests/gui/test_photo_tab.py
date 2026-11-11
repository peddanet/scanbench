"""GUI tests of the photo tab and the frame editor."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from gui_helpers import Answers, context, idle, trigger
from scan_fakes import FakeScanner
from scenes import DPI, Placed, scan
from scanbench.application.photo_session import PhotoSession
from scanbench.domain.print_job import PrintJob
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.settings_store import SettingsStore
from scanbench.ui.photo_tab import PhotoTab
from scanbench.ui.region_view import RegionItem, RegionMenus, RegionView

PAGE = [Placed(150, 100, 80, 60, 1.0), Placed(100, 150, 80, 200)]
"""A landscape and a portrait 10 x 15 photo."""


def _tab(tmp_path: Path, qtbot: QtBot, answers: Answers) -> PhotoTab:
    """Create a photo tab whose scanner returns PAGE.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        answers: Dialog answers.

    Returns:
        The tab.
    """
    scanner = FakeScanner([scan(PAGE)], DPI)
    session = PhotoSession(scanner, PhotoDetector(), ImageStore(), tmp_path)
    tab = PhotoTab(context(qtbot, scanner, answers), session,
                   SettingsStore(tmp_path / "settings.json"))
    qtbot.addWidget(tab)
    tab.resize(1000, 800)
    return tab


def _run(qtbot: QtBot, tab: PhotoTab, button: str) -> None:
    """Press a button and wait for the job.

    Args:
        qtbot: pytest-qt helper.
        tab: The tab.
        button: Button key.
    """
    tab.buttons[button].click()
    idle(qtbot, tab._ctx.runner)  # pylint: disable=protected-access


def _edit_frames(view: RegionView) -> None:
    """Use every frame command of the context menus.

    Args:
        view: The frame editor showing PAGE.
    """
    menus = RegionMenus(view)
    for text in ("Rotate 90° clockwise", "Rotate 90° counter-clockwise", "Rotate 180°",
                 "Align horizontally (remove skew)"):
        menus.item_menu(0)
        trigger(view, text)
    assert view.regions[0].angle == 0.0 and view.regions[0].quarter_turns == 2
    menus.item_menu(1)
    trigger(view, "13 x 18 cm")
    menus.background_menu(QPointF(50, 50))
    trigger(view, "9 x 13 cm")
    menus.background_menu(QPointF(50, 50))
    trigger(view, "Add frame: whole page")
    menus.item_menu(3)
    trigger(view, "Delete frame")


def test_scan_edit_and_confirm(tmp_path: Path, qtbot: QtBot) -> None:
    """Detected frames can be edited; confirmed photos are saved in the album.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    album = tmp_path / "album"
    tab = _tab(tmp_path, qtbot, Answers(PrintJob("MX920", 2, {}), album))
    tab.form.browse()
    assert tab.form.album.text() == str(album)
    assert tab.form.panel.resolution.currentData() == 600
    _run(qtbot, tab, "scan")
    assert len(tab.view.regions) == 2 and tab.waiting()
    _edit_frames(tab.view)
    assert tab.buttons["confirm"].text() == "Confirm 3 photo(s)"
    _run(qtbot, tab, "confirm")
    assert [p.name for p in tab.saved] == ["photo-0001.png", "photo-0002.png",
                                           "photo-0003.png"]
    assert not tab.waiting() and RegionMenus(tab.view).menu_at(QPointF(1, 1)) is None
    _run(qtbot, tab, "print")
    assert tab.info.text().startswith("Saved 3 photo(s)")


def test_drag_and_context_menu_event(tmp_path: Path, qtbot: QtBot) -> None:
    """A dragged frame moves; right-click opens a menu.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _tab(tmp_path, qtbot, Answers())
    _run(qtbot, tab, "scan")
    view = tab.view
    item = next(i for i in view.scene().items() if isinstance(i, RegionItem) and i.index == 1)
    before = view.regions[1].cx
    item.setPos(10, 0)
    view.mouseReleaseEvent(QMouseEvent(
        QEvent.Type.MouseButtonRelease, QPointF(0, 0), QPointF(0, 0), Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
    assert view.regions[1].cx == pytest.approx(before + 10 / view.scale_factor)
    centre = view.mapFromScene(item.polygon().boundingRect().center())
    assert RegionMenus(view).menu_at(QPointF(centre)) is not None
    view.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(2, 2),
                                            QPoint(2, 2)))


def test_detect_again_discard_and_cancel(tmp_path: Path, qtbot: QtBot) -> None:
    """Detect again, discard, and cancelled dialogs.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    answers = Answers()
    tab = _tab(tmp_path, qtbot, answers)
    _run(qtbot, tab, "scan")
    tab.form.snap.setChecked(False)
    _run(qtbot, tab, "detect")
    assert len(tab.view.regions) == 2
    tab.buttons["discard"].click()
    assert not tab.waiting() and not tab.view.regions
    tab.detect_again()
    tab.print_photos()
    tab.form.browse()
    assert answers.questions[-2] == "Print 0 photo(s)"


def test_save_error_keeps_scan_waiting(tmp_path: Path, qtbot: QtBot) -> None:
    """A failing save is reported and the scan stays waiting.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    tab = _tab(tmp_path, qtbot, Answers())
    messages: list[str] = []
    tab.message.connect(messages.append)
    tab.form.album.setText(str(blocker / "album"))
    _run(qtbot, tab, "scan")
    _run(qtbot, tab, "confirm")
    assert messages[-1].startswith("Error:") and tab.waiting()
