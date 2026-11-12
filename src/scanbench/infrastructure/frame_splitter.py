"""Split one detected blob into photos that lie edge to edge."""

from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

GAP_COVERAGE = 0.6
"""Share of a line across the blob that must look like lid or white border."""

EDGE_COVERAGE = 0.75
"""Share of a line that must be edge pixels (shadow line between borderless photos)."""

THIN = 0.3
"""Beside a light seam (a few millimetres away) the light share must be below this;
otherwise the light line is a bright area of the picture (sky, wall), not a gap."""

BESIDE_MM, MIN_SIDE_MM = 3.0, 25.0
"""Distance of the thinness check, relative to the minimum photo side (25 mm)."""

SLANTS = (-3.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 3.0)
"""Seam angles tried, in degrees against the blob's axes."""


class FrameSplitter:
    """Find straight light seams inside a blob and cut it there (Strategy).

    Photos laid edge to edge merge into one blob. Between them there is
    nearly always a thin light line: the white border of a print or a
    sliver of the lid. In the blob's own (deskewed) axes this seam is a row
    or column in which most pixels are close to the lid colour. The blob is
    cut along the best such line if both parts are big enough to be photos;
    each part then gets its own minimum-area rectangle, so photos with
    different skew get different frames. Parts are split again, so three or
    four photos in a row are separated as well.
    """

    def __init__(self, gap_distance: float, sizes: list[tuple[float, float]],
                 max_depth: int = 3) -> None:
        """Store the thresholds.

        Args:
            gap_distance: Lab distance below which a pixel counts as gap.
            sizes: Known photo sizes (long, short side) in work pixels. A cut
                along an edge line alone is accepted only if both parts have
                one of these sizes, because pictures themselves contain long
                straight edges (steps, horizons).
            max_depth: Maximum number of nested cuts.
        """
        self._gap_distance = gap_distance
        self._sizes = sizes
        self._max_depth = max_depth

    def _known_size(self, rect: Any) -> bool:
        """Whether a rectangle is a known photo size or a row of up to three.

        A row of equal photos is accepted too, because it may be cut again.

        Args:
            rect: OpenCV rotated rectangle.

        Returns:
            True if it matches a known size or a row of them (within 10 %).
        """
        long_side, short_side = sorted(rect[1], reverse=True)
        for first, second in self._sizes:
            for count in (1, 2, 3):
                for a, b in ((first * count, second), (first, second * count)):
                    a, b = max(a, b), min(a, b)
                    if abs(long_side - a) <= 0.1 * a and abs(short_side - b) <= 0.1 * b:
                        return True
        return False

    @staticmethod
    def _upright(rect: Any) -> tuple[NDArray[np.float64], int, int]:
        """Return the affine map from the image into the rectangle's own axes.

        Args:
            rect: OpenCV rotated rectangle.

        Returns:
            2 x 3 matrix, width and height of the upright rectangle.
        """
        points = np.asarray(cv2.boxPoints(rect), dtype=np.float32)
        # boxPoints: corners in order; take three consecutive corners.
        first, second, third = points[0], points[1], points[2]
        width = max(1, round(float(np.linalg.norm(second - first))))
        height = max(1, round(float(np.linalg.norm(third - second))))
        target = np.array([[0, 0], [width, 0], [width, height]], dtype=np.float32)
        matrix = cv2.getAffineTransform(np.array([first, second, third]), target)
        return np.asarray(matrix, dtype=np.float64), width, height

    @staticmethod
    def _line_index(shape: tuple[int, int], axis: int, slope: float) -> NDArray[np.int64]:
        """Number every pixel by the slanted line it lies on.

        Args:
            shape: Height and width of the upright blob.
            axis: 0 for rows (horizontal seams), 1 for columns (vertical seams).
            slope: Tangent of the seam's angle against the axis.

        Returns:
            Line index per pixel.
        """
        rows, cols = np.indices(shape)
        along, across = (cols, rows) if axis == 0 else (rows, cols)
        centre = shape[1 - axis] / 2
        return np.asarray(np.rint(across - (along - centre) * slope), dtype=np.int64)

    @staticmethod
    def _scores(cues: tuple[NDArray[np.bool_], NDArray[np.bool_]], inside: NDArray[np.bool_],
                key: NDArray[np.int64],
                beside: int) -> tuple[NDArray[np.float64], NDArray[np.bool_]]:
        """Score every line of one direction as seam.

        Args:
            cues: Light pixels and edge pixels, upright.
            inside: Blob pixels, upright.
            key: Line number (from 0) of every blob pixel.
            beside: Distance in pixels at which a light seam must have ended.

        Returns:
            Score per line (at least ``GAP_COVERAGE`` means seam) and whether
            the light cue alone carries it.
        """
        light, edges = cues
        counts = np.bincount(key)
        light_share = np.bincount(key, weights=light[inside]) / np.maximum(counts, 1)
        edge_share = (np.bincount(key, weights=edges[inside]) / np.maximum(counts, 1)
                      * GAP_COVERAGE / EDGE_COVERAGE)
        thin = np.zeros_like(light_share, dtype=bool)
        thin[beside:-beside] = ((light_share[:-2 * beside] < THIN)
                                & (light_share[2 * beside:] < THIN))
        light_score = np.where(thin, light_share, 0.0)
        score = np.maximum(light_score, edge_share)
        score[counts < 0.5 * counts.max()] = 0.0       # lines that only touch the blob
        return score, light_score >= GAP_COVERAGE

    def _seam(self, cues: tuple[NDArray[np.bool_], NDArray[np.bool_]],
              inside: NDArray[np.bool_],
              min_side: float, beside: int) -> tuple[int, float, int, bool] | None:
        """Find the best straight seam, allowing a few degrees of slant.

        Args:
            cues: Light pixels and edge pixels, upright.
            inside: Blob pixels, upright.
            min_side: Minimum photo side in pixels.
            beside: Distance in pixels at which a light seam must have ended.

        Returns:
            ``(axis, slope, index, by_edge)`` of the seam, or None; ``by_edge``
            tells that only the edge cue was strong enough.
        """
        found = [best for axis in (0, 1) for degrees in SLANTS
                 if (best := self._best_line(cues, inside, (axis, degrees),
                                             int(min_side), beside)) is not None]
        if not found:
            return None
        return max(found, key=lambda f: f[0])[1:]

    def _best_line(self, cues: tuple[NDArray[np.bool_], NDArray[np.bool_]],
                   inside: NDArray[np.bool_], direction: tuple[int, float], margin: int,
                   beside: int) -> tuple[float, int, float, int, bool] | None:
        """Return the best seam of one direction and slant.

        Args:
            cues: Light pixels and edge pixels, upright.
            inside: Blob pixels, upright.
            direction: Axis (0 rows, 1 columns) and slant in degrees.
            margin: Lines closer than this to the blob border are no seams.
            beside: Distance in pixels at which a light seam must have ended.

        Returns:
            ``(score, axis, slope, index, by_edge)``, or None without a seam.
        """
        axis, degrees = direction
        slope = float(np.tan(np.radians(degrees)))
        index = self._line_index(inside.shape, axis, slope)
        offset = max(0, -int(index.min()))
        score, by_light = self._scores(cues, inside, index[inside] + offset, beside)
        inner = score[margin:len(score) - margin]
        if not inner.size or inner.max() < GAP_COVERAGE:
            return None
        line = margin + int(inner.argmax())
        return float(score[line]), axis, slope, line - offset, not bool(by_light[line])

    def _upright_cues(self, rect: Any, images: tuple[NDArray[np.float64], NDArray[np.uint8],
                                                     NDArray[np.uint8]]) -> \
            tuple[NDArray[np.float64], NDArray[np.bool_], NDArray[np.bool_], NDArray[np.bool_]]:
        """Turn the blob upright and compute the seam cues inside it.

        Args:
            rect: OpenCV rotated rectangle of the blob.
            images: Colour distance, foreground mask and edge image.

        Returns:
            Affine map into the upright blob, blob pixels, light pixels and
            (slightly widened) edge pixels.
        """
        distance, foreground, edges = images
        matrix, width, height = self._upright(rect)
        size = (width, height)
        light = cv2.warpAffine(distance.astype(np.float32), matrix, size,
                               flags=cv2.INTER_NEAREST, borderValue=1e6) < self._gap_distance
        inside = cv2.warpAffine(foreground, matrix, size, flags=cv2.INTER_NEAREST) > 0
        edge = cv2.warpAffine(edges, matrix, size, flags=cv2.INTER_NEAREST) > 0
        # an edge seam is one pixel wide and may wobble: widen the edge cue a little
        wide_edge = cv2.dilate(edge.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        return matrix, inside, light & inside, wide_edge & inside

    @staticmethod
    def _part(matrix: NDArray[np.float64], pixels: NDArray[np.bool_],
              min_side: float) -> Any | None:
        """Return the rectangle around one side of a seam, in image coordinates.

        Args:
            matrix: Map from the image into the upright blob.
            pixels: Upright pixels of this side.
            min_side: Minimum photo side in pixels.

        Returns:
            OpenCV rotated rectangle, or None if this side is too small for a photo.
        """
        points = np.argwhere(pixels)[:, ::-1].astype(np.float32)   # (x, y)
        if len(points) < 3:
            return None
        back = cv2.transform(points.reshape(-1, 1, 2), cv2.invertAffineTransform(matrix))
        child = cv2.minAreaRect(back.reshape(-1, 2).astype(np.float32))
        return child if min(child[1]) >= min_side else None

    def split(self, rect: Any, images: tuple[NDArray[np.float64], NDArray[np.uint8],
                                             NDArray[np.uint8]],
              min_side: float, depth: int = 0) -> list[Any]:
        """Cut a blob's rectangle into the rectangles of single photos.

        Args:
            rect: OpenCV rotated rectangle of the blob.
            images: Colour distance from the lid, filled foreground mask and edge
                image (Canny), all of the whole work image.
            min_side: Minimum photo side in pixels.
            depth: Current nesting depth.

        Returns:
            One or more OpenCV rotated rectangles.
        """
        if depth >= self._max_depth:
            return [rect]
        matrix, inside, light, edge = self._upright_cues(rect, images)
        seam = self._seam((light, edge), inside, min_side,
                          max(2, round(min_side * BESIDE_MM / MIN_SIDE_MM)))
        if seam is None:
            return [rect]
        index = self._line_index(inside.shape, seam[0], seam[1])     # axis, slope
        parts = [self._part(matrix, inside & side & ~light, min_side)
                 for side in (index < seam[2] - 1, index > seam[2] + 1)]
        if any(part is None for part in parts) or \
                (seam[3] and not all(self._known_size(part) for part in parts)):
            return [rect]
        return [r for child in parts
                for r in self.split(child, images, min_side, depth + 1)]
