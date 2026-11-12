"""Convert image arrays for display in Qt."""

import numpy as np
from numpy.typing import NDArray
from PySide6.QtGui import QImage


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
