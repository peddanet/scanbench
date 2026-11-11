"""Write scanned pages into a PDF, optionally shrunk with Ghostscript."""

import shutil
import tempfile
from pathlib import Path

import img2pdf

from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_error import ScanError
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell


class PdfWriter:
    """Create PDF files from page images (Template Method in two steps).

    Step one always embeds the page images losslessly with ``img2pdf``
    (PNG data is copied, not re-encoded). Step two runs only for a reduced
    quality: Ghostscript ``pdfwrite`` with ``-dPDFSETTINGS`` re-encodes the
    images of that lossless original, never of an already reduced file. If
    the reduced file is not smaller, the original is kept.
    """

    def __init__(self, shell: Shell) -> None:
        """Store the runner for Ghostscript.

        Args:
            shell: Command runner.
        """
        self._shell = shell

    def _shrink(self, original: Path, target: Path, setting: str) -> None:
        """Run Ghostscript with a PDFSETTINGS preset.

        Args:
            original: Lossless PDF.
            target: Reduced PDF to write.
            setting: Preset such as ``/ebook``.

        Raises:
            ScanError: If Ghostscript is missing or fails.
        """
        try:
            result = self._shell.run(
                "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.7",
                f"-dPDFSETTINGS={setting}", "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
                f"-sOutputFile={target}", str(original), check=False)
        except UpdateError as exc:
            raise ScanError(f"{exc}; install the package ghostscript") from exc
        if not result.ok or not target.exists():
            raise ScanError(f"Ghostscript failed: {result.stderr.strip()[-200:]}")

    def write(self, pages: list[Path], target: Path, quality: PdfQuality) -> Path:
        """Write the pages in order into one PDF.

        Args:
            pages: Page images with their resolution stored in the file.
            target: PDF file to write; replaced if it exists.
            quality: Wanted reduction.

        Returns:
            The target.

        Raises:
            ScanError: If there are no pages or a step fails.
        """
        if not pages:
            raise ScanError("there are no pages to save")
        with tempfile.TemporaryDirectory(prefix="scanbench-pdf-") as tmp:
            original = Path(tmp) / "original.pdf"
            try:
                original.write_bytes(img2pdf.convert([str(p) for p in pages]))
            except (OSError, ValueError, img2pdf.ImageOpenError, img2pdf.AlphaChannelError,
                    img2pdf.UnsupportedColorspaceError) as exc:
                raise ScanError(f"cannot build the PDF: {exc}") from exc
            result = original
            if quality.setting is not None:
                reduced = Path(tmp) / "reduced.pdf"
                self._shrink(original, reduced, quality.setting)
                if reduced.stat().st_size < original.stat().st_size:
                    result = reduced
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(result, target)
        return target
