"""What to scan and how."""

from dataclasses import dataclass

from scanbench.domain.color_mode import ColorMode
from scanbench.domain.paper_format import A4, PaperFormat
from scanbench.domain.scan_source import ScanSource


@dataclass(frozen=True)
class ScanSettings:
    """Settings of one scan job.

    Attributes:
        source: Flatbed or feeder.
        mode: Colour depth.
        resolution: Dots per inch.
        paper: Scan area; the full A4 frame by default.
    """

    source: ScanSource = ScanSource.FLATBED
    mode: ColorMode = ColorMode.COLOR
    resolution: int = 300
    paper: PaperFormat = A4
