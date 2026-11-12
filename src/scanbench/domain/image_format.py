"""File format of saved photos."""

from dataclasses import dataclass
from enum import Enum


class ImageFormat(Enum):
    """Photo file format; the value is the file extension."""

    PNG = "png"
    JPEG = "jpg"


@dataclass(frozen=True)
class ImageEncoding:
    """How a photo file is written.

    Attributes:
        image_format: PNG (lossless) or JPEG.
        jpeg_quality: JPEG quality 70 to 95; 92 is visually lossless.
        png_compression: zlib level 0 to 9 for PNG; changes only time and size.
    """

    image_format: ImageFormat = ImageFormat.PNG
    jpeg_quality: int = 92
    png_compression: int = 6
