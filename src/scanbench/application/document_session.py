"""Use case "scan a document": collect pages, edit them, save a PDF."""

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.duplex_order import DuplexOrder
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.infrastructure.scanimage_backend import ScanimageBackend


@dataclass(frozen=True)
class Page:
    """One scanned page and how to show it.

    Attributes:
        path: Raw scan as delivered by the scanner.
        dpi: Resolution of the scan.
        quarter_turns: Clockwise 90-degree turns applied on output.
        batch: Number of the scan run that produced the page.
    """

    path: Path
    dpi: int
    quarter_turns: int = 0
    batch: int = 0


class DocumentSession:
    """Pages of the document being scanned (Command receiver of the tab).

    Pages are kept as raw scans in a work directory; rotation is stored and
    applied only on output, so editing never degrades the image. Each scan
    run is a batch; two batches can be merged when a stack was scanned
    front sides first and back sides second (manual duplex).
    """

    def __init__(self, scanner: ScanimageBackend, store: ImageStore, pdf: PdfWriter,
                 work_dir: Path) -> None:
        """Store the collaborators.

        Args:
            scanner: SANE adapter.
            store: Image file access.
            pdf: PDF writer.
            work_dir: Existing directory for the raw scans.
        """
        self._scanner = scanner
        self._store = store
        self._pdf = pdf
        self._work_dir = work_dir
        self._runs = 0
        self.pages: list[Page] = []

    def scan(self, device: str, settings: ScanSettings, options: DeviceOptions) -> list[Page]:
        """Scan one flatbed page or the whole feeder and append the pages.

        Args:
            device: SANE device name.
            settings: Wanted settings.
            options: What the device offers.

        Returns:
            The new pages.
        """
        self._runs += 1
        paths = self._scanner.scan(device, settings, options, self._work_dir,
                                   f"scan{self._runs:03d}")
        added = [Page(p, self._store.resolution(p, settings.resolution), 0, self._runs)
                 for p in paths]
        self.pages.extend(added)
        return added

    def rotate(self, index: int, steps: int) -> None:
        """Turn a page by quarter turns.

        Args:
            index: Page index.
            steps: +1 clockwise, -1 counter-clockwise, 2 upside down.
        """
        page = self.pages[index]
        self.pages[index] = replace(page, quarter_turns=(page.quarter_turns + steps) % 4)

    def remove(self, index: int) -> None:
        """Delete a page.

        Args:
            index: Page index.
        """
        del self.pages[index]

    def move(self, index: int, delta: int) -> int:
        """Move a page up or down.

        Args:
            index: Page index.
            delta: -1 to move towards the start, +1 towards the end.

        Returns:
            The new index of the page.
        """
        target = min(max(index + delta, 0), len(self.pages) - 1)
        self.pages.insert(target, self.pages.pop(index))
        return target

    def clear(self) -> None:
        """Forget all pages."""
        self.pages.clear()

    def merge_last_batches(self) -> None:
        """Interleave the last two batches as fronts and reversed backs.

        Raises:
            ScanError: If there are not two batches or their sizes differ.
        """
        batches = sorted({p.batch for p in self.pages})
        if len(batches) < 2:
            raise ScanError("scan the front sides and then the back sides first")
        fronts = [p for p in self.pages if p.batch == batches[-2]]
        backs = [p for p in self.pages if p.batch == batches[-1]]
        if len(fronts) != len(backs):
            raise ScanError(f"{len(fronts)} front sides but {len(backs)} back sides")
        rest = [p for p in self.pages if p.batch < batches[-2]]
        self.pages = rest + [replace(p, batch=batches[-2])
                             for p in DuplexOrder.FRONTS_THEN_BACKS.arrange(fronts + backs)]

    def render(self, directory: Path) -> list[Path]:
        """Write the pages with their rotation applied.

        Args:
            directory: Existing output directory.

        Returns:
            One PNG file per page, in page order.
        """
        return [self._store.turned_copy(p.path, directory / f"page-{n:04d}.png",
                                        p.quarter_turns, p.dpi)
                for n, p in enumerate(self.pages, start=1)]

    def save_pdf(self, target: Path, quality: PdfQuality) -> Path:
        """Save all pages as one PDF.

        Args:
            target: PDF file to write.
            quality: Wanted reduction.

        Returns:
            The written file.
        """
        with tempfile.TemporaryDirectory(prefix="scanbench-pages-") as tmp:
            return self._pdf.write(self.render(Path(tmp)), target, quality)
