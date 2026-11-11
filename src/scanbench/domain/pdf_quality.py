"""Compression levels of a PDF, mapped to Ghostscript's PDFSETTINGS."""

from enum import Enum


class PdfQuality(Enum):
    """PDF quality; ``setting`` is the Ghostscript preset or None for lossless.

    Every level is produced from the lossless original, never from another
    compressed level (Ghostscript does not downsample a second time below its
    threshold, see the scanner reference, chapter 12).
    """

    ORIGINAL = ("Original (lossless)", None)
    SCREEN = ("Screen (72 dpi)", "/screen")
    EBOOK = ("E-book (150 dpi)", "/ebook")
    PRINTER = ("Printer (300 dpi)", "/printer")
    PREPRESS = ("Prepress (300 dpi, best)", "/prepress")

    @property
    def label(self) -> str:
        """Text shown in the user interface.

        Returns:
            The label.
        """
        return str(self.value[0])

    @property
    def setting(self) -> str | None:
        """Ghostscript ``-dPDFSETTINGS`` value.

        Returns:
            The preset, or None for the lossless original.
        """
        setting = self.value[1]
        return None if setting is None else str(setting)
