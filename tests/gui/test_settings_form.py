"""GUI tests of the settings rows, sections, presets, defaults and summary line."""

import dataclasses
import tomllib
from pathlib import Path

from pytestqt.qtbot import QtBot

from gui_helpers import Answers, context
from scan_fakes import FakeScanner
from scanbench.application.document_session import DocumentSession
from scanbench.application.photo_session import PhotoSession
from scanbench.domain.settings_stack import Layer
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.pdf_writer import PdfWriter
from scanbench.infrastructure.photo_detector import PhotoDetector
from scanbench.infrastructure.settings_files import SettingsFiles
from scanbench.infrastructure.shell import Shell
from scanbench.ui.document_tab import DocumentTab
from scanbench.ui.photo_tab import PhotoTab
from scanbench.ui.tab_settings import SettingsHub


def _photo_tab(tmp_path: Path, qtbot: QtBot, answers: Answers) -> PhotoTab:
    """Create a photo tab whose settings are kept in ``tmp_path/config``.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
        answers: Dialog answers.

    Returns:
        The tab.
    """
    scanner = FakeScanner()
    hub = SettingsHub(files=SettingsFiles(tmp_path / "config"))
    ctx = dataclasses.replace(context(qtbot, scanner, answers), settings=hub)
    tab = PhotoTab(ctx, PhotoSession(scanner, PhotoDetector(), ImageStore(), tmp_path))
    qtbot.addWidget(tab)
    return tab


def test_badges_reset_sections_and_summary(tmp_path: Path, qtbot: QtBot) -> None:
    """A change is marked and counted; reset brings the value back.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _photo_tab(tmp_path, qtbot, Answers())
    rows = tab.settings.rows
    assert rows["photos.jpeg_quality"].badge.text() == "built-in"
    assert tab.settings.summary.text() == "Color · 600 dpi · PNG (lossless) · " \
                                          "fit frames to photo sizes"
    rows["photos.jpeg_quality"].editor.setValue(80)                  # type: ignore[attr-defined]
    assert rows["photos.jpeg_quality"].badge.text() == "changed"
    assert rows["photos.jpeg_quality"].reset.isEnabled()
    assert tab.form.album_options().jpeg_quality == 80
    assert tab.settings.summary.text().endswith("· 1 changed")
    title = tab.settings._titles["Output"]       # pylint: disable=protected-access
    assert title.text() == "Output  (1 set)"
    title.setChecked(True)
    assert rows["photos.jpeg_quality"].isVisibleTo(tab)
    rows["photos.jpeg_quality"].reset.click()
    assert tab.form.album_options().jpeg_quality == 92 and title.text() == "Output"
    rows["photos.snap_tolerance"].editor.setValue(10)                # type: ignore[attr-defined]
    assert tab.form.snap_tolerance() == 0.1
    tab.form.snap.setChecked(False)
    assert tab.form.snap_tolerance() == 0.0


def test_value_the_scanner_does_not_offer(tmp_path: Path, qtbot: QtBot) -> None:
    """A wanted resolution the scanner lacks is marked; the nearest one is used.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _photo_tab(tmp_path, qtbot, Answers())
    tab.settings.hub.stack.set_layer(Layer.DEFAULT, {"photos.resolution": 1200})
    tab.update_options()
    row = tab.settings.rows["photos.resolution"]
    assert row.badge.text() == "not offered" and row.get() == 600
    assert "1200 dpi" in row.badge.toolTip()


def test_presets_and_defaults(tmp_path: Path, qtbot: QtBot) -> None:
    """Save and choose presets; save as default; the album folder is remembered.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    tab = _photo_tab(tmp_path, qtbot, Answers(name="Album JPEG"))
    messages: list[str] = []
    tab.message.connect(messages.append)
    rows, presets = tab.settings.rows, tab.presets
    rows["photos.format"].editor.setCurrentIndex(1)                  # type: ignore[attr-defined]
    rows["photos.resolution"].editor.setCurrentIndex(2)              # type: ignore[attr-defined]
    presets.save_preset.click()
    assert presets.combo.currentText() == "Album JPEG" and messages[-1] == "Preset: Album JPEG"
    assert rows["photos.format"].badge.text() == "preset"
    assert "preset: Album JPEG" in tab.settings.summary.text()
    presets.combo.setCurrentIndex(0)
    assert rows["photos.format"].get() == "PNG" and messages[-1] == "No preset"
    presets.combo.setCurrentIndex(1)
    assert rows["photos.format"].get() == "JPEG"
    rows["photos.png_compression"].editor.setValue(9)                # type: ignore[attr-defined]
    presets.save_default.click()
    saved = tomllib.loads((tmp_path / "config" / "settings.toml").read_text(encoding="utf-8"))
    assert saved["photos"] == {"format": "JPEG", "resolution": 300, "png_compression": 9}
    assert rows["photos.png_compression"].badge.text() == "default"
    assert presets.combo.currentText() == "(no preset)" and rows["photos.format"].get() == "JPEG"
    tab.form.album.setText(str(tmp_path / "album"))
    assert tab.form.folder() == tmp_path / "album"
    saved = tomllib.loads((tmp_path / "config" / "settings.toml").read_text(encoding="utf-8"))
    assert saved["photos"]["album"] == str(tmp_path / "album")


def test_presets_without_files_and_invalid_preset(tmp_path: Path, qtbot: QtBot) -> None:
    """Without settings files presets are off; invalid preset values are reported.

    Args:
        tmp_path: Temporary directory of the test.
        qtbot: pytest-qt helper.
    """
    scanner = FakeScanner()
    tab = DocumentTab(context(qtbot, scanner, Answers()),
                      DocumentSession(scanner, ImageStore(), PdfWriter(Shell(tmp_path)),
                                      tmp_path))
    qtbot.addWidget(tab)
    assert not tab.presets.combo.isEnabled()
    assert tab.settings.summary.text() == "Flatbed · Color · 300 dpi · A4 · E-book (150 dpi)"
    photos = _photo_tab(tmp_path, qtbot, Answers())
    (tmp_path / "config" / "presets").mkdir(parents=True)
    (tmp_path / "config" / "presets" / "bad.toml").write_text(
        'schema = 1\nname = "Bad"\n[photos]\njpeg_quality = 1\n', encoding="utf-8")
    messages: list[str] = []
    photos.message.connect(messages.append)
    photos.presets.reload()
    photos.presets.combo.setCurrentIndex(1)
    assert messages[0].startswith("bad.toml: photos.jpeg_quality = 1 must be 70 to 95")
    photos.settings.rows["photos.jpeg_quality"].editor.setValue(70)  # type: ignore[attr-defined]
    assert photos.settings.rows["photos.jpeg_quality"].badge.text() == "changed"
