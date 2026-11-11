"""Order in which a feeder delivers the pages of a two-sided scan."""

from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class DuplexOrder(Enum):
    """How the scanner's page sequence maps to reading order.

    ``INTERLEAVED``: front 1, back 1, front 2, back 2 (sheets turned at once).
    ``FRONTS_THEN_BACKS``: all fronts, then all backs in reverse order.
    """

    INTERLEAVED = "front, back, front, back"
    FRONTS_THEN_BACKS = "all fronts, then backs reversed"

    def arrange(self, pages: list[T]) -> list[T]:
        """Return the pages in reading order.

        Args:
            pages: Pages in the order the scanner delivered them.

        Returns:
            Pages in reading order.
        """
        if self is DuplexOrder.INTERLEAVED or len(pages) < 2:
            return list(pages)
        half = (len(pages) + 1) // 2
        fronts, backs = pages[:half], list(reversed(pages[half:]))
        ordered: list[T] = []
        for index, front in enumerate(fronts):
            ordered.append(front)
            if index < len(backs):
                ordered.append(backs[index])
        return ordered
