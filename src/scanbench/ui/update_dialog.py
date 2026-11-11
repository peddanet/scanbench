"""Dialog that runs ``scanbench update`` and shows its staged output live."""

from PySide6.QtCore import QProcess, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QPlainTextEdit,
                               QVBoxLayout, QWidget)


class UpdateDialog(QDialog):
    """Run the update in a child process and stream its output.

    The child process is the command line of the running installation, so
    the dialog shows exactly what a terminal would show. The window stays
    responsive while gates and CI runs take their time.
    """

    succeeded = Signal()
    """Emitted when the update finished with exit status 0."""

    def __init__(self, program: str, args: list[str], parent: QWidget | None = None) -> None:
        """Build the dialog; the update starts with :meth:`start`.

        Args:
            program: Launcher to run, e.g. ``<venv>/bin/scanbench``.
            args: Arguments, e.g. ``["update", "--yes"]``.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.setWindowTitle("scanbench update")
        self.resize(900, 560)
        self.log = QPlainTextEdit(readOnly=True)
        self.log.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.status = QLabel("Running ...")
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        self.buttons.setEnabled(False)
        layout = QVBoxLayout(self)
        for widget in (self.log, self.status, self.buttons):
            layout.addWidget(widget)
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read)
        self.process.finished.connect(self._finished)
        self._program, self._args = program, args

    def start(self) -> None:
        """Start the update process."""
        self.log.appendPlainText(f"$ {self._program} {' '.join(self._args)}")
        self.process.start(self._program, self._args)

    def _read(self) -> None:
        """Append new output of the process."""
        data = self.process.readAllStandardOutput().data()
        self.log.appendPlainText(bytes(data).decode("utf-8", errors="replace").rstrip("\n"))

    def _finished(self, code: int, _status: QProcess.ExitStatus) -> None:
        """Show the result and allow closing.

        Args:
            code: Exit status of the update; a crash is reported as non-zero too.
        """
        self._read()
        self.buttons.setEnabled(True)
        if code == 0:
            self.status.setText("DONE: update complete.")
            self.succeeded.emit()
        else:
            self.status.setText(f"FAILED (exit status {code}); see the output above.")
