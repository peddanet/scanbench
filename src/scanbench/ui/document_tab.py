"""Documents tab: scan pages simplex or duplex, edit, save as PDF, print."""

import tempfile
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QPushButton, QVBoxLayout

from scanbench.application.document_session import DocumentSession, Page
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_error import ScanError
from scanbench.ui.page_list import PageList
from scanbench.ui.scan_tab import ScanTab
from scanbench.ui.settings_panel import SettingsPanel, fill
from scanbench.ui.tab_context import TabContext

BUTTONS = (("scan", "Scan"), ("left", "Rotate left"), ("right", "Rotate right"),
           ("up", "Move up"), ("down", "Move down"), ("delete", "Delete page"),
           ("merge", "Merge fronts + backs"), ("clear", "Start new document"),
           ("save", "Save PDF ..."), ("print", "Print ..."))
"""Command buttons in display order."""


class DocumentTab(ScanTab):
    """Scan, arrange and save the pages of a document.

    Every button is a command on the :class:`DocumentSession`; slow commands
    (scan, save, print) run in the task runner.
    """

    def __init__(self, context: TabContext, session: DocumentSession) -> None:
        """Build the widgets.

        Args:
            context: Shared collaborators.
            session: Pages of the document.
        """
        super().__init__(context)
        self._session = session
        self.panel = SettingsPanel(300)
        self.quality = QComboBox()
        fill(self.quality, [(q.label, q) for q in PdfQuality], PdfQuality.EBOOK)
        self.pages = PageList(session)
        self.buttons = {key: QPushButton(text) for key, text in BUTTONS}
        self.buttons["merge"].setToolTip(
            "Manual duplex: scan all front sides, turn the stack over, scan all back "
            "sides, then merge the two runs into reading order.")
        self._layout()
        self._connect()
        self.update_options()

    def _layout(self) -> None:
        """Arrange controls and pages."""
        form = QFormLayout()
        self.panel.add_rows(form)
        controls = QVBoxLayout()
        controls.addLayout(form)
        for key, _ in BUTTONS[:8]:
            controls.addWidget(self.buttons[key])
            if key == "scan":
                controls.addWidget(self.cancel_button)
        output = QFormLayout()
        output.addRow("PDF size:", self.quality)
        controls.addLayout(output)
        controls.addWidget(self.buttons["save"])
        controls.addWidget(self.buttons["print"])
        controls.addStretch(1)
        layout = QHBoxLayout(self)
        layout.addLayout(controls)
        layout.addWidget(self.pages, 1)

    def _connect(self) -> None:
        """Connect signals to commands."""
        self._ctx.devices.options_changed.connect(self.update_options)
        pages = self.pages
        actions = {"scan": self.scan, "left": lambda: pages.rotate(-1),
                   "right": lambda: pages.rotate(1), "up": lambda: pages.move_page(-1),
                   "down": lambda: pages.move_page(1), "delete": pages.delete,
                   "merge": self.merge, "clear": self.clear, "save": self.save,
                   "print": self.print_document}
        for key, action in actions.items():
            self.buttons[key].clicked.connect(action)
        pages.changed.connect(self.refresh)

    def update_options(self) -> None:
        """Adapt the settings to the selected device."""
        self.panel.apply(self._ctx.devices.options())
        self.refresh()

    def refresh(self) -> None:
        """Enable the commands that make sense now."""
        busy = self._ctx.runner.busy()
        has_pages = bool(self._session.pages)
        self.buttons["scan"].setEnabled(not busy and self._ctx.devices.device() is not None
                                        and self.panel.ready())
        for key in ("left", "right", "up", "down", "delete"):
            self.buttons[key].setEnabled(not busy and self.pages.row() >= 0)
        for key in ("merge", "clear", "save", "print"):
            self.buttons[key].setEnabled(not busy and has_pages)

    def scan(self) -> None:
        """Scan one page or the feeder in the background."""
        selected = self.selected_device()
        if selected is None:
            return
        device, options = selected
        settings = self.panel.settings()
        self.run_scan(f"Scanning ({settings.source.value}, {settings.mode.value}) ...",
                      lambda observer: self._session.scan(device, settings, options, observer),
                      self._scanned)

    def show_partial(self, pixels: NDArray[np.uint8]) -> None:
        """Show the page while it is being scanned.

        Args:
            pixels: The page so far.
        """
        self.pages.show_live(pixels)

    def _scanned(self, added: list[Page]) -> None:
        """Show new pages.

        Args:
            added: The scanned pages.
        """
        self.pages.redraw(len(self._session.pages) - 1)
        self.finish(f"{len(added)} page(s) scanned; {len(self._session.pages)} in total")

    def scanned_pages(self) -> list[Page]:
        """Return the pages of the document being scanned.

        Returns:
            The pages in order.
        """
        return list(self._session.pages)

    def resume(self, pages: list[Page]) -> None:
        """Show pages taken over from the previous release.

        Args:
            pages: The pages in order.
        """
        self._session.pages = list(pages)
        self.pages.redraw(len(pages) - 1)

    def merge(self) -> None:
        """Merge the last two scan runs as fronts and backs."""
        try:
            self._session.merge_last_batches()
        except ScanError as exc:
            self.message.emit(str(exc))
            return
        self.pages.redraw(0)
        self.message.emit("Front and back sides merged into reading order")

    def clear(self) -> None:
        """Start a new document."""
        self._session.clear()
        self.pages.redraw()
        self.message.emit("New document")

    def save(self) -> None:
        """Ask for a file name and save the PDF in the background."""
        target = self._ctx.dialogs.save_as(self, Path.home() / "scan.pdf")
        if target is None:
            return
        quality = self.quality.currentData()
        self.run_job(f"Saving {target.name} ({quality.label}) ...",
                     lambda: self._session.save_pdf(target, quality), self._saved)

    def _saved(self, target: Path) -> None:
        """Report the saved file.

        Args:
            target: The written PDF.
        """
        self.pages.dirty = False
        self.finish(f"Saved {target} ({target.stat().st_size / 1e6:.1f} MB)")

    def print_document(self) -> None:
        """Ask for printer and options and print all pages as one PDF."""
        job = self._ctx.dialogs.ask_print(self, "Print document", False)
        if job is None:
            return
        cups, session = self._ctx.cups, self._session

        def work() -> str:
            """Write a lossless PDF and send it to CUPS.

            Returns:
                The job ID.
            """
            with tempfile.TemporaryDirectory(prefix="scanbench-print-") as tmp:
                pdf = session.save_pdf(Path(tmp) / "document.pdf", PdfQuality.ORIGINAL)
                return cups.print_files(job.printer, [pdf], job.copies, job.options)
        self.run_job(f"Printing on {job.printer} ...", work,
                     lambda job_id: self.finish(f"Print job {job_id} sent"))
