"""Common behaviour of the scanning tabs (Template Method)."""

import threading
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
        # placed by the subclass below its buttons; visible while a job can be cancelled
        self.cancel_button = QPushButton("Cancel (Esc)")
        self.cancel_button.setToolTip("Stop the running job; what is finished is kept")
        self.cancel_button.clicked.connect(context.progress.cancel)
        self.cancel_button.hide()

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

    def _lock(self, text: str, cancellable: bool) -> threading.Event:
        """Disable the commands and show the progress of a new job.

        Args:
            text: Status text while the job runs.
            cancellable: Offer Cancel and Esc.

        Returns:
            The cancel event of the job.
        """
        self.message.emit(text)
        for button in self.buttons.values():
            button.setEnabled(False)
        self.cancel_button.setVisible(cancellable)
        self.cancel_button.setEnabled(cancellable)
        return self._ctx.progress.start(text, cancellable)

    def _failed(self, error: str) -> None:
        """Report a failed or cancelled job.

        Args:
            error: Error text of the job.
        """
        cancelled = self._ctx.progress.cancel_event.is_set()
        self.finish("Cancelled" if cancelled else f"Error: {error}")

    def run_job(self, text: str, work: Callable[[], Any], done: Callable[[Any], None],
                cancellable: bool = False) -> None:
        """Lock the commands, run a job in the background and report errors.

        A cancellable job reads ``progress.cancel_event`` itself and stops at
        a safe point; ``done`` still receives what it finished.

        Args:
            text: Status text while the job runs.
            work: The job.
            done: Called with the result in the GUI thread.
            cancellable: Offer Cancel and Esc.
        """
        self._lock(text, cancellable)
        self._ctx.runner.run(work, done, self._failed)

    def run_scan(self, text: str, scan: Callable[[ScanObserver], Any],
                 done: Callable[[Any], None]) -> None:
        """Run a scan with live progress, partial image and cancel button.

        Args:
            text: Status text while the scan runs.
            scan: Function doing the scan with the given observer.
            done: Called with the result in the GUI thread.
        """
        cancel = self._lock(text, True)

        def work(report: Callable[[object], None]) -> Any:
            """Scan and forward progress and image to the GUI thread.

            Args:
                report: Sends one item to the GUI thread.

            Returns:
                The scan result.
            """
            return scan(ScanObserver(progress=report, image=report, cancel=cancel))
        self._ctx.runner.run(work, done, self._failed, self._show_progress)

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

        After a cancel the text is marked, e.g. ``Cancelled - 2 page(s) scanned``.

        Args:
            text: Status text.
        """
        progress = self._ctx.progress
        if progress.cancel_event.is_set() and not text.startswith("Cancelled"):
            text = f"Cancelled - {text}"
        progress.finish()
        self.cancel_button.hide()
        self.message.emit(text)
        self.refresh()
