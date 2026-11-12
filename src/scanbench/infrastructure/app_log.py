"""Log file of the program: start and end, status texts, errors, hard crashes.

``scanbench.log`` (rotated at 1 MB, 5 files) receives one line per status
text and every error with its Python traceback; ``crash.log`` receives the
call stacks of all threads when the process dies hard (segmentation fault,
abort), written by :mod:`faulthandler`.
"""

import faulthandler
import logging
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import IO

LOGGER = "scanbench"
"""Name of the program's logger."""

LOG_FILE, CRASH_FILE = "scanbench.log", "crash.log"
"""File names in the log directory."""

MAX_BYTES, BACKUPS = 1_000_000, 4
"""Rotation: 1 MB per file, the current file plus 4 older ones."""


class AppLog:
    """Set up and tear down the log files of one program run."""

    def __init__(self, log_dir: Path) -> None:
        """Store the directory.

        Args:
            log_dir: E.g. ``$SCANBENCH_HOME/logs``.
        """
        self.log_dir = log_dir
        self._handler: RotatingFileHandler | None = None
        self._crash: IO[str] | None = None
        self._previous_hook = sys.excepthook

    def start(self, version: str) -> logging.Logger:
        """Open the log files and record the start.

        Args:
            version: Version of the running program.

        Returns:
            The program's logger.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger(LOGGER)
        logger.setLevel(logging.INFO)
        self._handler = RotatingFileHandler(self.log_dir / LOG_FILE, maxBytes=MAX_BYTES,
                                            backupCount=BACKUPS, encoding="utf-8")
        self._handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(threadName)s %(message)s"))
        logger.addHandler(self._handler)
        # stays open for the whole run: faulthandler writes into it while dying
        self._crash = (self.log_dir / CRASH_FILE).open(  # pylint: disable=consider-using-with
            "a", encoding="utf-8")
        faulthandler.enable(self._crash, all_threads=True)
        self._previous_hook = sys.excepthook
        sys.excepthook = self._uncaught
        logger.info("scanbench %s started (Python %s, %s)", version,
                    platform.python_version(), platform.platform())
        return logger

    def _uncaught(self, kind: type[BaseException], error: BaseException,
                  trace: TracebackType | None) -> None:
        """Record an exception nobody caught (e.g. in a Qt slot), then pass it on.

        Args:
            kind: Exception class.
            error: The exception.
            trace: Its traceback.
        """
        logging.getLogger(LOGGER).critical("uncaught exception", exc_info=(kind, error, trace))
        self._previous_hook(kind, error, trace)

    def stop(self) -> None:
        """Record the end and close the files."""
        logger = logging.getLogger(LOGGER)
        logger.info("scanbench ended")
        sys.excepthook = self._previous_hook
        if self._crash is not None:
            faulthandler.enable(sys.stderr, all_threads=True)
            self._crash.close()
            self._crash = None
        if self._handler is not None:
            logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None
