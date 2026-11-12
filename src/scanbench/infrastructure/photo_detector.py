"""Find photos and postcards on a flatbed scan."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from scanbench.domain.crop_region import CropRegion
from scanbench.domain.paper_format import PHOTO_PRESETS
from scanbench.infrastructure.edge_refiner import EdgeRefiner
from scanbench.infrastructure.frame_splitter import FrameSplitter

Rect = tuple[Sequence[float], Sequence[float], float]
"""OpenCV rotated rectangle: centre, size, angle."""

WORK_DPI = 75
"""Detection runs on a copy at this resolution; enough for frame edges."""


@dataclass(frozen=True)
class DetectorTuning:
    """Thresholds of the detection, in physical units where possible.

    Attributes:
        min_side_mm: Shorter side a photo must have at least.
        color_distance: Lab distance from the background that counts as photo.
        close_mm: Gaps up to this size inside a photo are closed.
        open_mm: Bridges up to this width between photos are cut.
        min_fill: Minimum share of the rectangle covered by the found area.
    """

    min_side_mm: float = 25.0
    color_distance: float = 14.0
    close_mm: float = 3.0
    open_mm: float = 2.0
    min_fill: float = 0.55


def _kernel(size_mm: float) -> NDArray[np.uint8]:
    """Return an elliptic structuring element of a physical size at WORK_DPI.

    Args:
        size_mm: Diameter in millimetres.

    Returns:
        The kernel, at least 3 pixels wide.
    """
    pixels = max(3, round(size_mm / 25.4 * WORK_DPI) | 1)
    return u8(cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (pixels, pixels)))


def u8(pixels: Any) -> NDArray[np.uint8]:
    """View an OpenCV result as 8-bit array (OpenCV's stubs are untyped).

    Args:
        pixels: Array returned by OpenCV.

    Returns:
        The same data as ``uint8`` array.
    """
    return np.asarray(pixels, dtype=np.uint8)


def region_from_points(points: NDArray[Any], scale: float) -> CropRegion:
    """Describe four rectangle corners as a region with skew in (-45, 45].

    The edge whose direction is closest to horizontal becomes the width,
    so a photo lying 89 degrees turned is recognised as a portrait photo
    with 1 degree skew instead of a landscape photo with 89 degrees.

    Args:
        points: Corners in order around the rectangle.
        scale: Factor from detection pixels to scan pixels.

    Returns:
        The region in scan pixels.
    """
    corners = [(float(x) * scale, float(y) * scale) for x, y in points]
    edges = []
    for index in range(2):
        (x0, y0), (x1, y1) = corners[index], corners[index + 1]
        angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
        angle = (angle + 90) % 180 - 90          # direction is irrelevant: (-90, 90]
        edges.append((abs(angle), angle, math.hypot(x1 - x0, y1 - y0)))
    (_, angle, width), (_, _, height) = sorted(edges)
    if angle == -45.0:
        angle = 45.0
    cx = sum(x for x, _ in corners) / 4
    cy = sum(y for _, y in corners) / 4
    return CropRegion(cx, cy, width, height, angle)


class PhotoDetector:
    """Detect rectangular photos on a light flatbed background (Strategy).

    Two cues are combined, because neither is enough alone:

    * colour distance from the background colour: finds the photo area,
      but misses light or grey borders that are close to the lid colour;
    * edges (Canny): the thin shadow line every photo edge casts on the
      scanner glass outlines even white-bordered postcards.

    The union is closed, filled and opened, and each remaining blob is
    described by its minimum-area rectangle. Only rotation is ever
    estimated, never perspective, so results cannot become trapezoids.
    """

    def __init__(self, tuning: DetectorTuning | None = None) -> None:
        """Store the thresholds.

        Args:
            tuning: Thresholds; defaults suit white or grey scanner lids.
        """
        self._tuning = tuning or DetectorTuning()

    @staticmethod
    def background(lab: NDArray[np.uint8]) -> NDArray[np.float32]:
        """Estimate the lid colour as the most frequent light colour.

        Args:
            lab: Image in Lab colour space.

        Returns:
            Lab colour of the background.
        """
        lightness = lab[:, :, 0]
        histogram = np.bincount(lightness.ravel() // 4, minlength=64)
        histogram[:32] = 0            # the lid is light; ignore the dark half
        peak = int(np.argmax(histogram)) * 4
        mask = (lightness >= peak) & (lightness < peak + 4)
        return np.asarray(np.median(lab[mask], axis=0), dtype=np.float32)

    def distance(self, small: NDArray[np.uint8]) -> NDArray[np.float64]:
        """Return the colour distance of every pixel from the lid colour.

        Args:
            small: RGB image at WORK_DPI.

        Returns:
            Lab distance per pixel.
        """
        lab = u8(cv2.cvtColor(small, cv2.COLOR_RGB2LAB))
        return np.asarray(np.linalg.norm(lab.astype(np.float64) - self.background(lab),
                                         axis=2), dtype=np.float64)

    def mask(self, small: NDArray[np.uint8],
             distance: NDArray[np.float64] | None = None) -> NDArray[np.uint8]:
        """Return the foreground mask at work resolution.

        Args:
            small: RGB image at WORK_DPI.
            distance: Precomputed colour distance, or None.

        Returns:
            255 for photo pixels, 0 for background.
        """
        if distance is None:
            distance = self.distance(small)
        colour = np.where(distance > self._tuning.color_distance, 255, 0).astype(np.uint8)
        gray = cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY), (3, 3), 0)
        edges = cv2.Canny(gray, 20, 60)
        combined = cv2.bitwise_or(colour, edges)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, _kernel(self._tuning.close_mm))
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(combined)
        cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
        return u8(cv2.morphologyEx(filled, cv2.MORPH_OPEN, _kernel(self._tuning.open_mm)))

    def _rectangle(self, contour: Any, min_side: float) -> Rect | None:
        """Return the minimum-area rectangle of a blob that looks like a photo.

        Args:
            contour: Outline of the blob.
            min_side: Minimum length of the shorter side in pixels.

        Returns:
            The rectangle, or None for specks and sparse shapes such as lines.
        """
        rect = cv2.minAreaRect(contour)
        rect_w, rect_h = rect[1]
        if min(rect_w, rect_h) < min_side:
            return None
        if cv2.contourArea(contour) / (rect_w * rect_h) < self._tuning.min_fill:
            return None
        return rect

    def _cues(self, small: NDArray[np.uint8]) -> tuple[NDArray[np.float64], NDArray[np.uint8],
                                                       NDArray[np.uint8]]:
        """Compute what the detection and the splitter look at.

        Args:
            small: Scan reduced to the work resolution.

        Returns:
            Colour distance from the lid, filled foreground mask and edge image.
        """
        distance = self.distance(small)
        edges = u8(cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY),
                                              (3, 3), 0), 20, 60))
        return distance, self.mask(small, distance), edges

    def _frames(self, small: NDArray[np.uint8], work_mm: float) -> list[Rect]:
        """Find and split the photo rectangles on the reduced scan.

        Args:
            small: Scan at the work resolution.
            work_mm: Work pixels per millimetre.

        Returns:
            OpenCV rotated rectangles in work pixels (rough; the edge refiner
            places the sides exactly).
        """
        cues = self._cues(small)
        contours, _ = cv2.findContours(cues[1], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_side = self._tuning.min_side_mm * work_mm
        splitter = FrameSplitter(2 * self._tuning.color_distance,
                                 [(p.height_mm * work_mm, p.width_mm * work_mm)
                                  for p in PHOTO_PRESETS])
        return [part for rect in (self._rectangle(c, min_side) for c in contours)
                if rect is not None for part in splitter.split(rect, cues, min_side)]

    def detect(self, pixels: NDArray[np.uint8], dpi: int) -> list[CropRegion]:
        """Find the photos on a scan.

        Args:
            pixels: RGB scan.
            dpi: Resolution of the scan.

        Returns:
            Regions in scan pixels, top to bottom, then left to right.
        """
        factor = min(1.0, WORK_DPI / dpi)
        height, width = pixels.shape[:2]
        size = (max(1, round(width * factor)), max(1, round(height * factor)))
        small = u8(cv2.resize(pixels, size, interpolation=cv2.INTER_AREA))
        refiner = EdgeRefiner(self.background(u8(cv2.cvtColor(small, cv2.COLOR_RGB2LAB))),
                              self._tuning.color_distance)
        regions = [refiner.refine(pixels, region_from_points(np.asarray(cv2.boxPoints(rect)),
                                                             1 / factor), dpi)
                   .clamped(width, height) for rect in self._frames(small, dpi * factor / 25.4)]
        row = 30 / 25.4 * dpi      # photos whose centres differ < 3 cm share a row
        return sorted(regions, key=lambda r: (round(r.cy / row), r.cx))
