"""The samples in examples/ stay in step with the code that reads them."""

import tomllib
from importlib import resources
from pathlib import Path

import privacy_scan
from PIL import Image

from scanbench.app_info import ICON_FILE

from scanbench.domain.settings_schema import DEFINITIONS, SCHEMA
from scanbench.infrastructure.settings_files import SettingsFiles

EXAMPLES = Path(__file__).resolve().parent.parent.parent / "examples"
"""Folder of the samples."""


def test_settings_sample_holds_every_built_in_value() -> None:
    """The settings sample has exactly the built-in values of all options."""
    sample = EXAMPLES / "settings.toml.sample"
    loaded = SettingsFiles(EXAMPLES).load_preset(sample)   # same reader as settings.toml
    assert not loaded.problems
    assert loaded.values == {d.key: d.default for d in DEFINITIONS}
    raw = tomllib.loads(sample.read_text(encoding="utf-8"))
    assert raw["schema"] == SCHEMA
    assert sum(len(table) for key, table in raw.items() if key != "schema") \
        == len(DEFINITIONS)


def test_preset_sample_is_valid() -> None:
    """The preset sample loads without problems and carries a name."""
    files = SettingsFiles(EXAMPLES)
    sample = EXAMPLES / "presets" / "photos-album-600-dpi-png.toml.sample"
    loaded = files.load_preset(sample)
    assert not loaded.problems and loaded.name == "Album 600 dpi PNG"
    assert str(loaded.values["photos.album"]).startswith("/home/USER/")


def test_privacy_samples_hold_entries() -> None:
    """Both list samples hold entries and are excluded from the content search."""
    deny = privacy_scan.load_entries(EXAMPLES / "privacy" / "denylist.sample.txt")
    allow = privacy_scan.load_entries(EXAMPLES / "privacy" / "allowlist.sample.txt")
    assert deny and allow
    assert all("@" in address and " " not in address for address in allow)
    root = EXAMPLES.parent
    assert all((root / name).is_file() for name in privacy_scan.SAMPLES)


def test_social_preview_meets_the_github_limits() -> None:
    """The preview is 1280 x 640 PNG below 1 MB and has its SVG source."""
    images = EXAMPLES.parent / "docs" / "images"
    picture = images / "social-preview.png"
    assert (images / "social-preview.svg").is_file()
    assert picture.stat().st_size < 1_000_000
    with Image.open(picture) as image:
        assert image.format == "PNG" and image.size == (1280, 640)


def test_program_icon_is_package_data() -> None:
    """The program icon is a real file in the package, read by the installers."""
    icon = resources.files("scanbench").joinpath("data", ICON_FILE)
    assert icon.read_bytes().startswith(b"<svg")
