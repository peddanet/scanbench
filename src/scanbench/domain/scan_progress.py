"""Progress of a running scan, as reported to the user."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanProgress:
    """One progress report.

    Attributes:
        page: Number of the page being scanned, from 1.
        pages: Number of pages if known (flatbed: 1), else None (feeder).
        percent: Progress of the current page, 0 to 100.
        elapsed: Seconds since the scan started.
        done_pages: Pages already finished.
    """

    page: int
    pages: int | None
    percent: float
    elapsed: float
    done_pages: int = 0

    def remaining(self) -> float | None:
        """Estimate the remaining seconds of the current page.

        Returns:
            Seconds, or None while the estimate is meaningless.
        """
        if self.pages != 1 or self.percent < 3:
            return None
        return self.elapsed * (100 - self.percent) / self.percent

    def text(self) -> str:
        """Describe the progress for the status bar.

        Returns:
            E.g. ``Page 2 of ? · 45 % · 0:12 · about 0:15 left``.
        """
        total = "?" if self.pages is None else str(self.pages)
        minutes, seconds = divmod(int(self.elapsed), 60)
        parts = [f"Page {self.page} of {total}", f"{self.percent:.0f} %",
                 f"{minutes}:{seconds:02d}"]
        left = self.remaining()
        if left is not None:
            left_min, left_sec = divmod(int(left + 0.5), 60)
            parts.append(f"about {left_min}:{left_sec:02d} left")
        return " · ".join(parts)
