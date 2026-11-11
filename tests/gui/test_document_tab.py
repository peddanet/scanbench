"""GUI tests of the documents tab and its page list."""

from pathlib import Path

from PySide6.QtCore import QPoint
from pytestqt.qtbot import QtBot

from fakes import FakeShell
from gui_helpers import Answers, context, idle, trigger
from scan_fakes import FakeScanner, page
from scanbench.application.document_session import DocumentSession
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.print_job import PrintJob
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_source import ScanSource
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.ui.document_tab import DocumentTab


def _tab(tmp_path: Path, qtbot: QtBot, scanner: FakeScanner,
         answers: Answers) -> tuple[DocumentTab, DocumentSession, list[str]]:
    """Create a documents tab with the feeder selected.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        scanner: Fake scanner.
        answers: Dialog answers.

    Returns:
        Tab, session and the list that collects status messages.
    """
    session = DocumentSession(scanner, ImageStore(), PdfWriter(FakeShell()), tmp_path)
    tab = DocumentTab(context(qtbot, scanner, answers), session)
    qtbot.addWidget(tab)
    messages: list[str] = []
    tab.message.connect(messages.append)
    assert tab.panel.source is not None and tab.panel.source.count() == 3
    tab.panel.source.setCurrentIndex(tab.panel.source.findData(ScanSource.ADF))
    return tab, session, messages


def _scan(qtbot: QtBot, tab: DocumentTab) -> None:
    """Press Scan and wait.

    Args:
        qtbot: pytest-qt helper.
        tab: The tab.
    """
    tab.buttons["scan"].click()
    idle(qtbot, tab._ctx.runner)  # pylint: disable=protected-access


def test_scan_and_edit_pages(tmp_path: Path, qtbot: QtBot) -> None:
    """Feeder pages arrive; rotate, move, delete and context menu edit them.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    scanner = FakeScanner([page(c) for c in (10, 20, 30)])
    tab, session, _ = _tab(tmp_path, qtbot, scanner, Answers())
    _scan(qtbot, tab)
    assert tab.pages.list.count() == 3 and tab.pages.dirty
    assert scanner.requests[-1].source is ScanSource.ADF
    tab.pages.list.setCurrentRow(0)
    tab.buttons["right"].click()
    tab.buttons["down"].click()
    assert tab.pages.row() == 1 and session.pages[1].quarter_turns == 1
    tab.buttons["delete"].click()
    assert tab.pages.list.count() == 2
    tab.pages.list.setCurrentRow(0)
    assert tab.pages.context_menu(QPoint(5, 5)) is not None
    trigger(tab.pages, "Upside down (180°)")
    assert session.pages[0].quarter_turns == 2
    tab.buttons["clear"].click()
    assert tab.pages.list.count() == 0 and not tab.pages.dirty
    for command in (lambda: tab.pages.rotate(1), lambda: tab.pages.move_page(1),
                    tab.pages.delete):
        command()
    assert tab.pages.context_menu(QPoint(1, 1)) is None


def test_save_and_print(tmp_path: Path, qtbot: QtBot) -> None:
    """Save as lossless PDF and print through CUPS; cancelled dialogs do nothing.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    target = tmp_path / "out.pdf"
    answers = Answers(PrintJob("MX920", 1, {"InputSlot": "PhotoTray"}), target)
    tab, _, messages = _tab(tmp_path, qtbot, FakeScanner(), answers)
    _scan(qtbot, tab)
    tab.quality.setCurrentIndex(tab.quality.findData(PdfQuality.ORIGINAL))
    tab.buttons["save"].click()
    idle(qtbot, tab._ctx.runner)  # pylint: disable=protected-access
    assert target.exists() and not tab.pages.dirty, messages
    tab.buttons["print"].click()
    idle(qtbot, tab._ctx.runner)  # pylint: disable=protected-access
    assert messages[-1] == "Print job MX920-3 sent"
    answers.job, answers.path = None, None
    tab.print_document()
    tab.save()
    assert messages[-1] == "Print job MX920-3 sent"


def test_merge_and_errors(tmp_path: Path, qtbot: QtBot) -> None:
    """Merging needs two runs; scan errors are reported.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    scanner = FakeScanner([page(c) for c in (1, 3, 5, 6, 4, 2)])
    tab, _, messages = _tab(tmp_path, qtbot, scanner, Answers())
    _scan(qtbot, tab)
    tab.buttons["merge"].click()
    assert "front sides" in messages[-1]
    _scan(qtbot, tab)
    tab.merge()
    assert messages[-1].startswith("Front and back") and tab.pages.row() == 0

    def broken(*args: object) -> list[Path]:
        """Fail like a jammed scanner.

        Args:
            *args: Ignored.

        Raises:
            ScanError: Always.
        """
        raise ScanError(f"paper jam ({len(args)})")
    scanner.scan = broken  # type: ignore[method-assign,assignment]
    _scan(qtbot, tab)
    assert messages[-1] == "Error: paper jam (5)"
