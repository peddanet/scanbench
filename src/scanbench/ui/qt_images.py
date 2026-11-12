"""Convert image arrays for display in Qt."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QImageReader


def to_qimage(pixels: NDArray[np.uint8]) -> QImage:
    """Convert an RGB array into a QImage that owns its data.

    Args:
        pixels: Height x width x 3 array.

    Returns:
        The image.
    """
    data = np.ascontiguousarray(pixels[:, :, :3])
    height, width = data.shape[:2]
    image = QImage(data.data, width, height, 3 * width, QImage.Format.Format_RGB888)
    return image.copy()      # detach from the numpy buffer


def read_preview(path: Path, max_side: int) -> tuple[QImage, tuple[int, int]]:
    """Read an image file reduced for display, whatever its size.

    Qt 6 refuses to decode images above an allocation limit (256 MB by
    default, ``QImageReader.allocationLimit``); a 1200 dpi area scan already
    exceeds it. The limit is raised for this one read to what the file needs,
    and the image is scaled while it is read.

    Args:
        path: Image file.
        max_side: Longest side of the result in pixels; smaller images keep
            their size.

    Returns:
        The reduced image and the full size (width, height) in pixels.

    Raises:
        OSError: If the file cannot be read.
    """
    reader = QImageReader(str(path))
    full = reader.size()
    if not full.isValid():
        raise OSError(f"{path.name}: {reader.errorString()}")
    width, height = full.width(), full.height()
    factor = min(1.0, max_side / max(width, height))
    reader.setScaledSize(QSize(max(1, round(width * factor)), max(1, round(height * factor))))
    limit = QImageReader.allocationLimit()
    needed = -(-width * height * 4 // 2**20) + 1       # 32-bit pixels, in MiB
    if 0 < limit < needed:
        QImageReader.setAllocationLimit(needed)
    try:
        image = reader.read()
    finally:
        QImageReader.setAllocationLimit(limit)
    if image.isNull():
        raise OSError(f"{path.name}: {reader.errorString()}")
    return image, (width, height)
