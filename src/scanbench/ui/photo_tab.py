"""Photo-album tab: scan the full frame, confirm the frames, save the photos."""

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from scanbench.application.photo_session import PhotoScan, PhotoSession
from scanbench.domain.crop_region import CropRegion
from scanbench.infrastructure.settings_store import SettingsStore
from scanbench.ui.photo_form import PhotoForm
from scanbench.ui.frame_editor import FrameEditor
from scanbench.ui.scan_tab import ScanTab
from scanbench.ui.tab_context import TabContext

START_TEXT = ("Put photos on the glass. 'Preview scan' finds them quickly; check the frames, "
              "then 'Scan photos' scans only their area at the chosen resolution.")
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
        self.editor = FrameEditor(START_TEXT)
        self.buttons.update({key: QPushButton(text) for key, text in (
            ("preview", "Preview scan"), ("area", "Scan photos"),
            ("confirm", "Confirm photos"), ("discard", "Discard scan"),
            ("detect", "Detect again"), ("print", "Print saved photos ..."))})
        self.buttons["preview"].setToolTip(
            "Quick scan of the whole glass at the lowest resolution to find the photos")
        self.buttons["area"].setToolTip(
            "Scan only the area around the frames of the preview, at the chosen resolution")
        controls = QVBoxLayout()
        controls.addWidget(self.form)
        for button in self.buttons.values():
            controls.addWidget(button)
        controls.addStretch(1)
        side = QWidget()
        side.setLayout(controls)
        side.setMaximumWidth(380)
        layout = QHBoxLayout(self)
        layout.addWidget(side)
        layout.addWidget(self.editor, 1)
        for key, action in (("preview", self._preview), ("area", self._scan_area),
                            ("confirm", self.confirm),
                            ("discard", self.discard), ("detect", self.detect_again),
                            ("print", self.print_photos)):
            self.buttons[key].clicked.connect(action)
        self.editor.view.regions_changed.connect(self._edited)
        context.devices.options_changed.connect(self.update_options)
        self.update_options()

    def pending(self) -> PhotoScan | None:
        """Return the scan waiting for confirmation.

        Returns:
            The scan, or None.
        """
        return self._session.current

    def resume(self, scan: PhotoScan) -> None:
        """Show a scan taken over from the previous release, waiting for confirmation.

        Args:
            scan: The scan with its frames.
        """
        self._session.current = scan
        self._detected(scan)

    def update_options(self) -> None:
        """Adapt the settings to the selected device."""
        self.form.panel.apply(self._ctx.devices.options())
        self.refresh()

    def refresh(self) -> None:
        """Enable the commands that fit the current state."""
        busy = self._ctx.runner.busy()
        current = self._session.current
        can_scan = (not busy and self.form.panel.ready()
                    and self._ctx.devices.device() is not None)
        is_preview = current is not None and current.preview
        self.buttons["preview"].setEnabled(can_scan and (current is None or is_preview))
        has_frames = current is not None and bool(current.regions)
        self.buttons["area"].setEnabled(can_scan and is_preview and has_frames)
        self.buttons["confirm"].setEnabled(not busy and current is not None and not is_preview)
        for key in ("discard", "detect"):
            self.buttons[key].setEnabled(not busy and current is not None)
        self.buttons["print"].setEnabled(not busy and bool(self.saved))

    def _preview(self) -> None:
        """Scan the whole glass quickly to locate the photos."""
        selected = self.selected_device()
        if selected is None:
            return
        device, options = selected
        settings, snap = self.form.panel.settings(), self.form.snap.isChecked()
        self.run_scan("Preview scan of the whole glass ...",
                      lambda observer: self._session.preview(device, settings, options, snap,
                                                             observer),
                      self._detected)

    def _scan_area(self) -> None:
        """Scan only the area around the frames at the chosen resolution."""
        selected = self.selected_device()
        if selected is None:
            return
        device, options = selected
        settings = self.form.panel.settings()
        self.run_scan(f"Scanning the photos at {settings.resolution} dpi ...",
                      lambda observer: self._session.scan_area(device, settings, options,
                                                               observer),
                      self._detected)

    def show_partial(self, pixels: NDArray[np.uint8]) -> None:
        """Show the glass while it is being scanned.

        Args:
            pixels: The scan so far.
        """
        self.editor.show_live(pixels)

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
        self.editor.show_scan(scan.path, scan.dpi, scan.regions)
        self.buttons["confirm"].setText(f"Confirm {len(scan.regions)} photo(s)")
        if scan.preview:
            self.editor.hint.setText(
                f"Preview at {scan.dpi} dpi: {len(scan.regions)} photo(s) found. Correct, "
                "draw or delete frames, then 'Scan photos' scans only the area around them "
                "at the chosen resolution; the frames are kept.")
            self.finish(f"Preview: {len(scan.regions)} photo(s) found")
            return
        self.editor.hint.setText(
            f"{len(scan.regions)} photo(s) found. Check the frames: click one to see its "
            "values; drag it to move, drag its grips to resize, the orange grip to rotate "
            "(Shift: 0.5° steps); arrow keys and +/- for fine steps; right-click for more. "
            "Then confirm.")
        self.finish(f"{len(scan.regions)} photo(s) detected; please confirm")

    def _edited(self, regions: list[CropRegion]) -> None:
        """Take over the user's corrections.

        Args:
            regions: Edited regions.
        """
        if self._session.current is not None:
            self._session.current.regions = list(regions)
            self.buttons["confirm"].setText(f"Confirm {len(regions)} photo(s)")
            self.refresh()

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
        self.editor.show_scan(None, 0, [])
        self.buttons["confirm"].setText("Confirm photos")
        names = f"{written[0].name} ... {written[-1].name}" if written else "nothing"
        self.editor.hint.setText(f"Saved {len(written)} photo(s): {names}. Put the next "
                                 "page on the glass and scan.")
        self.finish(f"Saved {len(written)} photo(s) in {self.form.album.text()}")

    def discard(self) -> None:
        """Drop the scan without saving."""
        self._session.discard()
        self.editor.show_scan(None, 0, [])
        self.editor.hint.setText(START_TEXT)
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
