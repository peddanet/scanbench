"""What every scanning tab needs from its surroundings (Parameter Object)."""

from dataclasses import dataclass

from scanbench.infrastructure.cups_client import CupsClient
from scanbench.ui.device_bar import DeviceBar
from scanbench.ui.dialogs import Dialogs
from scanbench.ui.progress_panel import ProgressPanel
from scanbench.ui.task_runner import TaskRunner


@dataclass(frozen=True)
class TabContext:
    """Shared collaborators of the tabs.

    Attributes:
        devices: Scanner selection.
        runner: Background job runner.
        cups: CUPS adapter for printing.
        dialogs: Modal questions (file, folder, printer).
        progress: Progress display in the status bar.
    """

    devices: DeviceBar
    runner: TaskRunner
    cups: CupsClient
    dialogs: Dialogs
    progress: ProgressPanel
