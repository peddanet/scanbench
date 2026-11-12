"""A part of the flatbed, in millimetres from the top-left corner."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanArea:
    """Rectangle to scan; ``scanimage -l -t -x -y``.

    Attributes:
        left: Distance from the left edge.
        top: Distance from the top edge.
        width: Width.
        height: Height.
    """

    left: float
    top: float
    width: float
    height: float

    def clamped(self, max_width: float, max_height: float) -> "ScanArea":
        """Keep the area inside the scanner's maximum area.

        Args:
            max_width: Maximum scan width.
            max_height: Maximum scan height.

        Returns:
            The area, moved and shrunk where needed.
        """
        left = min(max(self.left, 0.0), max_width)
        top = min(max(self.top, 0.0), max_height)
        return ScanArea(left, top, min(self.width, max_width - left),
                        min(self.height, max_height - top))
