"""Dialog with the exact values of one photo frame."""

from dataclasses import replace

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
                               QFormLayout, QWidget)

from scanbench.domain.crop_region import CropRegion

TURNS = ("as framed", "90° clockwise", "180°", "90° counter-clockwise")
"""Choices for the turn of the saved photo, by number of clockwise quarter turns."""


class FrameValuesDialog(QDialog):
    """Enter width, height, skew and output turn of a frame as numbers."""

    def __init__(self, region: CropRegion, dpi: int, parent: QWidget | None = None) -> None:
        """Show the current values.

        Args:
            region: The frame.
            dpi: Resolution of the scan.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("Exact values")
        self._region = region
        self._mm = 25.4 / dpi
        self.width_mm = self._spin(region.width * self._mm, 5, 400, " mm", 1)
        self.height_mm = self._spin(region.height * self._mm, 5, 400, " mm", 1)
        self.angle = self._spin(region.angle, -180, 180, " °", 1)
        self.angle.setSingleStep(0.1)
        self.turn = QComboBox()
        self.turn.addItems(list(TURNS))
        self.turn.setCurrentIndex(region.quarter_turns % 4)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form = QFormLayout(self)
        form.addRow("Width:", self.width_mm)
        form.addRow("Height:", self.height_mm)
        form.addRow("Skew (positive = clockwise):", self.angle)
        form.addRow("Save the photo:", self.turn)
        form.addRow(buttons)

    @staticmethod
    def _spin(value: float, low: float, high: float, suffix: str,
              decimals: int) -> QDoubleSpinBox:
        """Create a number field.

        Args:
            value: Start value.
            low: Minimum.
            high: Maximum.
            suffix: Unit shown after the number.
            decimals: Shown decimals.

        Returns:
            The field.
        """
        spin = QDoubleSpinBox()
        spin.setDecimals(decimals)
        spin.setRange(low, high)
        spin.setSuffix(suffix)
        spin.setValue(value)
        return spin

    def region(self) -> CropRegion:
        """Return the frame with the entered values; the centre stays.

        Returns:
            The edited frame.
        """
        return replace(self._region, width=self.width_mm.value() / self._mm,
                       height=self.height_mm.value() / self._mm, angle=self.angle.value(),
                       quarter_turns=self.turn.currentIndex())
