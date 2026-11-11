"""Paper and photo sizes in millimetres."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PaperFormat:
    """A named size in portrait orientation.

    Attributes:
        name: Display name, e.g. ``A4``.
        width_mm: Width in millimetres.
        height_mm: Height in millimetres.
    """

    name: str
    width_mm: float
    height_mm: float

    def pixels(self, dpi: int) -> tuple[int, int]:
        """Return the size in pixels at a resolution.

        Args:
            dpi: Resolution in dots per inch.

        Returns:
            Width and height in pixels.
        """
        return round(self.width_mm * dpi / 25.4), round(self.height_mm * dpi / 25.4)


A4 = PaperFormat("A4", 210.0, 297.0)
"""The full scan frame for documents and photo pages."""

DOCUMENT_FORMATS = (A4, PaperFormat("A5", 148.0, 210.0), PaperFormat("A6", 105.0, 148.0),
                    PaperFormat("Letter", 215.9, 279.4))
"""Document formats offered in the documents tab."""

PHOTO_PRESETS = (PaperFormat("9 x 13 cm", 90.0, 130.0), PaperFormat("10 x 15 cm", 100.0, 150.0),
                 PaperFormat("Postcard A6", 105.0, 148.0), PaperFormat("13 x 18 cm", 130.0, 180.0))
"""Photo sizes that help the detection and the manual "add frame"."""
