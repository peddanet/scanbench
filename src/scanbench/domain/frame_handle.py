"""The grips of a selected photo frame."""

from enum import Enum


class FrameHandle(Enum):
    """A grip on the frame; the value is its position in frame units.

    ``(sx, sy)`` with -1 = left/top, 0 = middle, +1 = right/bottom of the
    frame in its own (rotated) axes. ``ROTATE`` sits above the top edge.
    """

    TOP_LEFT = (-1, -1)
    TOP = (0, -1)
    TOP_RIGHT = (1, -1)
    RIGHT = (1, 0)
    BOTTOM_RIGHT = (1, 1)
    BOTTOM = (0, 1)
    BOTTOM_LEFT = (-1, 1)
    LEFT = (-1, 0)
    ROTATE = (0, -2)

    @property
    def sx(self) -> int:
        """Horizontal position: -1 left, 0 middle, +1 right.

        Returns:
            The position.
        """
        return int(self.value[0])

    @property
    def sy(self) -> int:
        """Vertical position: -1 top, 0 middle, +1 bottom (-2 rotation grip).

        Returns:
            The position.
        """
        return int(self.value[1])
