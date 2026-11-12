"""Tests of the log files."""

import logging
import sys
from pathlib import Path

from scanbench.infrastructure.app_log import CRASH_FILE, LOG_FILE, LOGGER, AppLog


def test_log_records_start_errors_and_end(tmp_path: Path) -> None:
    """Start, an uncaught exception with traceback and the end are written.

    Args:
        tmp_path: Temporary directory of the test.
    """
    previous = sys.excepthook
    log = AppLog(tmp_path / "logs")
    caught: list[str] = []
    sys.excepthook = lambda kind, error, trace: caught.append(str(error))
    try:
        logger = log.start("9.9.9")
        logger.info("status: scanning")
        try:
            raise ValueError("boom")
        except ValueError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
        log.stop()
        log.stop()                                   # a second stop does nothing
    finally:
        sys.excepthook = previous
    text = (tmp_path / "logs" / LOG_FILE).read_text(encoding="utf-8")
    assert "scanbench 9.9.9 started" in text and "status: scanning" in text
    assert "uncaught exception" in text and "ValueError: boom" in text
    assert "scanbench ended" in text and caught == ["boom"]
    assert (tmp_path / "logs" / CRASH_FILE).exists()
    assert not logging.getLogger(LOGGER).handlers
