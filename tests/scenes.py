"""Synthetic flatbed scans with photos and postcards for detector tests."""

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray

from scanbench.domain.crop_region import CropRegion

DPI = 100
"""Resolution of the synthetic scans: fast, but fine enough for the edges."""

LID = (246, 246, 243)
"""Colour of the scanner lid (slightly warm white)."""


@dataclass(frozen=True)
class Placed:
    """A photo placed on the synthetic glass.

    Attributes:
        width_mm: Width of the photo.
        height_mm: Height of the photo.
        cx_mm: Centre x on the glass.
        cy_mm: Centre y on the glass.
        angle: Skew in degrees, clockwise on screen.
        border: Grey value of a 4 mm border, or None for borderless.
        seed: Seed of the random picture content.
    """

    width_mm: float
    height_mm: float
    cx_mm: float
    cy_mm: float
    angle: float = 0.0
    border: int | None = None
    seed: int = 1

    def region(self) -> CropRegion:
        """Return the true region in scan pixels.

        Returns:
            The region.
        """
        mm = DPI / 25.4
        return CropRegion(self.cx_mm * mm, self.cy_mm * mm, self.width_mm * mm,
                          self.height_mm * mm, self.angle)


def picture(width: int, height: int, seed: int, border: int | None) -> NDArray[np.uint8]:
    """Create random but photo-like content: smooth colour areas and noise.

    Args:
        width: Width in pixels.
        height: Height in pixels.
        seed: Random seed.
        border: Grey value of a 4 mm border, or None.

    Returns:
        RGB pixels.
    """
    rng = np.random.default_rng(seed)
    coarse = rng.integers(20, 220, size=(4, 5, 3), dtype=np.uint8)
    content = np.asarray(cv2.resize(coarse, (width, height), interpolation=cv2.INTER_CUBIC),
                         dtype=np.uint8)
    noise = rng.normal(0, 6, size=content.shape)
    content = np.clip(content.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    if border is not None:
        edge = round(4 * DPI / 25.4)
        framed = np.full_like(content, border)
        framed[edge:-edge, edge:-edge] = content[edge:-edge, edge:-edge]
        content = framed
    return np.asarray(content, dtype=np.uint8)


def scan(photos: list[Placed], width_mm: float = 210, height_mm: float = 297) -> \
        NDArray[np.uint8]:
    """Render a flatbed scan with the photos on the lid background.

    Each photo casts a thin shadow line, as on a real scanner.

    Args:
        photos: The photos.
        width_mm: Width of the scan area.
        height_mm: Height of the scan area.

    Returns:
        RGB pixels.
    """
    mm = DPI / 25.4
    size = (round(width_mm * mm), round(height_mm * mm))
    rng = np.random.default_rng(0)
    canvas = np.clip(np.full((size[1], size[0], 3), LID, dtype=np.float64)
                     + rng.normal(0, 1.5, (size[1], size[0], 3)), 0, 255).astype(np.uint8)
    for photo in photos:
        _paste(canvas, photo)
    return canvas


def _paste(canvas: NDArray[np.uint8], photo: Placed) -> None:
    """Draw one photo with its shadow line onto the glass.

    Args:
        canvas: The scan, changed in place.
        photo: The photo.
    """
    size = (canvas.shape[1], canvas.shape[0])
    region = photo.region()
    content = picture(round(region.width), round(region.height), photo.seed, photo.border)
    top_left, top_right, _, bottom_left = region.corners()
    matrix = cv2.getAffineTransform(
        np.array([[0, 0], [region.width, 0], [0, region.height]], dtype=np.float32),
        np.array([top_left, top_right, bottom_left], dtype=np.float32))
    warped = cv2.warpAffine(content, matrix, size)
    mask = cv2.warpAffine(np.full(content.shape[:2], 255, np.uint8), matrix, size)
    outline = np.array(region.corners(), dtype=np.int32)
    cv2.polylines(canvas, [outline], True, (150, 150, 150), 1, cv2.LINE_AA)
    canvas[mask > 127] = warped[mask > 127]
