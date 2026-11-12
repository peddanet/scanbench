"""Combo boxes for source, mode, resolution and paper that follow the device."""

from collections.abc import Callable
from enum import Enum
from typing import Any

from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

from scanbench.domain.color_mode import ColorMode
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.paper_format import A4, DOCUMENT_FORMATS
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource


def fill(combo: QComboBox, items: list[tuple[str, Any]], preferred: Any = None) -> None:
    """Replace the entries of a combo box and keep or set the selection.

    Args:
        combo: The combo box.
        items: Text and data per entry.
        preferred: Data to select if the previous selection disappeared.
    """
    previous = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    for text, data in items:
        combo.addItem(text, data)
    for wanted in (previous, preferred):
        index = combo.findData(wanted)
        if wanted is not None and index >= 0:
            combo.setCurrentIndex(index)
            break
    combo.blockSignals(False)


def enum_items(values: list[Any]) -> list[tuple[str, Any]]:
    """Return combo entries for enum members.

    Args:
        values: Enum members whose value is the display text.

    Returns:
        Text and member per entry.
    """
    return [(str(v.value) if isinstance(v, Enum) else str(v), v) for v in values]


class SettingsPanel:
    """Scan settings form whose choices follow the selected device.

    The photo tab scans the full A4 frame of the flatbed, so its panel has
    neither source nor paper choice.
    """

    def __init__(self, preferred_dpi: int, documents: bool = True) -> None:
        """Create the combo boxes.

        Args:
            preferred_dpi: Resolution selected for a new device.
            documents: Offer source and paper (documents tab).
        """
        self.source = QComboBox() if documents else None
        self.paper = QComboBox() if documents else None
        self.mode = QComboBox()
        self.resolution = QComboBox()
        self._preferred_dpi = preferred_dpi
        if self.paper is not None:
            fill(self.paper, [(p.name, p) for p in DOCUMENT_FORMATS])

    def add_rows(self, form: QFormLayout,
                 wrap: Callable[[str, QWidget], QWidget] | None = None) -> None:
        """Add the combo boxes to a form.

        Args:
            form: Target form.
            wrap: Wraps a combo box by its setting name (``source``, ``colour``,
                ``resolution``, ``paper``), e.g. with a source badge.
        """
        rows = (("Source:", "source", self.source), ("Colour:", "colour", self.mode),
                ("Resolution:", "resolution", self.resolution), ("Paper:", "paper", self.paper))
        for label, name, combo in rows:
            if combo is not None:
                form.addRow(label, combo if wrap is None else wrap(name, combo))

    def _combos(self) -> list[QComboBox]:
        """Return the combos that follow the device.

        Returns:
            Source (if any), mode and resolution.
        """
        return [c for c in (self.source, self.mode, self.resolution) if c is not None]

    def apply(self, options: DeviceOptions | None) -> None:
        """Offer what the device supports.

        Args:
            options: Device options, or None while unknown.
        """
        if options is None:
            for combo in self._combos():
                combo.clear()
            return
        if self.source is not None:
            fill(self.source, enum_items(options.available_sources()), ScanSource.FLATBED)
        fill(self.mode, enum_items(options.available_modes()), ColorMode.COLOR)
        dpis = list(options.resolutions) or [self._preferred_dpi]  # device default
        fill(self.resolution, [(f"{d} dpi", d) for d in dpis],
             min(dpis, key=lambda d: abs(d - self._preferred_dpi)))

    def ready(self) -> bool:
        """Whether every combo has a selection.

        Returns:
            True if a scan can start.
        """
        return all(c.currentData() is not None for c in self._combos())

    def settings(self) -> ScanSettings:
        """Return the chosen settings; without source/paper: flatbed and A4.

        Returns:
            The settings.
        """
        source = self.source.currentData() if self.source is not None else ScanSource.FLATBED
        paper = self.paper.currentData() if self.paper is not None else A4
        return ScanSettings(source, self.mode.currentData(), self.resolution.currentData(),
                            paper)
