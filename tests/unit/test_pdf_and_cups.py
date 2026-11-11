"""Tests for the PDF writer and the CUPS client."""

import shutil
from pathlib import Path

import numpy as np
import pytest

from fakes import FakeShell, failed, ok
from scan_fakes import write_png
from scanbench.domain.command_result import CommandResult
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_error import ScanError
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.infrastructure.shell import Shell

HAS_GS = shutil.which("gs") is not None


def _pages(directory: Path, count: int) -> list[Path]:
    """Write noisy colour pages (they compress badly, so reduction shows).

    Args:
        directory: Target directory.
        count: Number of pages.

    Returns:
        The page files.
    """
    rng = np.random.default_rng(1)
    return [write_png(directory / f"p{n}.png",
                      rng.integers(0, 255, (600, 420, 3), dtype=np.uint8), 150)
            for n in range(count)]


def test_original_pdf(tmp_path: Path) -> None:
    """Without reduction the pages are embedded losslessly, A4-sized by resolution.

    Args:
        tmp_path: Temporary directory of the test.
    """
    target = PdfWriter(FakeShell()).write(_pages(tmp_path, 2), tmp_path / "out" / "a.pdf",
                                          PdfQuality.ORIGINAL)
    data = target.read_bytes()
    assert data.startswith(b"%PDF") and data.count(b"/Type /Page\n") + \
        data.count(b"/Type /Page ") + data.count(b"/Type/Page") >= 1


@pytest.mark.skipif(not HAS_GS, reason="ghostscript not installed")
def test_reduced_pdf_is_smaller(tmp_path: Path) -> None:
    """The screen preset shrinks a noisy scan considerably.

    Args:
        tmp_path: Temporary directory of the test.
    """
    pages = _pages(tmp_path, 1)
    writer = PdfWriter(Shell(tmp_path))
    original = writer.write(pages, tmp_path / "o.pdf", PdfQuality.ORIGINAL)
    reduced = writer.write(pages, tmp_path / "r.pdf", PdfQuality.SCREEN)
    assert reduced.stat().st_size < original.stat().st_size / 2


def test_reduction_keeps_original_if_not_smaller(tmp_path: Path) -> None:
    """A "reduced" file that is larger is not used.

    Args:
        tmp_path: Temporary directory of the test.
    """
    class GrowingShell(FakeShell):
        """Writes a large file instead of running Ghostscript."""

        def run(self, *argv: str, check: bool = True,
                stdin: str | None = None) -> CommandResult:
            """Write a big output file.

            Args:
                *argv: Command.
                check: Ignored.
                stdin: Ignored.

            Returns:
                Success.
            """
            output = next(a for a in argv if a.startswith("-sOutputFile="))
            Path(output.split("=", 1)[1]).write_bytes(b"x" * 10_000_000)
            return super().run(*argv, check=check, stdin=stdin)

    target = PdfWriter(GrowingShell()).write(_pages(tmp_path, 1), tmp_path / "a.pdf",
                                             PdfQuality.EBOOK)
    assert target.read_bytes().startswith(b"%PDF")


def test_pdf_errors(tmp_path: Path) -> None:
    """No pages, broken images, failing or missing Ghostscript.

    Args:
        tmp_path: Temporary directory of the test.
    """
    writer = PdfWriter(FakeShell(script={("gs",): [failed("gs broke")]}))
    with pytest.raises(ScanError, match="no pages"):
        writer.write([], tmp_path / "a.pdf", PdfQuality.ORIGINAL)
    (tmp_path / "bad.png").write_text("no image", encoding="utf-8")
    with pytest.raises(ScanError, match="cannot build"):
        writer.write([tmp_path / "bad.png"], tmp_path / "a.pdf", PdfQuality.ORIGINAL)
    pages = _pages(tmp_path, 1)
    with pytest.raises(ScanError, match="gs broke"):
        writer.write(pages, tmp_path / "a.pdf", PdfQuality.PRINTER)
    missing = PdfWriter(Shell(tmp_path, which=lambda _n: None))
    with pytest.raises(ScanError, match="ghostscript"):
        missing.write(pages, tmp_path / "a.pdf", PdfQuality.PREPRESS)


def test_cups_printers_options_and_print(tmp_path: Path) -> None:
    """Printers with default, driver options and the lp command line.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shell = FakeShell(script={
        ("lpstat", "-e"): [ok("MX920\nOffice\n")],
        ("lpstat", "-d"): [ok("system default destination: Office\n")],
        ("lpoptions",): [ok("InputSlot/Paper Source: *Auto PhotoTray\n")],
        ("lp",): [ok("request id is MX920-17 (1 file(s))\n"), ok("")]})
    cups = CupsClient(shell)
    printers = cups.printers()
    assert [(p.name, p.is_default) for p in printers] == [("MX920", False), ("Office", True)]
    assert cups.options("MX920")[0].choices == ("Auto", "PhotoTray")
    photo = tmp_path / "photo.png"
    job = cups.print_files("MX920", [photo], 2, {"InputSlot": "PhotoTray", "fit-to-page": ""})
    assert job == "MX920-17"
    assert shell.calls[-1] == ("lp", "-d", "MX920", "-n", "2", "-o", "InputSlot=PhotoTray",
                               "-o", "fit-to-page", "--", str(photo))
    assert cups.print_files("MX920", [photo], 0, {}) == "submitted"


def test_cups_errors(tmp_path: Path) -> None:
    """Missing programs, failures and empty jobs.

    Args:
        tmp_path: Temporary directory of the test.
    """
    with pytest.raises(ScanError, match="cups-client"):
        CupsClient(Shell(tmp_path, which=lambda _n: None)).printers()
    broken = CupsClient(FakeShell(script={("lpstat",): [failed("scheduler is not running")]}))
    with pytest.raises(ScanError, match="scheduler"):
        broken.printers()
    with pytest.raises(ScanError, match="nothing to print"):
        broken.print_files("x", [], 1, {})
    none = CupsClient(FakeShell(script={("lpstat", "-d"): [ok("no system default destination")]}))
    assert not none.printers()
