"""Settings of the photo tab: scan quality and album options."""

from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from scanbench.application.photo_session import AlbumOptions
from scanbench.domain.image_format import ImageFormat
from scanbench.ui.dialogs import ChooseFolder
from scanbench.ui.settings_panel import SettingsPanel, fill
from scanbench.ui.tab_settings import TabSettings


class PhotoForm(QWidget):
    """Colour, resolution, output format, album folder and detection options.

    Every widget is a row of the tab's settings (badge, reset); the album
    folder is saved as default at once, as before.
    """

    def __init__(self, settings: TabSettings, choose: ChooseFolder) -> None:
        """Build the form.

        Args:
            settings: The photo tab's settings.
            choose: Folder question.
        """
        super().__init__()
        self.settings = settings
        self._choose = choose
        self.panel = SettingsPanel(600, documents=False)
        self.image_format = QComboBox()
        fill(self.image_format, [("PNG (lossless)", ImageFormat.PNG),
                                 ("JPEG (smaller)", ImageFormat.JPEG)])
        self.album = QLineEdit()
        self.snap = QCheckBox("Fit frames to photo sizes (10 x 15 cm ...)")
        self.keep_scans = QCheckBox("Keep full-page scans in the album")
        browse_button = QPushButton("Choose ...")
        form = QFormLayout()
        self.panel.add_rows(form, lambda name, w: settings.row(f"photos.{name}", w))
        form.addRow("Format:", settings.row("photos.format", self.image_format))
        folder = QHBoxLayout()
        folder.addWidget(settings.row("photos.album", self.album), 1)
        folder.addWidget(browse_button)
        form.addRow("Album:", folder)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(settings.row("photos.snap", self.snap))
        layout.addWidget(settings.row("photos.keep_scans", self.keep_scans))
        layout.addWidget(settings.sections())
        browse_button.clicked.connect(self.browse)

    def folder(self) -> Path:
        """Return the album folder; a typed but not yet confirmed path counts.

        Returns:
            The folder with ``~`` expanded.
        """
        typed = self.album.text().strip()
        if typed and typed != self.settings.value("photos.album"):
            self.album.editingFinished.emit()        # takes it over like leaving the field
        return Path(str(self.settings.value("photos.album"))).expanduser()

    def browse(self) -> None:
        """Choose the album folder."""
        chosen = self._choose(self, self.folder())
        if chosen is not None:
            self.album.setText(str(chosen))
            self.album.editingFinished.emit()

    def snap_tolerance(self) -> float:
        """Return the size tolerance for fitting frames, 0 if fitting is off.

        Returns:
            Fraction per side, e.g. 0.06.
        """
        if not self.snap.isChecked():
            return 0.0
        return int(self.settings.value("photos.snap_tolerance")) / 100

    def album_options(self) -> AlbumOptions:
        """Return where and how photos are stored.

        Returns:
            The album options.
        """
        value = self.settings.value
        return AlbumOptions(self.folder(), self.image_format.currentData(),
                            self.keep_scans.isChecked(), int(value("photos.jpeg_quality")),
                            int(value("photos.png_compression")))
