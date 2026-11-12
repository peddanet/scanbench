"""Unit tests of the settings schema, the layer stack and the TOML files."""

import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

from scanbench.domain.settings_schema import BY_KEY, DEFINITIONS, for_tab
from scanbench.domain.settings_stack import Layer, SettingsStack
from scanbench.infrastructure.settings_files import SettingsFiles, slug


def test_definitions_are_consistent() -> None:
    """Every default passes its own check; keys are unique and belong to a tab."""
    assert len(BY_KEY) == len(DEFINITIONS)
    for definition in DEFINITIONS:
        assert definition.check(definition.default) == definition.default
        assert definition.help and definition.tab in ("documents", "photos")
    assert [d.name for d in for_tab("documents")][:3] == ["source", "colour", "resolution"]


@pytest.mark.parametrize(("key", "value", "reason"), [
    ("photos.jpeg_quality", 96, "must be 70 to 95"),
    ("photos.jpeg_quality", "92", "must be a whole number"),
    ("photos.snap", 1, "must be true or false"),
    ("photos.format", "GIF", "must be one of PNG, JPEG"),
    ("documents.paper", 4, "must be text"),
])
def test_check_reports_the_reason(key: str, value: object, reason: str) -> None:
    """Wrong types, ranges and choices are refused with a reason.

    Args:
        key: Setting key.
        value: Invalid value.
        reason: Expected message.
    """
    with pytest.raises(ValueError, match=reason):
        BY_KEY[key].check(value)


def test_text_of_values() -> None:
    """Values are shown with their labels and units."""
    assert BY_KEY["documents.pdf_size"].text("EBOOK") == "E-book (150 dpi)"
    assert BY_KEY["photos.resolution"].text(600) == "600 dpi"
    assert BY_KEY["photos.snap"].text(False) == "off"
    assert BY_KEY["documents.colour"].text("COLOR") == "Color"
    assert BY_KEY["photos.album"].text("~/x") == "~/x"


def test_stack_layers_sources_and_reset() -> None:
    """The highest layer wins; equal values and resets fall back."""
    stack = SettingsStack()
    key = "photos.resolution"
    assert stack.value(key) == 600 and stack.source(key) is Layer.BUILT_IN
    stack.set_layer(Layer.DEFAULT, {key: 300, "unknown.key": 1})
    stack.set_layer(Layer.PRESET, {key: 1200})
    assert stack.value(key) == 1200 and stack.source(key) is Layer.PRESET
    stack.set(key, 2400)
    assert stack.source(key) is Layer.SESSION and stack.below(key) == 1200
    stack.set(key, 1200)                                     # back to the preset value
    assert stack.source(key) is Layer.PRESET
    stack.set(key, 75)
    stack.reset(key)
    assert stack.value(key) == 1200 and "unknown.key" not in stack.layer(Layer.DEFAULT)
    stack.set("photos.album", "/a", Layer.DEFAULT)
    assert stack.source("photos.album") is Layer.DEFAULT
    assert stack.effective("photos")["photos.album"] == "/a"
    with pytest.raises(ValueError):
        stack.set_layer(Layer.BUILT_IN, {})


def test_files_round_trip_keep_unknown_and_report(tmp_path: Path) -> None:
    """Defaults are written atomically; foreign keys survive; bad values are named.

    Args:
        tmp_path: Temporary directory of the test.
    """
    files = SettingsFiles(tmp_path)
    assert not files.load_defaults().values
    files.path.write_text('schema = 1\nnote = "mine"\n[photos]\nresolution = 1200\n'
                          'jpeg_quality = 120\nfuture = 3\n', encoding="utf-8")
    loaded = files.load_defaults()
    assert loaded.values == {"photos.resolution": 1200}
    assert loaded.problems == ["settings.toml: photos.jpeg_quality = 120 must be 70 to 95; "
                               "the built-in value is used"]
    files.save_defaults({"photos.format": "JPEG", "documents.resolution": 150})
    raw = tomllib.loads(files.path.read_text(encoding="utf-8"))
    assert raw == {"schema": 1, "note": "mine", "photos": {"future": 3, "format": "JPEG"},
                   "documents": {"resolution": 150}}
    files.path.write_text("schema = 2\n[photos\n", encoding="utf-8")
    assert "cannot be read" in files.load_defaults().problems[0]
    files.path.write_text("schema = 9\n", encoding="utf-8")
    assert "newer scanbench (schema 9)" in files.load_defaults().problems[0]


def test_old_json_settings_are_taken_over(tmp_path: Path) -> None:
    """The album folder of settings.json (0.2.x) moves into settings.toml once.

    Args:
        tmp_path: Temporary directory of the test.
    """
    (tmp_path / "settings.json").write_text(json.dumps({"photo.album": "/p"}),
                                            encoding="utf-8")
    assert SettingsFiles(tmp_path).load_defaults().values == {"photos.album": "/p"}
    assert (tmp_path / "settings.json.migrated").exists()
    other = tmp_path / "other"
    other.mkdir()
    (other / "settings.json").write_text("[1]", encoding="utf-8")       # not a mapping
    assert not SettingsFiles(other).load_defaults().values


def test_presets(tmp_path: Path) -> None:
    """Presets are listed per tab by name and read back.

    Args:
        tmp_path: Temporary directory of the test.
    """
    files = SettingsFiles(tmp_path)
    path = files.save_preset("Album 1200 dpi JPEG", "photos",
                             {"photos.resolution": 1200, "photos.format": "JPEG"})
    files.save_preset("Letter", "documents", {"documents.paper": "Letter"})
    assert path.name == "photos-album-1200-dpi-jpeg.toml"
    assert list(files.presets("photos")) == ["Album 1200 dpi JPEG"]
    loaded = files.load_preset(path)
    assert loaded.name == "Album 1200 dpi JPEG" and loaded.values["photos.resolution"] == 1200
    assert slug("  ") == "preset"


def test_user_guide_table_is_current() -> None:
    """The options table of the user guide matches the schema."""
    tool = Path(__file__).resolve().parents[2] / "tools" / "settings_table.py"
    spec = importlib.util.spec_from_file_location("settings_table", tool)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    text = module.GUIDE.read_text(encoding="utf-8")
    assert module.updated(text) == text, "run python3 tools/settings_table.py"
    with pytest.raises(ValueError, match="markers"):
        module.updated("no markers")
