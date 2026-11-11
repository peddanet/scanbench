"""Read, turn and write raster images with Pillow."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from scanbench.domain.image_format import ImageFormat
from scanbench.domain.scan_error import ScanError

JPEG_QUALITY = 92
"""JPEG quality for photos: visually lossless at moderate size."""

_TRANSPOSE = {1: Image.Transpose.ROTATE_270, 2: Image.Transpose.ROTATE_180,
              3: Image.Transpose.ROTATE_90}
"""Pillow operation per clockwise quarter turn (Pillow turns counter-clockwise)."""


class ImageStore:
    """File access for scans and results.

    Images travel as numpy arrays (height x width x 3, RGB, uint8) between
    the detector, the cropper and this store. The resolution is written
    into every file, so PDF pages and prints get their physical size.
    """

    @staticmethod
    def _open(path: Path) -> Image.Image:
        """Open an image and load it completely.

        Args:
            path: Image file.

        Returns:
            The loaded image.

        Raises:
            ScanError: If the file is missing or no image.
        """
        try:
            with Image.open(path) as image:
                image.load()
                return image.copy()  # the copy keeps info such as "dpi"
        except (OSError, ValueError) as exc:
            raise ScanError(f"cannot read image {path.name}: {exc}") from exc

    def load_rgb(self, path: Path) -> NDArray[np.uint8]:
        """Read an image as RGB array.

        Args:
            path: Image file.

        Returns:
            The pixels.
        """
        return np.asarray(self._open(path).convert("RGB"), dtype=np.uint8)

    def resolution(self, path: Path, fallback: int) -> int:
        """Return the resolution stored in an image file.

        Args:
            path: Image file.
            fallback: Value used if the file stores none.

        Returns:
            Horizontal resolution in dpi.
        """
        dpi = self._open(path).info.get("dpi")
        return round(float(dpi[0])) if dpi and float(dpi[0]) > 1 else fallback

    def turned_copy(self, source: Path, target: Path, quarter_turns: int, dpi: int) -> Path:
        """Write a copy turned clockwise by quarter turns, keeping its mode.

        Args:
            source: Scanned page.
            target: PNG file to write.
            quarter_turns: Clockwise 90-degree turns, 0..3.
            dpi: Resolution written into the file.

        Returns:
            The target.
        """
        image = self._open(source)
        if quarter_turns % 4:
            image = image.transpose(_TRANSPOSE[quarter_turns % 4])
        if image.mode not in ("1", "L", "RGB"):
            image = image.convert("RGB")
        image.save(target, format="PNG", dpi=(dpi, dpi))
        return target

    @staticmethod
    def save(pixels: NDArray[np.uint8], target: Path, image_format: ImageFormat,
             dpi: int) -> Path:
        """Write an RGB array as PNG or JPEG.

        Args:
            pixels: The image.
            target: File to write; the suffix is not changed.
            image_format: Output format.
            dpi: Resolution written into the file.

        Returns:
            The target.

        Raises:
            ScanError: If the file cannot be written.
        """
        image = Image.fromarray(pixels)
        try:
            if image_format is ImageFormat.JPEG:
                image.save(target, format="JPEG", quality=JPEG_QUALITY, dpi=(dpi, dpi),
                           subsampling=0)
            else:
                image.save(target, format="PNG", dpi=(dpi, dpi))
        except OSError as exc:
            raise ScanError(f"cannot write {target}: {exc}") from exc
        return target
