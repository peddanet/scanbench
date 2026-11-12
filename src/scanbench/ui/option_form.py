"""Form with one combo box per printer driver option."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QWidget

from scanbench.domain.print_labels import choice_label, is_disc_slot, size_label
from scanbench.domain.printer_option import PrinterOption

SIZE_OPTIONS = ("PageSize", "PageRegion")
"""Options whose choices are paper sizes; photo sizes are listed after the others."""

IMPORTANT_OPTIONS = ("InputSlot", "MediaType", "PageSize", "ColorModel", "CNIJPrintQuality",
                     "cupsPrintQuality", "Duplex", "BorderlessPrint")
"""Options shown first: paper source (photo tray, cassette, CD/DVD tray),
media, size, colour and quality. The rest follows in driver order."""


def fill_choices(combo: QComboBox, option: PrinterOption) -> None:
    """Fill a combo box with readable labels; the keyword is the item data.

    Paper sizes are sorted into document sizes, a separator and photo sizes
    (marked "Photo ..."); the keyword is shown as tooltip.

    Args:
        combo: Empty combo box.
        option: The driver option.
    """
    choices = list(option.choices)
    if option.key in SIZE_OPTIONS:
        photos = [c for c in choices if size_label(c)[1]]
        others = [c for c in choices if c not in photos]
        choices = others + photos
    for keyword in choices:
        if option.key in SIZE_OPTIONS and size_label(keyword)[1] and combo.count() and \
                not size_label(str(combo.itemData(combo.count() - 1)))[1]:
            combo.insertSeparator(combo.count())
        combo.addItem(choice_label(option.key, keyword), keyword)
        combo.setItemData(combo.count() - 1, f"Driver keyword: {keyword}",
                          Qt.ItemDataRole.ToolTipRole)
    wanted = combo.findData(option.default)
    if wanted >= 0:
        combo.setCurrentIndex(wanted)


class OptionForm(QWidget):
    """Edit the driver options of one printer; reports only changed values."""

    def __init__(self) -> None:
        """Create the empty form."""
        super().__init__()
        self._layout = QFormLayout(self)
        self._defaults: dict[str, str] = {}
        self.choices: dict[str, QComboBox] = {}
        # placed by the dialog below the form: a note on missing trays
        self.hint = QLabel()
        self.hint.setWordWrap(True)

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
            fill_choices(combo, option)
            self._layout.addRow(f"{option.label}:", combo)
            self.choices[option.key] = combo
            self._defaults[option.key] = option.default
        slots = next((o for o in options if o.key == "InputSlot"), None)
        self.hint.setText("" if slots is None or any(is_disc_slot(c) for c in slots.choices)
                          else "The driver of this printer offers no CD/DVD tray. "
                          "Printing on discs needs a driver that knows the tray "
                          "(user guide, section 7).")

    def changed(self) -> dict[str, str]:
        """Return the options whose value differs from the driver default.

        Returns:
            Key and chosen value.
        """
        return {key: str(combo.currentData()) for key, combo in self.choices.items()
                if combo.currentData() != self._defaults.get(key)}
