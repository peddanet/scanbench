"""Common behaviour of the scanning tabs (Template Method)."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QWidget

from scanbench.domain.device_options import DeviceOptions
from scanbench.ui.tab_context import TabContext


class ScanTab(QWidget):
    """Base of the tabs: status messages, button locking, background jobs.

    Subclasses fill ``buttons`` and implement :meth:`refresh`, which
    enables the commands that fit the current state.
    """

    message = Signal(str)
    """A status text for the status bar."""

    def __init__(self, context: TabContext) -> None:
        """Store the shared collaborators.

        Args:
            context: Shared collaborators.
        """
        super().__init__()
        self._ctx = context
        self.buttons: dict[str, QPushButton] = {}

    def refresh(self) -> None:
        """Enable the commands that fit the current state (subclass hook)."""
        raise NotImplementedError

    def selected_device(self) -> tuple[str, DeviceOptions] | None:
        """Return the selected device and its options.

        Returns:
            Device name and options, or None while unknown.
        """
        device, options = self._ctx.devices.device(), self._ctx.devices.options()
        return None if device is None or options is None else (device, options)

    def run_job(self, text: str, work: Callable[[], Any], done: Callable[[Any], None]) -> None:
        """Lock the commands, run a job in the background and report errors.

        Args:
            text: Status text while the job runs.
            work: The job.
            done: Called with the result in the GUI thread.
        """
        self.message.emit(text)
        for button in self.buttons.values():
            button.setEnabled(False)
        self._ctx.runner.run(work, done, lambda error: self.finish(f"Error: {error}"))

    def finish(self, text: str) -> None:
        """Show the outcome of a job and unlock the commands.

        Args:
            text: Status text.
        """
        self.message.emit(text)
        self.refresh()
