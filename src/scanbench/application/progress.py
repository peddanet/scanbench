"""Numbered progress output and the closing summary of a release workflow."""

from collections.abc import Callable


class Progress:
    """Announce steps as numbered stages and collect CI runs for the summary.

    The output format matches ``tools/check.sh``: ``-- [n] title``. The
    summary lists every CI run with event, purpose and URL, and is printed
    on success and on failure, so the user always sees where things stand.
    """

    def __init__(self, out: Callable[[str], object]) -> None:
        """Store the output function.

        Args:
            out: Function that prints one line.
        """
        self._out = out
        self._step = 0
        self.runs: list[tuple[str, str, str]] = []

    def header(self, title: str) -> None:
        """Print a section rule.

        Args:
            title: Text inside the rule.
        """
        self._out(f"==== {title} " + "=" * max(4, 72 - len(title)))

    def step(self, title: str) -> None:
        """Announce the next step.

        Args:
            title: What the step does.
        """
        self._step += 1
        self._out(f"-- [{self._step}] {title}")

    def info(self, text: str) -> None:
        """Print an indented detail line.

        Args:
            text: The detail.
        """
        self._out(f"       {text}")

    def ci(self, label: str, purpose: str, url: str) -> None:
        """Record and announce a CI run.

        Args:
            label: Short name, e.g. ``CI 1/3``.
            purpose: What the run checks.
            url: Link to the run or pull request.
        """
        self.runs.append((label, purpose, url))
        self.info(f"{label}: {purpose} -> {url}")

    def summary(self, outcome: str) -> None:
        """Print the table of CI runs and the outcome.

        Args:
            outcome: Final sentence, e.g. ``DONE: scanbench 0.2.0 installed``.
        """
        self.header("CI runs")
        for label, purpose, url in self.runs or [("-", "no CI run", "-")]:
            self._out(f"   {label:<8} {purpose:<44} {url}")
        self.header(outcome)
