"""Tests for streaming scans: PNM assembly, progress parsing, cancel."""

import subprocess
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image

from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_progress import ScanProgress
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.pnm_assembler import PnmAssembler
from scanbench.infrastructure.scan_observer import ScanObserver
from scanbench.infrastructure.scan_stream import ProgressParser, ScanStream
from scanbench.infrastructure.shell import Shell

FAKE = Path(__file__).resolve().parent.parent / "fake_scanimage.py"


class FakeScanimageShell(Shell):
    """Starts the fake scanimage script instead of the real program."""

    def start(self, *argv: str) -> "subprocess.Popen[bytes]":
        """Run the fake script with the given arguments.

        Args:
            *argv: Program and arguments; the program name is replaced.

        Returns:
            The process.
        """
        return subprocess.Popen([sys.executable, str(FAKE), *argv[1:]], cwd=self.cwd,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def test_pnm_assembler_formats() -> None:
    """P6, P5 and P4 streams with comments; partial rows are white."""
    colour = PnmAssembler()
    colour.feed(b"P6\n# SANE data\n2 2\n")
    assert colour.rows() == 0 and colour.image().shape == (1, 1, 3)
    colour.feed(b"255\n" + bytes([10, 20, 30]) * 2)
    assert colour.rows() == 1
    image = colour.image()
    assert image[0, 0].tolist() == [10, 20, 30] and image[1, 0].tolist() == [255, 255, 255]
    gray = PnmAssembler()
    gray.feed(b"P5 3 1 255\n" + bytes([0, 128, 255]))
    assert gray.image()[0, :, 0].tolist() == [0, 128, 255]
    line_art = PnmAssembler()
    line_art.feed(b"P4\n10 1\n" + bytes([0b10000000, 0b01000000]))
    assert line_art.image()[0, :, 0].tolist() == [0] + [255] * 8 + [0]


def test_pnm_preview_is_reduced() -> None:
    """The live preview reads every n-th row and column only."""
    big = PnmAssembler()
    big.feed(b"P6\n3200 10\n255\n" + bytes([1, 2, 3]) * 3200 * 4)
    small = big.preview(1600)
    assert small.shape == (5, 1600, 3)
    assert small[0, 0].tolist() == [1, 2, 3] and small[2, 0].tolist() == [255, 255, 255]
    grey = PnmAssembler()
    grey.feed(b"P5 4 2 255\n" + bytes([7, 8, 9, 10]))
    assert grey.preview()[0, :, 0].tolist() == [7, 8, 9, 10]
    assert PnmAssembler().preview().shape == (1, 1, 3)


def test_progress_parser() -> None:
    """Progress, page lines, other messages and partial lines."""
    parser = ProgressParser()
    parser.feed("Progress: 12.5%\rProgress: 40")
    assert parser.percent == 12.5
    parser.feed(".0%\rScanning page 2\nScanned page 1. (scanner status = 5)\nboom\n")
    assert (parser.page, parser.done, parser.percent) == (2, 1, 0.0)
    assert parser.failure() == "boom"
    assert ProgressParser().failure() == "no message"


def test_scan_progress_text() -> None:
    """Text and remaining time of progress reports."""
    report = ScanProgress(1, 1, 50.0, 10.0)
    assert report.remaining() == pytest.approx(10.0)
    assert report.text() == "Page 1 of 1 · 50 % · 0:10 · about 0:10 left"
    assert ScanProgress(3, None, 50.0, 70.0).text() == "Page 3 of ? · 50 % · 1:10"
    assert ScanProgress(1, 1, 1.0, 1.0).remaining() is None


def test_page_stream_with_progress_and_image(tmp_path: Path) -> None:
    """A streamed page arrives with progress reports and partial images.

    Args:
        tmp_path: Temporary directory of the test.
    """
    reports: list[ScanProgress] = []
    images: list[int] = []
    observer = ScanObserver(progress=reports.append,
                            image=lambda a: images.append(int((a[:, 0, 0] != 255).sum())),
                            interval=0.01)
    target = ScanStream(FakeScanimageShell(tmp_path)).page([], tmp_path / "p.png", 300,
                                                           observer)
    with Image.open(target) as picture:
        assert picture.size == (40, 30) and round(picture.info["dpi"][0]) == 300
    assert reports[-1].percent == 100.0 and len(reports) >= 3
    assert images and images[0] < 30


def test_page_stream_cancel_and_failure(tmp_path: Path) -> None:
    """Cancelling stops the scan; a failing scan reports its message.

    Args:
        tmp_path: Temporary directory of the test.
    """
    stream = ScanStream(FakeScanimageShell(tmp_path))
    observer = ScanObserver(interval=0.01)
    threading.Timer(0.12, observer.cancel.set).start()
    with pytest.raises(ScanError, match="cancelled"):
        stream.page([], tmp_path / "c.png", 300, observer)
    with pytest.raises(ScanError, match="Invalid argument"):
        stream.page(["--fail"], tmp_path / "f.png", 300, ScanObserver())
    missing = ScanStream(Shell(tmp_path, which=lambda _n: None))
    with pytest.raises(ScanError, match="sane-utils"):
        missing.page([], tmp_path / "m.png", 300, ScanObserver())


def test_batch_stream_and_cancel(tmp_path: Path) -> None:
    """Feeder pages are counted; cancelling keeps finished pages only.

    Args:
        tmp_path: Temporary directory of the test.
    """
    reports: list[ScanProgress] = []
    stream = ScanStream(FakeScanimageShell(tmp_path))
    observer = ScanObserver(progress=reports.append, interval=0.02)
    pages = stream.batch([], tmp_path, "b", observer)
    assert len(pages) == 3 and reports[-1].done_pages == 3 and reports[-1].page == 3
    observer = ScanObserver(interval=0.02)
    threading.Timer(0.25, observer.cancel.set).start()
    kept = stream.batch([], tmp_path, "c", observer)
    assert len(kept) < 3


def test_shell_start_errors(tmp_path: Path) -> None:
    """A program that cannot start raises UpdateError.

    Args:
        tmp_path: Temporary directory of the test.
    """
    with pytest.raises(UpdateError):
        Shell(tmp_path / "missing", which=lambda name: name).start("true")
    process = Shell(tmp_path).start("true")
    process.communicate()
    assert process.returncode == 0
