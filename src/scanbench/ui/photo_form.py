"""Settings of the photo tab: scan quality and album options."""

from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget)

from scanbench.application.photo_session import AlbumOptions
from scanbench.domain.image_format import ImageFormat
from scanbench.infrastructure.settings_store import SettingsStore
from scanbench.ui.dialogs import ChooseFolder
from scanbench.ui.settings_panel import SettingsPanel, fill

ALBUM_KEY = "photo.album"
"""Settings key of the album folder."""


class PhotoForm(QWidget):
    """Colour, resolution, output format, album folder and detection options.

    The album folder is remembered across restarts in the settings file.
    """

    def __init__(self, settings: SettingsStore, choose: ChooseFolder) -> None:
        """Build the form.

        Args:
            settings: Persistent settings.
            choose: Folder question.
        """
        super().__init__()
        self._settings = settings
        self._choose = choose
        self.panel = SettingsPanel(600, documents=False)
        self.image_format = QComboBox()
        fill(self.image_format, [("PNG (lossless)", ImageFormat.PNG),
                                 ("JPEG (smaller)", ImageFormat.JPEG)])
        default_album = Path.home() / "Pictures" / "scanbench-album"
        self.album = QLineEdit(settings.get(ALBUM_KEY, str(default_album)))
        self.snap = QCheckBox("Fit frames to photo sizes (10 x 15 cm ...)")
        self.snap.setChecked(True)
        self.keep_scans = QCheckBox("Keep full-page scans in the album")
        browse_button = QPushButton("Choose ...")
        folder = QHBoxLayout()
        folder.addWidget(self.album, 1)
        folder.addWidget(browse_button)
        form = QFormLayout()
        self.panel.add_rows(form)
        form.addRow("Format:", self.image_format)
        form.addRow("Album:", folder)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.snap)
        layout.addWidget(self.keep_scans)
        browse_button.clicked.connect(self.browse)
        self.album.editingFinished.connect(self.remember)

    def remember(self) -> Path:
        """Store the album folder in the settings.

        Returns:
            The folder with ``~`` expanded.
        """
        folder = Path(self.album.text()).expanduser()
        self._settings.set(ALBUM_KEY, str(folder))
        return folder

    def browse(self) -> None:
        """Choose the album folder."""
        chosen = self._choose(self, Path(self.album.text()).expanduser())
        if chosen is not None:
            self.album.setText(str(chosen))
            self.remember()

    def album_options(self) -> AlbumOptions:
        """Return where and how photos are stored.

        Returns:
            The album options.
        """
        return AlbumOptions(self.remember(), self.image_format.currentData(),
                            self.keep_scans.isChecked())
