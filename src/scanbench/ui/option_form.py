"""Form with one combo box per printer driver option."""

from PySide6.QtWidgets import QComboBox, QFormLayout, QWidget

from scanbench.domain.printer_option import PrinterOption

IMPORTANT_OPTIONS = ("InputSlot", "MediaType", "PageSize", "ColorModel", "CNIJPrintQuality",
                     "cupsPrintQuality", "Duplex", "BorderlessPrint")
"""Options shown first: paper source (photo tray, cassette, CD/DVD tray),
media, size, colour and quality. The rest follows in driver order."""


class OptionForm(QWidget):
    """Edit the driver options of one printer; reports only changed values."""

    def __init__(self) -> None:
        """Create the empty form."""
        super().__init__()
        self._layout = QFormLayout(self)
        self._defaults: dict[str, str] = {}
        self.choices: dict[str, QComboBox] = {}

    def show_options(self, options: list[PrinterOption]) -> None:
        """Replace the rows by the given options, important ones first.

        Args:
            options: Driver options of the printer.
        """
        while self._layout.rowCount():
            self._layout.removeRow(0)
        self.choices.clear()
        self._defaults.clear()
        rank = {key: number for number, key in enumerate(IMPORTANT_OPTIONS)}
        for option in sorted(options, key=lambda o: rank.get(o.key, len(rank))):
            combo = QComboBox()
            combo.addItems(list(option.choices))
            if option.default in option.choices:
                combo.setCurrentText(option.default)
            self._layout.addRow(f"{option.label}:", combo)
            self.choices[option.key] = combo
            self._defaults[option.key] = option.default

    def changed(self) -> dict[str, str]:
        """Return the options whose value differs from the driver default.

        Returns:
            Key and chosen value.
        """
        return {key: combo.currentText() for key, combo in self.choices.items()
                if combo.currentText() != self._defaults.get(key)}
