"""Bounded wait for child processes started by tests.

A test must never hang the gate run: every wait has a time limit, and a child
that does not end in time is killed and reported with its last output.
"""

import subprocess

import pytest

LIMIT = 30.0
"""Default time limit in seconds."""


def _tail(data: bytes | None, lines: int = 10) -> str:
    """Return the last lines of a child's output.

    Args:
        data: Raw output, None if not captured.
        lines: Number of lines to keep.

    Returns:
        The decoded tail, or ``(none)``.
    """
    text = (data or b"").decode("utf-8", errors="replace").rstrip()
    return "\n".join(text.splitlines()[-lines:]) or "(none)"


def finish(process: "subprocess.Popen[bytes]", limit: float = LIMIT) -> tuple[bytes, bytes]:
    """Wait for a child with a time limit.

    Args:
        process: Child started with ``stdout``/``stderr`` pipes (or none).
        limit: Seconds to wait.

    Returns:
        Standard output and standard error of the child.
    """
    try:
        out, err = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
        pytest.fail(f"child {process.args!r} did not end within {limit:g} s\n"
                    f"last stdout:\n{_tail(out)}\nlast stderr:\n{_tail(err)}")
    return out or b"", err or b""
