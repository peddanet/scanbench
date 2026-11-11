"""Run slow jobs (scanning, saving, printing) outside the GUI thread."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


class _Relay(QObject):
    """Carries the result of a job back into the GUI thread."""

    done = Signal(object)
    failed = Signal(str)


class _Job(QRunnable):
    """A callable executed by the thread pool."""

    def __init__(self, work: Callable[[], Any], relay: _Relay) -> None:
        """Store the work.

        Args:
            work: Function to run.
            relay: Object whose signals report the outcome.
        """
        super().__init__()
        self._work = work
        self._relay = relay

    def run(self) -> None:
        """Run the work and report its result or error."""
        try:
            result = self._work()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Any error must reach the user; a lost exception would hang the tab.
            self._emit(False, str(exc) or type(exc).__name__)
        else:
            self._emit(True, result)

    def _emit(self, success: bool, value: Any) -> None:
        """Report the outcome unless the receiver is already gone.

        Args:
            success: True for a result, False for an error message.
            value: Result or message.
        """
        try:
            (self._relay.done if success else self._relay.failed).emit(value)
        except RuntimeError:
            pass  # window closed while the job ran; nobody waits for the result


class TaskRunner(QObject):
    """Start jobs in a thread pool and deliver results in the GUI thread.

    ``started`` and ``finished`` are emitted per job, so the main window can
    count running jobs and postpone a release switch until it is idle.
    """

    started = Signal()
    finished = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        """Create the pool.

        Args:
            parent: Qt parent.
        """
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._relays: set[_Relay] = set()

    def busy(self) -> bool:
        """Whether a job is running.

        Returns:
            True while at least one job runs.
        """
        return bool(self._relays)

    def run(self, work: Callable[[], Any], on_done: Callable[[Any], None],
            on_error: Callable[[str], None]) -> None:
        """Run a job; the callbacks run in the GUI thread.

        Args:
            work: Function to run in the background.
            on_done: Receives the result.
            on_error: Receives the error message.
        """
        relay = _Relay()
        self._relays.add(relay)

        def finish() -> None:
            """Forget the relay and report the end of the job."""
            self._relays.discard(relay)
            self.finished.emit()

        # finish first: the callbacks then already see the runner as idle.
        relay.done.connect(finish)
        relay.failed.connect(finish)
        relay.done.connect(on_done)
        relay.failed.connect(on_error)
        self.started.emit()
        self._pool.start(_Job(work, relay))

    def wait(self, msecs: int = 30000) -> bool:
        """Wait until all jobs are done (used at shutdown and in tests).

        Args:
            msecs: Maximum waiting time.

        Returns:
            True if all jobs ended in time.
        """
        return self._pool.waitForDone(msecs)
