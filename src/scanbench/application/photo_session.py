"""Use case "scan a photo album": scan, detect, confirm, cut into photos."""

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from scanbench.domain.crop_region import CropRegion
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.image_format import ImageFormat
from scanbench.domain.paper_format import PHOTO_PRESETS
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.infrastructure.image_cropper import ImageCropper
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.scanimage_backend import ScanimageBackend

INDEX_FILE = "album.json"
"""Album index: one entry per photo with its source scan and region."""

_NUMBERED = re.compile(r"^photo-(\d{4,})\.(png|jpg)$")


@dataclass
class PhotoScan:
    """The scan waiting for confirmation and its (edited) regions.

    Attributes:
        path: Full-frame scan.
        dpi: Resolution of the scan.
        regions: Photo frames, as proposed or as edited by the user.
    """

    path: Path
    dpi: int
    regions: list[CropRegion] = field(default_factory=list)


@dataclass(frozen=True)
class AlbumOptions:
    """Where and how confirmed photos are stored.

    Attributes:
        folder: Album folder.
        image_format: PNG (lossless) or JPEG.
        keep_scans: Also keep the full-frame scans in ``scans/``.
    """

    folder: Path
    image_format: ImageFormat = ImageFormat.PNG
    keep_scans: bool = False


class PhotoSession:
    """State of the photo tab (State pattern: idle or waiting for confirmation).

    Every scan covers the whole A4 frame. The detector proposes regions;
    the user corrects them and confirms. Only then the photos are cut,
    deskewed, numbered after the last photo in the album and indexed.
    """

    def __init__(self, scanner: ScanimageBackend, detector: PhotoDetector,
                 store: ImageStore, work_dir: Path) -> None:
        """Store the collaborators.

        Args:
            scanner: SANE adapter.
            detector: Photo detection strategy.
            store: Image file access.
            work_dir: Existing directory for full-frame scans.
        """
        self._scanner = scanner
        self._detector = detector
        self._store = store
        self._work_dir = work_dir
        self._runs = 0
        self.current: PhotoScan | None = None

    def scan(self, device: str, settings: ScanSettings, options: DeviceOptions,
             snap: bool = True) -> PhotoScan:
        """Scan the full frame and propose photo regions.

        Args:
            device: SANE device name.
            settings: Settings; the source should be the flatbed.
            options: What the device offers.
            snap: Fit regions that nearly match a photo preset to it.

        Returns:
            The scan waiting for confirmation.
        """
        self._runs += 1
        path = self._scanner.scan(device, settings, options, self._work_dir,
                                  f"photo{self._runs:03d}")[0]
        return self.detect(path, self._store.resolution(path, settings.resolution), snap)

    def detect(self, path: Path, dpi: int, snap: bool = True) -> PhotoScan:
        """Propose regions for an existing full-frame scan.

        Args:
            path: The scan.
            dpi: Its resolution.
            snap: Fit regions that nearly match a photo preset to it.

        Returns:
            The scan waiting for confirmation.
        """
        regions = self._detector.detect(self._store.load_rgb(path), dpi)
        if snap:
            regions = [r.snapped(PHOTO_PRESETS, dpi) for r in regions]
        self.current = PhotoScan(path, dpi, regions)
        return self.current

    def discard(self) -> None:
        """Drop the scan waiting for confirmation."""
        self.current = None

    @staticmethod
    def next_number(folder: Path) -> int:
        """Return the number of the next photo in an album folder.

        Args:
            folder: Album folder (may not exist yet).

        Returns:
            One more than the highest ``photo-NNNN`` number, at least 1.
        """
        numbers = [int(m[1]) for p in folder.glob("photo-*")
                   if (m := _NUMBERED.match(p.name))] if folder.is_dir() else []
        return max(numbers, default=0) + 1

    @staticmethod
    def _index(folder: Path, entries: list[dict[str, object]]) -> None:
        """Append entries to the album index, replacing it atomically.

        Args:
            folder: Album folder.
            entries: New entries.
        """
        index = folder / INDEX_FILE
        data: list[dict[str, object]] = []
        if index.exists():
            try:
                data = json.loads(index.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                index.replace(folder / f"{INDEX_FILE}.broken")
        temporary = folder / f".{INDEX_FILE}.tmp"
        temporary.write_text(json.dumps(data + entries, indent=1) + "\n", encoding="utf-8")
        temporary.replace(index)

    def accept(self, album: AlbumOptions) -> list[Path]:
        """Cut, deskew and save the confirmed regions.

        Args:
            album: Target folder and format.

        Returns:
            The written photos in region order.

        Raises:
            ScanError: If no scan waits for confirmation.
        """
        scan = self.current
        if scan is None:
            raise ScanError("there is no scan to confirm")
        album.folder.mkdir(parents=True, exist_ok=True)
        number = self.next_number(album.folder)
        source = scan.path.name
        if album.keep_scans:
            kept = album.folder / "scans" / f"scan-{number:04d}.png"
            kept.parent.mkdir(exist_ok=True)
            shutil.copyfile(scan.path, kept)
            source = f"scans/{kept.name}"
        pixels = self._store.load_rgb(scan.path)
        written, entries = [], []
        for offset, region in enumerate(scan.regions):
            name = f"photo-{number + offset:04d}.{album.image_format.value}"
            target = self._store.save(ImageCropper.crop(pixels, region), album.folder / name,
                                      album.image_format, scan.dpi)
            written.append(target)
            entries.append({"file": name, "scan": source, "dpi": scan.dpi,
                            "region": asdict(region)})
        self._index(album.folder, entries)
        self.current = None
        return written
