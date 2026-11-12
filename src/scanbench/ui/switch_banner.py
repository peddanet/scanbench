"""Notice above the tabs while a newly installed release waits for the switch."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class SwitchBanner(QFrame):
    """Shows that a new release is installed, why the window still waits, and
    offers **Switch now**.

    The banner stays visible until the switch happens; the status bar text
    would be overwritten by the next command.
    """

    switch_now = Signal()
    """The user wants to switch without waiting (the running job is cancelled)."""

    def __init__(self) -> None:
        """Build the hidden banner."""
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("SwitchBanner { background: palette(highlight); }"
                           "QLabel { color: palette(highlighted-text); }")
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.button = QPushButton("Switch now")
        self.button.setToolTip("Cancel the running job and switch; open work is handed over")
        layout = QHBoxLayout(self)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.button)
        self.button.clicked.connect(self.switch_now)
        self.pending: tuple[str, bool] | None = None
        self.hide()

    def wait_for(self, version: str, automatic: bool, reason: str) -> None:
        """Show the waiting switch and its reason.

        Args:
            version: The installed release.
            automatic: Switch without asking when idle.
            reason: Why the window waits, e.g. ``the running job is done``.
        """
        self.pending = (version, automatic)
        self.label.setText(f"scanbench {version} is installed. The window switches to it "
                           f"when {reason}.")
        self.show()

    def take(self) -> tuple[str, bool] | None:
        """Return the waiting switch and hide the banner.

        Returns:
            Version and automatic flag, or None if nothing waits.
        """
        pending, self.pending = self.pending, None
        self.hide()
        return pending
