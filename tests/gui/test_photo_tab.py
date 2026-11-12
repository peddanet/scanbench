"""GUI tests of the photo tab and the frame editor."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from pytestqt.qtbot import QtBot

from gui_helpers import Answers, context, idle, trigger
from scan_fakes import FakeScanner
from scenes import DPI, Placed, scan
from scanbench.application.photo_session import PhotoScan, PhotoSession
from scanbench.domain.print_job import PrintJob
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_progress import ScanProgress
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.ui.frame_editor import FrameEditor
from scanbench.ui.photo_tab import PhotoTab
from scanbench.ui.progress_panel import ProgressPanel
from scanbench.ui.frame_items import RegionItem
from scanbench.ui.region_menus import RegionMenus
from scanbench.ui.region_view import RegionView

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
    tab = PhotoTab(context(qtbot, scanner, answers), session)
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


def _scan(qtbot: QtBot, tab: PhotoTab) -> None:
    """Make a preview scan, then scan the photos.

    Args:
        qtbot: pytest-qt helper.
        tab: The tab.
    """
    _run(qtbot, tab, "preview")
    _run(qtbot, tab, "area")


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
    _scan(qtbot, tab)
    assert len(tab.editor.view.regions) == 2 and tab.pending() is not None
    _edit_frames(tab.editor.view)
    assert tab.buttons["confirm"].text() == "Confirm 3 photo(s)"
    _run(qtbot, tab, "confirm")
    assert [p.name for p in tab.saved] == ["photo-0001.png", "photo-0002.png",
                                           "photo-0003.png"]
    assert tab.pending() is None and RegionMenus(tab.editor.view).menu_at(QPointF(1, 1)) is None
    _run(qtbot, tab, "print")
    assert tab.editor.hint.text().startswith("Saved 3 photo(s)")


def test_drag_and_context_menu_event(tmp_path: Path, qtbot: QtBot) -> None:
    """A dragged frame moves; right-click opens a menu.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _tab(tmp_path, qtbot, Answers())
    _scan(qtbot, tab)
    view = tab.editor.view
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
    _scan(qtbot, tab)
    tab.form.snap.setChecked(False)
    _run(qtbot, tab, "detect")
    assert len(tab.editor.view.regions) == 2
    tab.buttons["discard"].click()
    assert tab.pending() is None and not tab.editor.view.regions
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
    _scan(qtbot, tab)
    _run(qtbot, tab, "confirm")
    assert messages[-1].startswith("Error:") and tab.pending() is not None


def test_preview_then_scan_photos(tmp_path: Path, qtbot: QtBot) -> None:
    """Preview finds frames; 'Scan photos' scans only their area and allows confirming.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _tab(tmp_path, qtbot, Answers(None, tmp_path / "album"))
    tab.form.album.setText(str(tmp_path / "album"))
    progress = tab._ctx.progress  # pylint: disable=protected-access
    assert tab.buttons["preview"].isEnabled() and not tab.buttons["area"].isEnabled()
    _run(qtbot, tab, "preview")
    current = tab.pending()
    assert current is not None and current.preview and len(current.regions) == 2
    assert tab.buttons["area"].isEnabled() and not tab.buttons["confirm"].isEnabled()
    assert tab.editor.hint.text().startswith("Preview at 75 dpi")
    assert progress.meter.value() == 100 and progress.isHidden()
    _run(qtbot, tab, "area")
    current = tab.pending()
    assert current is not None and not current.preview and current.dpi == DPI
    assert tab.buttons["confirm"].isEnabled() and not tab.buttons["preview"].isEnabled()
    _run(qtbot, tab, "confirm")
    assert len(tab.saved) == 2


def test_progress_panel_cancel(qtbot: QtBot) -> None:
    """The panel shows a busy bar, then percent and text; Cancel sets the event.

    Args:
        qtbot: pytest-qt helper.
    """
    panel = ProgressPanel()
    qtbot.addWidget(panel)
    event = panel.start("Scanning ...")
    assert panel.meter.maximum() == 0 and panel.cancel_button.isEnabled()
    panel.update_progress(ScanProgress(1, 1, 40.0, 4.0))
    assert panel.meter.value() == 40 and "Page 1 of 1" in panel.label.text()
    panel.cancel_button.click()
    assert event.is_set() and panel.label.text() == "Cancelling ..."
    assert not panel.cancel_button.isEnabled()
    panel.start("Saving ...", cancellable=False)
    assert not panel.cancel_button.isVisible() or not panel.cancel_button.isEnabled()
    panel.finish()
    assert panel.isHidden()


def test_cancel_saving(tmp_path: Path, qtbot: QtBot,
                       monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancel while saving keeps the saved photos; the other frames wait.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        monkeypatch: pytest helper.
    """
    tab = _tab(tmp_path, qtbot, Answers(None, tmp_path / "album"))
    tab.form.album.setText(str(tmp_path / "album"))
    messages: list[str] = []
    tab.message.connect(messages.append)
    progress = tab._ctx.progress  # pylint: disable=protected-access
    _scan(qtbot, tab)
    original_save = ImageStore.save

    def save_then_cancel(*args: object) -> Path:
        """Save one photo, then press Cancel.

        Args:
            *args: Arguments of ``save``.

        Returns:
            The saved file.
        """
        result = original_save(*args)  # type: ignore[arg-type]
        progress.cancel()
        return result
    monkeypatch.setattr(ImageStore, "save", staticmethod(save_then_cancel))
    tab.buttons["confirm"].click()
    assert not tab.cancel_button.isHidden()
    idle(qtbot, tab._ctx.runner)  # pylint: disable=protected-access
    assert len(tab.saved) == 1 and tab.buttons["confirm"].text() == "Confirm 1 photo(s)", messages
    assert messages[-1] == "Cancelled - Saved 1 photo(s); 1 still waiting"
    assert tab.cancel_button.isHidden()
    monkeypatch.setattr(ImageStore, "save", staticmethod(original_save))
    _run(qtbot, tab, "confirm")
    assert len(tab.saved) == 1 and tab.pending() is None


def test_cancel_detection_and_scan(tmp_path: Path, qtbot: QtBot,
                                   monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancel keeps the old frames after a detection and reports a stopped scan.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        monkeypatch: pytest helper.
    """
    tab = _tab(tmp_path, qtbot, Answers(None, tmp_path / "album"))
    messages: list[str] = []
    tab.message.connect(messages.append)
    progress = tab._ctx.progress  # pylint: disable=protected-access
    _scan(qtbot, tab)
    before = tab.pending()
    session = tab._session  # pylint: disable=protected-access
    original_detect = session.detect

    def detect_then_cancel(*args: object) -> PhotoScan:
        """Detect, then press Cancel.

        Args:
            *args: Arguments of ``detect``.

        Returns:
            The new proposal.
        """
        result = original_detect(*args)  # type: ignore[arg-type]
        progress.cancel()
        return result
    monkeypatch.setattr(session, "detect", detect_then_cancel)
    _run(qtbot, tab, "detect")
    assert tab.pending() is before and messages[-1] == "Cancelled; the previous frames stay"
    tab.discard()
    scanner = session._scanner  # pylint: disable=protected-access

    def stopped(*_args: object, **_kwargs: object) -> list[Path]:
        """Behave like a scan stopped by Cancel.

        Args:
            *_args: Ignored.
            **_kwargs: Ignored.

        Raises:
            ScanError: Always.
        """
        progress.cancel()
        raise ScanError("scan cancelled")
    monkeypatch.setattr(scanner, "scan", stopped)
    _run(qtbot, tab, "preview")
    assert messages[-1] == "Cancelled"


def test_escape_cancels_and_editor_escape_only_while_drawing(qtbot: QtBot) -> None:
    """Esc of the progress panel is active during a cancellable job only.

    Args:
        qtbot: pytest-qt helper.
    """
    panel = ProgressPanel()
    qtbot.addWidget(panel)
    event = panel.start("Scanning ...")
    assert panel.escape.isEnabled()
    panel.escape.activated.emit()
    assert event.is_set() and not panel.escape.isEnabled()
    panel.start("Saving ...", cancellable=False)
    assert not panel.escape.isEnabled()
    panel.finish()
    editor = FrameEditor("hint")
    qtbot.addWidget(editor)
    stop = editor.tools.actions["stop_draw"]
    assert not stop.isEnabled()
    editor.set_draw_mode(True)
    assert stop.isEnabled()
    stop.trigger()
    assert not editor.view.mode.draw and not stop.isEnabled()
