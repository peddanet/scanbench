"""Callbacks through which a running scan reports progress and can be cancelled."""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from scanbench.domain.scan_progress import ScanProgress


@dataclass
class ScanObserver:
    """Receiver of progress reports and of the partial image (Observer).

    The callbacks run in the scanning thread; the GUI forwards them to its
    own thread.

    Attributes:
        progress: Receives progress reports.
        image: Receives the partial image of the current page (flatbed only).
        cancel: Set this event to stop the scan.
        interval: Seconds between two reports.
    """

    progress: Callable[[ScanProgress], None] | None = None
    image: Callable[[NDArray[np.uint8]], None] | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    interval: float = 0.4
