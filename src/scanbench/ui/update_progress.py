"""Follow the output of ``scanbench update`` to show a progress bar."""

import re
from dataclasses import dataclass

_STEP = re.compile(r"^-- \[(\d+)\] (.+?)\s*$")
_GATE = re.compile(r"^-- \[(\d)\] (\w+)\s.*\s(PASS|FAIL|skipped)\b")
_PENDING = re.compile(r"^\s*pending: (.+)$")

STEPS_PER_RELEASE = 5
"""Steps per archive: apply, gates, pull request into main, tag, back-merge."""

GATES = 6
"""Number of quality gates (privacy, format, lint, types, security, tests)."""


@dataclass
class UpdateProgress:
    """State of a running update, read from its output lines.

    Attributes:
        step: Number of the current step, 0 before the first.
        total: Expected number of steps (read state, per archive 5, install).
        title: Title of the current step.
        gates: Quality gates finished in the current gate run.
        started: Start time (``time.monotonic``) for the elapsed time.
    """

    step: int = 0
    total: int = 2
    title: str = "starting"
    gates: int = 0
    started: float = 0.0

    def feed(self, line: str) -> bool:
        """Read one output line.

        Args:
            line: Line of the update output.

        Returns:
            True if the state changed.
        """
        if (gate := _GATE.match(line)) is not None:
            self.gates = int(gate[1]) + 1
            return True
        if (pending := _PENDING.match(line)) is not None:
            count = 0 if pending[1].strip() == "none" else len(pending[1].split(","))
            self.total = 2 + STEPS_PER_RELEASE * count
            return True
        if (step := _STEP.match(line)) is not None:
            self.step, self.title, self.gates = int(step[1]), step[2], 0
            self.total = max(self.total, self.step)
            return True
        return False

    def text(self) -> str:
        """Describe the state in one line.

        Returns:
            E.g. ``Step 3 of 7: 0.2.5: quality gates (local) - 4 of 6 gates``.
        """
        gates = f" - {self.gates} of {GATES} gates" if self.gates else ""
        return f"Step {self.step} of {self.total}: {self.title}{gates}"

    def percent(self) -> int:
        """Return the share of finished steps.

        Returns:
            0 to 100.
        """
        done = max(0, self.step - 1) + (self.gates / GATES if self.gates else 0.0)
        return min(100, round(100 * done / self.total))
