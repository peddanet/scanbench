"""Frame editor with a details line and a hint text below it."""

from pathlib import Path

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.ui.region_view import RegionView

NO_SELECTION = "Click a frame to see its size, skew and orientation."
"""Details text while no frame is selected."""


class FrameEditor(QWidget):
    """The region view, a line describing the selected frame and a hint."""

    def __init__(self, hint: str) -> None:
        """Build the widgets.

        Args:
            hint: Initial hint text.
        """
        super().__init__()
        self.view = RegionView()
        self.details = QLabel()
        self.hint = QLabel(hint)
        self.hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.details)
        layout.addWidget(self.hint)
        self.view.frame_selected.connect(self.describe)
        self.view.regions_changed.connect(lambda _r: self.describe(self.view.selected_index()))
        self.describe(-1)

    def describe(self, index: int) -> None:
        """Show size, skew and orientation of a frame.

        Args:
            index: Frame index, -1 for none.
        """
        regions = self.view.regions
        if 0 <= index < len(regions):
            self.details.setText(f"Frame {index + 1}: "
                                 f"{frame_edit.summary(regions[index], self.view.dpi)}")
        else:
            self.details.setText(NO_SELECTION if regions else "")

    def show_scan(self, path: Path | None, dpi: int, regions: list[CropRegion]) -> None:
        """Show a scan (or nothing) and reset the details line.

        Args:
            path: Full-frame scan, or None.
            dpi: Its resolution.
            regions: Proposed frames.
        """
        self.view.show_scan(path, dpi, regions)
        self.describe(-1)
