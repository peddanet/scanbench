"""Colour depth of a scan."""

from enum import Enum


class ColorMode(Enum):
    """Scan mode, independent of the backend's option names."""

    COLOR = "Color"
    GRAY = "Gray"
    LINEART = "Black and white"
