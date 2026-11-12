"""Factory that wires the scanning and printing parts of the GUI."""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from scanbench.application.document_session import DocumentSession
from scanbench.application.photo_session import PhotoSession
from scanbench.application.session_handover import Handover
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.infrastructure.device_cache import DeviceCache
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.scanimage_backend import ScanimageBackend
from scanbench.infrastructure.settings_files import SettingsFiles
from scanbench.infrastructure.shell import Shell
from scanbench.ui.device_bar import DeviceBar
from scanbench.ui.dialogs import Dialogs, print_asker
from scanbench.ui.document_tab import DocumentTab
from scanbench.ui.photo_tab import PhotoTab
from scanbench.ui.progress_panel import ProgressPanel
from scanbench.ui.tab_context import TabContext
from scanbench.ui.tab_settings import SettingsHub
from scanbench.ui.task_runner import TaskRunner

TEST_DEVICE_VARIABLE = "SCANBENCH_TEST_DEVICE"
"""Set to 1 to offer SANE's virtual test scanner in the device list."""

DEVICE_CACHE = "devices.json"
"""Device cache file in the cache directory."""


@dataclass
class Workbench:
    """The connected widgets of the scanning GUI.

    Attributes:
        runner: Background job runner shared by all tabs.
        devices: Scanner selection.
        documents: Documents tab.
        photos: Photo-album tab.
        progress: Progress display for the status bar.
        work: Temporary directory with the raw scans of this session.
        problems: Invalid values found in the settings files at start.
    """

    runner: TaskRunner
    devices: DeviceBar
    documents: DocumentTab
    photos: PhotoTab
    progress: ProgressPanel
    work: tempfile.TemporaryDirectory[str]
    problems: list[str] = field(default_factory=list)

    def handover(self, tab: int) -> Handover:
        """Collect the open work for the next release.

        Args:
            tab: Index of the open tab.

        Returns:
            Device, tab, waiting photo scan and document pages.
        """
        return Handover(self.devices.device(), tab, self.photos.pending(),
                        self.documents.scanned_pages())

    def restore(self, handover: Handover) -> None:
        """Continue with the work of the previous release.

        Args:
            handover: State written before the switch.
        """
        self.devices.preferred = handover.device
        if handover.photo is not None:
            self.photos.resume(handover.photo)
        if handover.pages:
            self.documents.resume(handover.pages)

    def close(self) -> None:
        """Wait for running jobs and delete the raw scans."""
        self.runner.wait()
        self.work.cleanup()


def build_workbench(paths: AppPaths, include_test: bool | None = None) -> Workbench:
    """Create adapters, sessions and tabs (Factory Method).

    Args:
        paths: Resolver of the application directories.
        include_test: Offer SANE's test scanner; None reads the environment.

    Returns:
        The workbench.
    """
    paths.cache_dir.mkdir(parents=True, exist_ok=True)
    # Lives as long as the window; Workbench.close() removes it.
    work = tempfile.TemporaryDirectory(  # pylint: disable=consider-using-with
        prefix="session-", dir=paths.cache_dir)
    work_dir = Path(work.name)
    (work_dir / "documents").mkdir()
    (work_dir / "photos").mkdir()
    shell = Shell(work_dir)
    scanner, store, cups = ScanimageBackend(shell), ImageStore(), CupsClient(shell)
    runner = TaskRunner()
    if include_test is None:
        include_test = os.environ.get(TEST_DEVICE_VARIABLE) == "1"
    devices = DeviceBar(scanner, runner, include_test,
                        DeviceCache(paths.cache_dir / DEVICE_CACHE))
    hub = SettingsHub(files=SettingsFiles(paths.config_dir))
    problems = hub.load()                        # before the tabs: they show the values
    context = TabContext(devices, runner, cups, Dialogs(print_asker(cups)), ProgressPanel(),
                         hub)
    documents = DocumentTab(
        context, DocumentSession(scanner, store, PdfWriter(shell), work_dir / "documents"))
    photos = PhotoTab(
        context, PhotoSession(scanner, PhotoDetector(), store, work_dir / "photos"))
    return Workbench(runner, devices, documents, photos, context.progress, work, problems)
