"""Dialog to choose printer, copies and driver options (CUPS)."""

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QLabel, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from scanbench.domain.print_job import PrintJob
from scanbench.domain.scan_error import ScanError
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.ui.option_form import OptionForm


class PrintDialog(QDialog):
    """Show every CUPS printer and the options its driver offers.

    The option list is read with ``lpoptions -l`` for the selected printer,
    so the trays (photo tray, CD/DVD tray) and sizes are exactly those of the
    driver (PPD); they are shown with readable labels, photo sizes marked.
    Only changed options are sent with the job.
    """

    def __init__(self, cups: CupsClient, title: str, parent: QWidget | None = None,
                 photos: bool = False) -> None:
        """Build the dialog and load the printers.

        Args:
            cups: CUPS adapter.
            title: Window title, e.g. what is printed.
            parent: Parent widget.
            photos: Preselect "fit to page" for photo prints.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(520, 560)
        self._cups = cups
        self.printer = QComboBox()
        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        self.fit = QCheckBox("Scale to fit the page")
        self.fit.setChecked(photos)
        self.options = OptionForm()
        self.error = QLabel()
        self.error.setWordWrap(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._arrange(buttons)
        self.printer.currentIndexChanged.connect(self._load_options)
        self._load_printers()

    def _arrange(self, buttons: QDialogButtonBox) -> None:
        """Lay out the widgets.

        Args:
            buttons: OK and Cancel.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.options)
        top = QFormLayout()
        top.addRow("Printer:", self.printer)
        top.addRow("Copies:", self.copies)
        top.addRow("", self.fit)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(QLabel("Driver options:"))
        layout.addWidget(scroll, 1)
        layout.addWidget(self.options.hint)
        layout.addWidget(self.error)
        layout.addWidget(buttons)

    def _load_printers(self) -> None:
        """Fill the printer list; the default printer is selected."""
        try:
            printers = self._cups.printers()
        except ScanError as exc:
            printers = []
            self.error.setText(str(exc))
        self.printer.blockSignals(True)
        for info in printers:
            self.printer.addItem(f"{info.name} (default)" if info.is_default else info.name,
                                 info.name)
            if info.is_default:
                self.printer.setCurrentIndex(self.printer.count() - 1)
        self.printer.blockSignals(False)
        if not printers and not self.error.text():
            self.error.setText("No printer is set up in CUPS (see 'lpstat -e').")
        self.ok_button.setEnabled(bool(printers))
        self._load_options()

    def _load_options(self) -> None:
        """Show the driver options of the selected printer."""
        name = self.printer.currentData()
        try:
            options = self._cups.options(str(name)) if name else []
        except ScanError as exc:
            options = []
            self.error.setText(str(exc))
        self.options.show_options(options)

    def job(self) -> PrintJob:
        """Return the choices as a print job.

        Returns:
            Printer, copies and the options that differ from the defaults.
        """
        options = self.options.changed()
        if self.fit.isChecked():
            options["fit-to-page"] = ""
        return PrintJob(str(self.printer.currentData() or ""), self.copies.value(), options)
