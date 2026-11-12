"""Use case "scan a photo album": scan, detect, confirm, cut into photos."""

import json
import re
import shutil
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.image_format import ImageFormat
from scanbench.domain.paper_format import PHOTO_PRESETS
from scanbench.domain.scan_area import ScanArea
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.infrastructure.image_cropper import ImageCropper
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.scan_observer import ScanObserver
from scanbench.infrastructure.scanimage_backend import ScanimageBackend

PREVIEW_MIN_DPI = 75
"""A preview scan uses the lowest offered resolution from this value up."""

AREA_MARGIN_MM = 3.0
"""Margin around the frames when only their area is scanned."""

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
        preview: True for a quick low-resolution scan that only locates the photos.
    """

    path: Path
    dpi: int
    regions: list[CropRegion] = field(default_factory=list)
    preview: bool = False


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

    def _scan(self, device: str, settings: ScanSettings, options: DeviceOptions,
              observer: ScanObserver | None) -> tuple[Path, int]:
        """Scan one flatbed image into the work directory.

        Args:
            device: SANE device name.
            settings: Settings of this scan.
            options: What the device offers.
            observer: Receiver of progress and the partial image.

        Returns:
            The file and its resolution.
        """
        self._runs += 1
        prefix = self._work_dir / f"photo{self._runs:03d}"
        path = self._scanner.scan(device, settings, options, prefix, observer)[0]
        return path, self._store.resolution(path, settings.resolution)

    def scan(self, device: str, settings: ScanSettings, options: DeviceOptions,
             snap: bool = True, observer: ScanObserver | None = None) -> PhotoScan:
        """Scan the full frame and propose photo regions.

        Args:
            device: SANE device name.
            settings: Settings; the source should be the flatbed.
            options: What the device offers.
            snap: Fit regions that nearly match a photo preset to it.
            observer: Receiver of progress and the partial image.

        Returns:
            The scan waiting for confirmation.
        """
        path, dpi = self._scan(device, replace(settings, area=None), options, observer)
        return self.detect(path, dpi, snap)

    def preview(self, device: str, settings: ScanSettings, options: DeviceOptions,
                snap: bool = True, observer: ScanObserver | None = None) -> PhotoScan:
        """Scan the full frame quickly at the lowest resolution and locate the photos.

        Args:
            device: SANE device name.
            settings: Settings; only the colour mode is used.
            options: What the device offers.
            snap: Fit regions that nearly match a photo preset to it.
            observer: Receiver of progress and the partial image.

        Returns:
            The preview with proposed frames.
        """
        low = min((d for d in options.resolutions if d >= PREVIEW_MIN_DPI),
                  default=settings.resolution)
        path, dpi = self._scan(device, replace(settings, resolution=low, area=None), options,
                               observer)
        found = self.detect(path, dpi, snap)
        found.preview = True
        return found

    def scan_area(self, device: str, settings: ScanSettings, options: DeviceOptions,
                  observer: ScanObserver | None = None) -> PhotoScan:
        """Scan only the area around the frames of the preview, at full resolution.

        The frames, including the user's corrections, are carried over.

        Args:
            device: SANE device name.
            settings: Settings with the wanted resolution.
            options: What the device offers.
            observer: Receiver of progress and the partial image.

        Returns:
            The full-resolution scan waiting for confirmation.

        Raises:
            ScanError: If there is no preview with frames.
        """
        preview = self.current
        if preview is None or not preview.preview or not preview.regions:
            raise ScanError("make a preview scan with at least one frame first")
        area = ScanArea(*frame_edit.bounding_area_mm(preview.regions, preview.dpi,
                                                     AREA_MARGIN_MM))
        area = area.clamped(options.max_width_mm or settings.paper.width_mm,
                            options.max_height_mm or settings.paper.height_mm)
        path, dpi = self._scan(device, replace(settings, area=area), options, observer)
        factor, mm = dpi / preview.dpi, dpi / 25.4
        regions = [frame_edit.transferred(r, factor, area.left * mm, area.top * mm)
                   for r in preview.regions]
        self.current = PhotoScan(path, dpi, regions)
        return self.current

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
        if scan.preview:
            raise ScanError("this is a preview; scan the photos first")
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
