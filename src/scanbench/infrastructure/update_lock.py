"""Prevent two updates from working on the same clone at the same time."""

import fcntl
from pathlib import Path
from types import TracebackType
from typing import IO

from scanbench.domain.update_error import UpdateError


class UpdateLock:
    """Exclusive, non-blocking file lock, used as a context manager.

    The kernel releases the lock when the process ends, so a crashed update
    never leaves a stale lock behind.
    """

    def __init__(self, path: Path) -> None:
        """Store the lock file location.

        Args:
            path: Lock file; its directory is created if needed.
        """
        self._path = path
        self._handle: IO[str] | None = None

    def __enter__(self) -> "UpdateLock":
        """Take the lock.

        Returns:
            The lock itself.

        Raises:
            UpdateError: If another update holds the lock.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("w", encoding="utf-8")  # pylint: disable=consider-using-with
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.close()
            raise UpdateError(f"another update is running (lock {self._path})") from exc
        self._handle = handle
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 traceback: TracebackType | None) -> None:
        """Release the lock.

        Args:
            exc_type: Exception type, if any.
            exc: Exception, if any.
            traceback: Traceback, if any.
        """
        if self._handle is not None:
            self._handle.close()
            self._handle = None
