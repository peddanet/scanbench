"""A detected or user-edited photo frame on a scan."""

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace

from scanbench.domain.paper_format import PaperFormat


@dataclass(frozen=True)
class CropRegion:
    """A rotated rectangle in pixel coordinates of the raw scan.

    Attributes:
        cx: Centre x.
        cy: Centre y.
        width: Width along the rectangle's own x axis.
        height: Height along the rectangle's own y axis.
        angle: Skew in degrees, (-45, 45]; positive turns clockwise on screen.
        quarter_turns: Extra 90-degree turns of the result, clockwise, 0..3.
    """

    cx: float
    cy: float
    width: float
    height: float
    angle: float = 0.0
    quarter_turns: int = 0

    def turned(self, steps: int) -> "CropRegion":
        """Return the region with the result turned by 90-degree steps.

        Args:
            steps: +1 clockwise, -1 counter-clockwise.

        Returns:
            The new region.
        """
        return replace(self, quarter_turns=(self.quarter_turns + steps) % 4)

    def straightened(self) -> "CropRegion":
        """Return the region without skew (axis-parallel frame).

        Returns:
            The new region.
        """
        return replace(self, angle=0.0)

    def fitted(self, paper: PaperFormat, dpi: int) -> "CropRegion":
        """Return the region resized to a format, keeping centre and orientation.

        Args:
            paper: Wanted size, e.g. a 10 x 15 cm photo.
            dpi: Resolution of the scan.

        Returns:
            The new region; landscape stays landscape, portrait stays portrait.
        """
        long_side, short_side = sorted(paper.pixels(dpi), reverse=True)
        if self.width >= self.height:
            return replace(self, width=long_side, height=short_side)
        return replace(self, width=short_side, height=long_side)

    def snapped(self, presets: Iterable[PaperFormat], dpi: int,
                tolerance: float = 0.06) -> "CropRegion":
        """Return the region fitted to the first preset it nearly matches.

        Args:
            presets: Candidate formats.
            dpi: Resolution of the scan.
            tolerance: Allowed relative deviation per side.

        Returns:
            The fitted region, or this region if no preset matches.
        """
        size = sorted((self.width, self.height), reverse=True)
        for paper in presets:
            wanted = sorted(paper.pixels(dpi), reverse=True)
            if all(abs(have - want) <= tolerance * want for have, want in zip(size, wanted)):
                return self.fitted(paper, dpi)
        return self

    def corners(self) -> list[tuple[float, float]]:
        """Return the four corners clockwise from top-left.

        Returns:
            Corner coordinates in scan pixels.
        """
        rad = math.radians(self.angle)
        cos, sin = math.cos(rad), math.sin(rad)
        half_w, half_h = self.width / 2, self.height / 2
        result = []
        for dx, dy in ((-half_w, -half_h), (half_w, -half_h), (half_w, half_h),
                       (-half_w, half_h)):
            result.append((self.cx + dx * cos - dy * sin, self.cy + dx * sin + dy * cos))
        return result

    def clamped(self, frame_width: float, frame_height: float) -> "CropRegion":
        """Shrink the region so that its corners stay inside the frame.

        The full scan frame (A4) is the largest possible region.

        Args:
            frame_width: Width of the scan in pixels.
            frame_height: Height of the scan in pixels.

        Returns:
            The region, scaled down around its centre if it sticks out.
        """
        scale = 1.0
        for x, y in self.corners():
            for value, centre, limit in ((x, self.cx, frame_width), (y, self.cy, frame_height)):
                if value < 0:
                    scale = min(scale, centre / max(centre - value, 1e-9))
                elif value > limit:
                    scale = min(scale, (limit - centre) / max(value - centre, 1e-9))
        return replace(self, width=self.width * scale, height=self.height * scale)
