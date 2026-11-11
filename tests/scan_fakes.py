"""Test doubles for scanning: a scanner that returns prepared images."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from fakes import FakeShell
from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource
from scanbench.infrastructure.scanimage_backend import ScanimageBackend

OPTIONS = DeviceOptions(("Flatbed", "Automatic Document Feeder", "ADF Duplex"),
                        ("Color", "Gray", "Lineart"), (75, 150, 300, 600), 216.0, 297.0)
"""Options resembling a multifunction device with duplex feeder."""


def write_png(path: Path, pixels: NDArray[np.uint8], dpi: int) -> Path:
    """Write an RGB array as PNG with resolution.

    Args:
        path: Target file.
        pixels: Image.
        dpi: Resolution.

    Returns:
        The path.
    """
    Image.fromarray(pixels).save(path, dpi=(dpi, dpi))
    return path


def page(colour: int, width: int = 60, height: int = 80) -> NDArray[np.uint8]:
    """Create a plain page with a dark mark in the top-left corner.

    Args:
        colour: Grey value of the page.
        width: Width in pixels.
        height: Height in pixels.

    Returns:
        RGB pixels.
    """
    pixels = np.full((height, width, 3), colour, dtype=np.uint8)
    pixels[:10, :10] = 0
    return pixels


class FakeScanner(ScanimageBackend):
    """Scanner returning prepared images; records the requested settings."""

    def __init__(self, images: list[NDArray[np.uint8]] | None = None, dpi: int = 100,
                 feeder_pages: int = 3) -> None:
        """Store the images.

        Args:
            images: Images returned for a flatbed scan, in turn (last repeats).
            dpi: Resolution written into the files.
            feeder_pages: Number of pages a feeder scan returns.
        """
        super().__init__(FakeShell())
        self.images = images or [page(230)]
        self.dpi = dpi
        self.feeder_pages = feeder_pages
        self.requests: list[ScanSettings] = []

    def devices(self, include_test: bool = False) -> list[DeviceInfo]:
        """Return one device.

        Args:
            include_test: Ignored.

        Returns:
            The device list.
        """
        return [DeviceInfo("fake:1", "Fake", "Scanner", "flatbed scanner")]

    def options(self, device: str) -> DeviceOptions:
        """Return fixed options.

        Args:
            device: Ignored.

        Returns:
            The options.
        """
        return OPTIONS

    def scan(self, device: str, settings: ScanSettings, options: DeviceOptions,
             directory: Path, stem: str) -> list[Path]:
        """Write prepared images as scanned pages.

        Args:
            device: Ignored.
            settings: Recorded.
            options: Ignored.
            directory: Target directory.
            stem: File name prefix.

        Returns:
            The written pages.
        """
        self.requests.append(settings)
        count = 1 if settings.source is ScanSource.FLATBED else self.feeder_pages
        result = []
        for number in range(1, count + 1):
            image = self.images.pop(0) if len(self.images) > 1 else self.images[0]
            result.append(write_png(directory / f"{stem}-{number:03d}.png", image, self.dpi))
        return result
