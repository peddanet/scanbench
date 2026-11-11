"""Cut a rotated rectangle out of a scan and make it axis-parallel."""

import cv2
import numpy as np
from numpy.typing import NDArray

from scanbench.domain.crop_region import CropRegion


class ImageCropper:
    """Cut photos out of a scan.

    The region is mapped by an affine transformation (rotation and
    translation only), so the result is always a straight rectangle and
    never a trapezoid. Afterwards the result is turned by the region's
    quarter turns.
    """

    @staticmethod
    def crop(pixels: NDArray[np.uint8], region: CropRegion) -> NDArray[np.uint8]:
        """Return the content of a region, deskewed.

        Args:
            pixels: The scan (height x width x channels).
            region: Region in scan pixels.

        Returns:
            The cut-out photo.
        """
        width, height = max(1, round(region.width)), max(1, round(region.height))
        top_left, top_right, _, bottom_left = region.corners()
        source = np.array([top_left, top_right, bottom_left], dtype=np.float32)
        target = np.array([[0, 0], [width, 0], [0, height]], dtype=np.float32)
        matrix = cv2.getAffineTransform(source, target)
        result = cv2.warpAffine(pixels, matrix, (width, height), flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
        return np.ascontiguousarray(np.rot90(result, k=-region.quarter_turns))
