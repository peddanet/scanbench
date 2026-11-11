"""Photo-album tab: scan the full frame, confirm the frames, save the photos."""

from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from scanbench.application.photo_session import PhotoScan, PhotoSession
from scanbench.domain.crop_region import CropRegion
from scanbench.infrastructure.settings_store import SettingsStore
from scanbench.ui.photo_form import PhotoForm
from scanbench.ui.region_view import RegionView
from scanbench.ui.scan_tab import ScanTab
from scanbench.ui.tab_context import TabContext

START_TEXT = "Put photos on the glass with a little space between them."
"""Hint shown while no scan waits for confirmation."""


class PhotoTab(ScanTab):
    """Scan album pages one after another and cut out the photos.

    Workflow per page: *Scan* covers the whole A4 frame, the detector
    proposes frames, the user corrects them (right-click on a frame) and
    *Confirm* cuts, deskews and saves them. Only then the next scan
    starts, so every photo has been seen and confirmed.
    """

    def __init__(self, context: TabContext, session: PhotoSession,
                 settings: SettingsStore) -> None:
        """Build the widgets.

        Args:
            context: Shared collaborators.
            session: Photo session.
            settings: Persistent settings (album folder).
        """
        super().__init__(context)
        self._session = session
        self.saved: list[Path] = []
        self.form = PhotoForm(settings, context.dialogs.choose_folder)
        self.view = RegionView()
        self.info = QLabel(START_TEXT)
        self.info.setWordWrap(True)
        self.buttons.update({key: QPushButton(text) for key, text in (
            ("scan", "Scan page"), ("confirm", "Confirm photos"), ("discard", "Discard scan"),
            ("detect", "Detect again"), ("print", "Print saved photos ..."))})
        controls = QVBoxLayout()
        controls.addWidget(self.form)
        for button in self.buttons.values():
            controls.addWidget(button)
        controls.addWidget(self.info)
        controls.addStretch(1)
        side = QWidget()
        side.setLayout(controls)
        side.setMaximumWidth(380)
        layout = QHBoxLayout(self)
        layout.addWidget(side)
        layout.addWidget(self.view, 1)
        for key, action in (("scan", self.scan), ("confirm", self.confirm),
                            ("discard", self.discard), ("detect", self.detect_again),
                            ("print", self.print_photos)):
            self.buttons[key].clicked.connect(action)
        self.view.regions_changed.connect(self._edited)
        context.devices.options_changed.connect(self.update_options)
        self.update_options()

    def waiting(self) -> bool:
        """Whether a scan waits for confirmation.

        Returns:
            True between scan and confirm or discard.
        """
        return self._session.current is not None

    def update_options(self) -> None:
        """Adapt the settings to the selected device."""
        self.form.panel.apply(self._ctx.devices.options())
        self.refresh()

    def refresh(self) -> None:
        """Enable the commands that fit the current state."""
        busy = self._ctx.runner.busy()
        waiting = self.waiting()
        self.buttons["scan"].setEnabled(not busy and not waiting and self.form.panel.ready()
                                        and self._ctx.devices.device() is not None)
        for key in ("confirm", "discard", "detect"):
            self.buttons[key].setEnabled(not busy and waiting)
        self.buttons["print"].setEnabled(not busy and bool(self.saved))

    def scan(self) -> None:
        """Scan the whole A4 frame of the flatbed and detect the photos."""
        selected = self.selected_device()
        if selected is None:
            return
        device, options = selected
        settings = self.form.panel.settings()
        snap = self.form.snap.isChecked()
        self.run_job(f"Scanning the full A4 frame at {settings.resolution} dpi ...",
                     lambda: self._session.scan(device, settings, options, snap),
                     self._detected)

    def detect_again(self) -> None:
        """Run the detection again, e.g. after changing the size fitting."""
        current = self._session.current
        if current is None:
            return
        snap = self.form.snap.isChecked()
        self.run_job("Detecting photos ...",
                     lambda: self._session.detect(current.path, current.dpi, snap),
                     self._detected)

    def _detected(self, scan: PhotoScan) -> None:
        """Show the proposal and wait for confirmation.

        Args:
            scan: Scan with proposed regions.
        """
        self.view.show_scan(scan.path, scan.dpi, scan.regions)
        self.buttons["confirm"].setText(f"Confirm {len(scan.regions)} photo(s)")
        self.info.setText(f"{len(scan.regions)} photo(s) found. Check the frames: right-click "
                          "to rotate, straighten, fit or delete; drag to move; right-click "
                          "on free space to add a frame. Then confirm.")
        self.finish(f"{len(scan.regions)} photo(s) detected; please confirm")

    def _edited(self, regions: list[CropRegion]) -> None:
        """Take over the user's corrections.

        Args:
            regions: Edited regions.
        """
        if self._session.current is not None:
            self._session.current.regions = list(regions)
            self.buttons["confirm"].setText(f"Confirm {len(regions)} photo(s)")

    def confirm(self) -> None:
        """Cut, deskew and save the confirmed photos."""
        album = self.form.album_options()
        self.run_job(f"Saving photos to {album.folder} ...",
                     lambda: self._session.accept(album), self._saved)

    def _saved(self, written: list[Path]) -> None:
        """Report the saved photos and get ready for the next page.

        Args:
            written: The photo files.
        """
        self.saved = written
        self.view.show_scan(None, 0, [])
        self.buttons["confirm"].setText("Confirm photos")
        names = f"{written[0].name} ... {written[-1].name}" if written else "nothing"
        self.info.setText(f"Saved {len(written)} photo(s): {names}. Put the next page on the "
                          "glass and scan.")
        self.finish(f"Saved {len(written)} photo(s) in {self.form.album.text()}")

    def discard(self) -> None:
        """Drop the scan without saving."""
        self._session.discard()
        self.view.show_scan(None, 0, [])
        self.info.setText(START_TEXT)
        self.finish("Scan discarded")

    def print_photos(self) -> None:
        """Print the photos of the last confirmed page."""
        job = self._ctx.dialogs.ask_print(self, f"Print {len(self.saved)} photo(s)", True)
        if job is None:
            return
        files, cups = list(self.saved), self._ctx.cups
        self.run_job(f"Printing on {job.printer} ...",
                     lambda: cups.print_files(job.printer, files, job.copies, job.options),
                     lambda job_id: self.finish(f"Print job {job_id} sent"))
