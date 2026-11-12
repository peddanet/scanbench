"""Tests for the document and photo sessions and the settings store."""

import json
from pathlib import Path

import pytest

from fakes import FakeShell
from scan_fakes import OPTIONS, FakeScanner, page
from scenes import DPI, Placed, scan
from scanbench.application.document_session import DocumentSession
from scanbench.application.photo_session import INDEX_FILE, AlbumOptions, PhotoSession
from scanbench.domain.image_format import ImageFormat
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.scan_observer import ScanObserver

FEEDER = ScanSettings(ScanSource.ADF)


def _documents(tmp_path: Path, scanner: FakeScanner) -> DocumentSession:
    """Create a document session in a work directory.

    Args:
        tmp_path: Temporary directory of the test.
        scanner: Fake scanner.

    Returns:
        The session.
    """
    work = tmp_path / "work"
    work.mkdir()
    return DocumentSession(scanner, ImageStore(), PdfWriter(FakeShell()), work)


def test_document_editing_and_pdf(tmp_path: Path) -> None:
    """Scan, turn, move, delete and save a document.

    Args:
        tmp_path: Temporary directory of the test.
    """
    session = _documents(tmp_path, FakeScanner([page(10), page(20), page(30)]))
    added = session.scan("dev", FEEDER, OPTIONS)
    assert len(added) == 3 and added[0].dpi == 100
    session.rotate(0, -1)
    assert session.pages[0].quarter_turns == 3
    assert session.move(0, 5) == 2 and session.pages[2].quarter_turns == 3
    session.remove(1)
    rendered = session.render(tmp_path)
    assert [p.name for p in rendered] == ["page-0001.png", "page-0002.png"]
    assert ImageStore().load_rgb(rendered[1]).shape == (60, 80, 3)
    pdf = session.save_pdf(tmp_path / "doc.pdf", PdfQuality.ORIGINAL)
    assert pdf.read_bytes().startswith(b"%PDF")
    session.clear()
    assert not session.pages


def test_manual_duplex_merge(tmp_path: Path) -> None:
    """Fronts and reversed backs are merged into reading order.

    Args:
        tmp_path: Temporary directory of the test.
    """
    scanner = FakeScanner([page(c) for c in (1, 3, 5, 6, 4, 2)])
    session = _documents(tmp_path, scanner)
    with pytest.raises(ScanError, match="front sides"):
        session.merge_last_batches()
    session.scan("dev", FEEDER, OPTIONS)
    session.scan("dev", FEEDER, OPTIONS)
    session.merge_last_batches()
    store = ImageStore()
    colours = [int(store.load_rgb(p.path)[40, 40, 0]) for p in session.pages]
    assert colours == [1, 2, 3, 4, 5, 6]
    scanner.feeder_pages = 2
    session.scan("dev", FEEDER, OPTIONS)
    with pytest.raises(ScanError, match="6 front sides but 2"):
        session.merge_last_batches()


def _photos(tmp_path: Path, placed: list[Placed]) -> PhotoSession:
    """Create a photo session whose scanner returns a synthetic album page.

    Args:
        tmp_path: Temporary directory of the test.
        placed: Photos on the page.

    Returns:
        The session.
    """
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return PhotoSession(FakeScanner([scan(placed)], DPI), PhotoDetector(), ImageStore(), work)


def test_photo_scan_confirm_and_numbering(tmp_path: Path) -> None:
    """Photos are detected, snapped, saved with continuing numbers and indexed.

    Args:
        tmp_path: Temporary directory of the test.
    """
    session = _photos(tmp_path, [Placed(150, 100, 80, 60, 1.0), Placed(100, 150, 80, 200)])
    album = tmp_path / "album"
    album.mkdir()
    (album / "photo-0007.jpg").write_bytes(b"")
    (album / "other.png").write_bytes(b"")
    current = session.scan("dev", ScanSettings(), OPTIONS)
    assert len(current.regions) == 2
    assert round(current.regions[0].width / DPI * 25.4) == 150     # snapped to 10 x 15
    current.regions[1] = current.regions[1].turned(1)
    written = session.accept(AlbumOptions(album, ImageFormat.JPEG, keep_scans=True))
    assert [p.name for p in written] == ["photo-0008.jpg", "photo-0009.jpg"]
    assert (album / "scans" / "scan-0008.png").exists()
    index = json.loads((album / INDEX_FILE).read_text(encoding="utf-8"))
    assert index[1]["region"]["quarter_turns"] == 1 and index[0]["scan"] == "scans/scan-0008.png"
    assert session.current is None
    with pytest.raises(ScanError, match="no scan"):
        session.accept(AlbumOptions(album))


def test_photo_preview_then_area_scan(tmp_path: Path) -> None:
    """A low-resolution preview finds the frames; the area scan keeps them.

    Args:
        tmp_path: Temporary directory of the test.
    """
    truth = Placed(150, 100, 100, 200, 1.0)
    scanner = FakeScanner([scan([truth])], DPI)
    session = PhotoSession(scanner, PhotoDetector(), ImageStore(), tmp_path)
    with pytest.raises(ScanError, match="preview"):
        session.scan_area("dev", ScanSettings(resolution=100), OPTIONS)
    reports: list[float] = []
    preview = session.preview("dev", ScanSettings(resolution=100), OPTIONS,
                              observer=ScanObserver(progress=lambda r: reports.append(r.percent)))
    assert preview.preview and preview.dpi == 75 and len(preview.regions) == 1 and reports
    with pytest.raises(ScanError, match="preview"):
        session.accept(AlbumOptions(tmp_path / "album"))
    full = session.scan_area("dev", ScanSettings(resolution=100), OPTIONS)
    area = scanner.requests[-1].area
    assert area is not None and area.width < 170 and area.height < 120
    assert not full.preview and full.dpi == DPI
    region = full.regions[0]
    mm = DPI / 25.4
    assert abs(region.cx / mm + area.left - truth.cx_mm) < 2
    assert abs(region.cy / mm + area.top - truth.cy_mm) < 2
    assert abs(region.width / mm - 150) < 2 and abs(region.angle - 1.0) < 0.5
    assert len(session.accept(AlbumOptions(tmp_path / "album"))) == 1


def test_photo_detect_discard_and_broken_index(tmp_path: Path) -> None:
    """Detection without snapping, discarding and a damaged index file.

    Args:
        tmp_path: Temporary directory of the test.
    """
    session = _photos(tmp_path, [Placed(120, 80, 80, 60)])
    current = session.scan("dev", ScanSettings(), OPTIONS, snap=0.0)
    again = session.detect(current.path, current.dpi, snap=0.0)
    assert len(again.regions) == 1
    session.discard()
    assert session.current is None
    album = tmp_path / "album"
    album.mkdir()
    (album / INDEX_FILE).write_text("{broken", encoding="utf-8")
    session.detect(current.path, current.dpi)
    session.accept(AlbumOptions(album))
    assert (album / f"{INDEX_FILE}.broken").exists()
    assert len(json.loads((album / INDEX_FILE).read_text(encoding="utf-8"))) == 1
    assert PhotoSession.next_number(tmp_path / "none") == 1
