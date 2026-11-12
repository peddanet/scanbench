"""Common behaviour of the scanning tabs (Template Method)."""

from collections.abc import Callable
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QWidget

from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.scan_progress import ScanProgress
from scanbench.infrastructure.scan_observer import ScanObserver
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
        self._ctx.progress.start(text, cancellable=False)
        self._ctx.runner.run(work, done, lambda error: self.finish(f"Error: {error}"))

    def run_scan(self, text: str, scan: Callable[[ScanObserver], Any],
                 done: Callable[[Any], None]) -> None:
        """Run a scan with live progress, partial image and cancel button.

        Args:
            text: Status text while the scan runs.
            scan: Function doing the scan with the given observer.
            done: Called with the result in the GUI thread.
        """
        self.message.emit(text)
        for button in self.buttons.values():
            button.setEnabled(False)
        cancel = self._ctx.progress.start(text)

        def work(report: Callable[[object], None]) -> Any:
            """Scan and forward progress and image to the GUI thread.

            Args:
                report: Sends one item to the GUI thread.

            Returns:
                The scan result.
            """
            return scan(ScanObserver(progress=report, image=report, cancel=cancel))
        self._ctx.runner.run(work, done, lambda error: self.finish(f"Error: {error}"),
                             self._show_progress)

    def _show_progress(self, item: object) -> None:
        """Show a progress report or a partial image.

        Args:
            item: ``ScanProgress`` or an RGB array of the page so far.
        """
        if isinstance(item, ScanProgress):
            self._ctx.progress.update_progress(item)
        elif isinstance(item, np.ndarray):
            self.show_partial(item)

    def show_partial(self, pixels: NDArray[np.uint8]) -> None:
        """Show the page while it is being scanned (subclass hook).

        Args:
            pixels: The page so far.
        """

    def finish(self, text: str) -> None:
        """Show the outcome of a job and unlock the commands.

        Args:
            text: Status text.
        """
        self._ctx.progress.finish()
        self.message.emit(text)
        self.refresh()
