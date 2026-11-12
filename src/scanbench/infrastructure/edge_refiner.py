"""Place the frame sides exactly on the photo edges, at full resolution."""

from dataclasses import replace

import cv2
import numpy as np
from numpy.typing import NDArray

from scanbench.domain.crop_region import CropRegion

OUTSIDE_MM = 2.0
"""How far outside the rough frame side the search starts."""

STRIP_MM = 1.5
"""Widest light strip along a side that is cut away (shadow line, paper edge,
light lid seam). A wider light band is the white border of the print and stays."""

LOOSE = 2.0
"""A pixel belongs to a light strip if its colour distance from the lid is below
this times the lid threshold: lighter than the photo, but not quite lid colour."""

NEUTRAL = (70.0, 6.0)
"""A pixel also belongs to a strip if it is a neutral grey (a, b within the
second value of the lid) at most the first value darker than the lid: the
shadow line of the photo edge."""

SHARE = 0.5
"""Share of a line that must be lid or strip for the line to be cut away."""


class EdgeRefiner:
    """Move each side of a rough frame onto the real photo edge (Strategy).

    The detection works on a reduced copy of the scan, so a side may lie a
    fraction of a millimetre off, and along the edges of a photo there is
    often a thin light strip that is neither lid nor picture. For each side
    the refiner looks at lines parallel to that side, from a little outside
    the rough frame inwards, at full resolution. Lines that consist mainly of
    lid colour, or of a light strip no wider than ``STRIP_MM``, are outside
    the photo; the first other line is the photo edge.
    """

    def __init__(self, lid: NDArray[np.float32], lid_distance: float) -> None:
        """Store the lid colour and threshold.

        Args:
            lid: Lab colour of the lid (OpenCV 8-bit Lab scale).
            lid_distance: Lab distance below which a pixel counts as lid.
        """
        self._lid = lid
        self._lid_distance = lid_distance

    def _upright(self, pixels: NDArray[np.uint8], region: CropRegion,
                 margin: int) -> NDArray[np.float64]:
        """Cut the region with a margin out of the scan, deskew it, measure lid distance.

        Only this cut-out is converted, so a 2400 dpi scan needs little memory.

        Args:
            pixels: RGB scan at full resolution.
            region: Rough frame.
            margin: Margin in pixels on every side.

        Returns:
            Lab distance from the lid of the upright cut-out, with neutral
            grey (shadow) mapped into the light-strip range; the frame occupies
            ``margin`` to ``margin + size`` in both directions. Outside the
            scan the outermost pixels repeat.
        """
        matrix = cv2.getRotationMatrix2D((region.cx, region.cy), region.angle, 1.0)
        matrix[0, 2] += region.width / 2 + margin - region.cx
        matrix[1, 2] += region.height / 2 + margin - region.cy
        size = (round(region.width) + 2 * margin, round(region.height) + 2 * margin)
        crop = cv2.warpAffine(pixels, matrix, size, flags=cv2.INTER_NEAREST,
                              borderMode=cv2.BORDER_REPLICATE)
        lab = np.asarray(cv2.cvtColor(crop, cv2.COLOR_RGB2LAB), dtype=np.float64)
        distance = np.linalg.norm(lab - self._lid, axis=2)
        neutral = ((np.abs(lab[:, :, 1:] - self._lid[1:]) < NEUTRAL[1]).all(axis=2)
                   & (lab[:, :, 0] > self._lid[0] - NEUTRAL[0]))
        # neutral grey counts as a light strip (between lid and loose threshold)
        strip_value = (self._lid_distance + LOOSE * self._lid_distance) / 2
        return np.asarray(np.where(neutral & (distance >= self._lid_distance),
                                   np.minimum(distance, strip_value), distance),
                          dtype=np.float64)

    @staticmethod
    def _run(flags: NDArray[np.bool_], start: int) -> int:
        """Return the index of the first False flag at or after ``start``.

        Args:
            flags: One flag per line.
            start: First line to look at.

        Returns:
            The index, or the number of flags if all are True.
        """
        rest = np.flatnonzero(~flags[start:])
        return start + int(rest[0]) if rest.size else len(flags)

    def _edge(self, lines: NDArray[np.float64], margin: int, strip: int) -> int:
        """Return how many outer lines are not part of the photo.

        Args:
            lines: Distances, one row per line, outermost line first; line
                ``margin`` is the side of the rough frame.
            margin: Lines outside the rough frame.
            strip: Widest light strip in lines.

        Returns:
            Number of lines outside the photo.
        """
        lid = (lines < self._lid_distance).mean(axis=1) >= SHARE
        light = (lines < LOOSE * self._lid_distance).mean(axis=1) >= SHARE
        if lid[0]:
            # free side: lid, maybe a light strip, then the photo
            lid_end = self._run(lid, 0)
            if lid_end - margin > strip:
                return margin     # a border in lid colour: only the rough edge shows it
            light_end = self._run(light, lid_end)
            edge = lid_end if light_end - lid_end > strip else light_end
            return min(edge, margin + strip)
        # a neighbouring photo lies outside: only cut a light strip inside the frame
        light_end = self._run(light, margin)
        return light_end if light_end - margin <= strip else margin

    def _cuts(self, image: NDArray[np.float64], margin: int,
              strip: int) -> tuple[int, int, int, int]:
        """Return how many lines lie outside the photo on each side.

        Args:
            image: Upright distance image with ``margin`` around the rough frame.
            margin: Lines outside the rough frame.
            strip: Widest light strip in lines.

        Returns:
            Left, right, top and bottom count.
        """
        height, width = image.shape
        # the middle 80 % of each side, so corners and neighbouring photos do not count
        rows = image[round(0.1 * height) + margin:round(0.9 * height) - margin]
        cols = image[:, round(0.1 * width) + margin:round(0.9 * width) - margin]
        reach = margin + 3 * strip    # far enough to tell a strip from a wide border
        return (self._edge(rows[:, :reach].T, margin, strip),
                self._edge(rows[:, ::-1][:, :reach].T, margin, strip),
                self._edge(cols[:reach], margin, strip),
                self._edge(cols[::-1][:reach], margin, strip))

    def refine(self, pixels: NDArray[np.uint8], region: CropRegion,
               dpi: int) -> CropRegion:
        """Return the frame with every side on the photo edge.

        Args:
            pixels: RGB scan at full resolution.
            region: Rough frame in scan pixels.
            dpi: Resolution of the scan.

        Returns:
            The refined frame; skew and turn stay unchanged.
        """
        mm = dpi / 25.4
        margin, strip = max(2, round(OUTSIDE_MM * mm)), max(1, round(STRIP_MM * mm))
        left, right, top, bottom = self._cuts(self._upright(pixels, region, margin),
                                              margin, strip)
        # centre shift in upright coordinates, turned back into the scan
        du, dv = (left - right) / 2, (top - bottom) / 2
        rad = np.radians(region.angle)
        return replace(region,
                       cx=region.cx + float(du * np.cos(rad) - dv * np.sin(rad)),
                       cy=region.cy + float(du * np.sin(rad) + dv * np.cos(rad)),
                       width=region.width + 2 * margin - left - right,
                       height=region.height + 2 * margin - top - bottom)
