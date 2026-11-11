"""File format of saved photos."""

from enum import Enum


class ImageFormat(Enum):
    """Photo file format; the value is the file extension."""

    PNG = "png"
    JPEG = "jpg"
