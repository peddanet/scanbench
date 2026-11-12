"""Progress of scans and processing in the status bar, with a cancel button."""

import threading

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QWidget

from scanbench.domain.scan_progress import ScanProgress


class ProgressPanel(QWidget):
    """Shows what runs: text, a progress bar and **Cancel**.

    The bar shows the progress of the current page; the text shows page
    number, elapsed and remaining time. Without a percentage (e.g. while
    saving) the bar runs as a busy indicator.
    """

    def __init__(self) -> None:
        """Build the hidden panel."""
        super().__init__()
        self.label = QLabel()
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setFixedWidth(220)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_event = threading.Event()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.meter)
        layout.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(self.cancel)
        self.hide()

    def start(self, text: str, cancellable: bool = True) -> threading.Event:
        """Show the panel for a new job.

        Args:
            text: What runs.
            cancellable: Offer the cancel button.

        Returns:
            The event the job checks for cancellation.
        """
        self.cancel_event = threading.Event()
        self.label.setText(text)
        self.meter.setRange(0, 0)          # busy until the first percentage arrives
        self.cancel_button.setEnabled(cancellable)
        self.cancel_button.setVisible(cancellable)
        self.show()
        return self.cancel_event

    def update_progress(self, progress: ScanProgress) -> None:
        """Show a progress report.

        Args:
            progress: The report.
        """
        if self.meter.maximum() == 0:
            self.meter.setRange(0, 100)
        self.meter.setValue(round(progress.percent))
        self.label.setText(progress.text())

    def cancel(self) -> None:
        """Ask the running job to stop."""
        self.cancel_event.set()
        self.cancel_button.setEnabled(False)
        self.label.setText("Cancelling ...")

    def finish(self) -> None:
        """Hide the panel."""
        self.hide()
