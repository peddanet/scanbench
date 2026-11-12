"""Read and write ``settings.toml`` and the presets (TOML, Adapter).

Layout of both kinds of file::

    schema = 1
    name = "Album 600 dpi PNG"        # presets only

    [photos]
    resolution = 600
    format = "PNG"

Rules (concept "Settings and sessions", section 4.2): unknown keys are kept
when the file is written again; invalid values are reported with file, key
and reason, and the built-in value is used meanwhile; files are written
atomically. ``settings.json`` of 0.2.x (album folder only) is taken over once.
"""

import json
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from scanbench.domain.settings_schema import BY_KEY, SCHEMA, TABS, Scalar

OLD_ALBUM_KEY = "photo.album"
"""Key of the album folder in ``settings.json`` (0.2.x)."""


@dataclass
class Loaded:
    """Values read from one file.

    Attributes:
        values: Valid known settings, key to value.
        problems: One line per invalid value or unreadable file.
        name: Preset name, empty for ``settings.toml``.
    """

    values: dict[str, Scalar] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)
    name: str = ""


def slug(name: str) -> str:
    """Return a file name stem for a preset name.

    Args:
        name: Preset name, e.g. ``Album 600 dpi PNG``.

    Returns:
        E.g. ``album-600-dpi-png``.
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "preset"


class SettingsFiles:
    """The settings files below the configuration directory."""

    def __init__(self, config_dir: Path) -> None:
        """Store the location.

        Args:
            config_dir: E.g. ``~/.config/scanbench`` or ``$SCANBENCH_HOME/config``.
        """
        self.path = config_dir / "settings.toml"
        self.presets_dir = config_dir / "presets"

    @staticmethod
    def _raw(path: Path, problems: list[str]) -> dict[str, Any]:
        """Return the parsed file; nothing if it is missing or broken.

        Args:
            path: TOML file.
            problems: Receives a line if the file cannot be read.

        Returns:
            The TOML document.
        """
        try:
            with path.open("rb") as stream:
                return tomllib.load(stream)
        except FileNotFoundError:
            return {}
        except (OSError, tomllib.TOMLDecodeError) as exc:
            problems.append(f"{path.name}: cannot be read ({exc}); built-in values are used")
            return {}

    @classmethod
    def _read(cls, path: Path) -> Loaded:
        """Read the known settings of a file and report invalid ones.

        Args:
            path: TOML file.

        Returns:
            Values, problems and the preset name.
        """
        loaded = Loaded()
        raw = cls._raw(path, loaded.problems)
        schema = raw.get("schema", SCHEMA)
        if not isinstance(schema, int) or schema > SCHEMA:
            loaded.problems.append(f"{path.name}: written by a newer scanbench "
                                   f"(schema {schema!r}); unknown values are kept")
        loaded.name = str(raw.get("name", ""))
        for tab in TABS:
            table = raw.get(tab, {})
            for name, value in table.items() if isinstance(table, dict) else ():
                key = f"{tab}.{name}"
                if key not in BY_KEY:
                    continue                      # kept in the file, not used
                try:
                    loaded.values[key] = BY_KEY[key].check(value)
                except ValueError as exc:
                    loaded.problems.append(f"{path.name}: {key} = {value!r} {exc}; "
                                           "the built-in value is used")
        return loaded

    @classmethod
    def _write(cls, path: Path, values: dict[str, Scalar], tab: str | None = None,
               name: str = "") -> None:
        """Write values into a file, keeping what it holds besides them.

        Args:
            path: TOML file.
            values: Settings to store; settings of the given tab(s) not listed
                are removed from the file.
            tab: Only this tab's table is replaced; None for all.
            name: Preset name, empty for none.
        """
        raw = cls._raw(path, [])
        raw["schema"] = SCHEMA
        if name:
            raw["name"] = name
        for table in TABS if tab is None else (tab,):
            kept = {k: v for k, v in dict(raw.get(table, {})).items()
                    if f"{table}.{k}" not in BY_KEY}
            kept.update({BY_KEY[k].name: v for k, v in values.items()
                         if BY_KEY[k].tab == table})
            raw[table] = kept
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".tmp")
        partial.write_text(tomli_w.dumps(raw), encoding="utf-8")
        partial.replace(path)                      # atomic

    def load_defaults(self) -> Loaded:
        """Read ``settings.toml``; take over ``settings.json`` of 0.2.x once.

        Returns:
            The saved defaults and any problems.
        """
        old = self.path.with_name("settings.json")
        if not self.path.exists() and old.exists():
            try:
                album = json.loads(old.read_text(encoding="utf-8")).get(OLD_ALBUM_KEY)
                self._write(self.path, {"photos.album": str(album)} if album else {})
                old.replace(old.with_name("settings.json.migrated"))
            except (OSError, ValueError, AttributeError):
                pass                                # an unreadable old file is ignored
        return self._read(self.path)

    def save_defaults(self, values: dict[str, Scalar]) -> None:
        """Write the defaults.

        Args:
            values: All saved defaults.

        Raises:
            OSError: If the file cannot be written.
        """
        self._write(self.path, values)

    def presets(self, tab: str) -> dict[str, Path]:
        """Return the presets that hold settings of a tab.

        Args:
            tab: ``documents`` or ``photos``.

        Returns:
            Preset name to file, sorted by name.
        """
        found: dict[str, Path] = {}
        for path in sorted(self.presets_dir.glob("*.toml")):
            raw = self._raw(path, [])
            if isinstance(raw.get(tab), dict):
                found[str(raw.get("name", path.stem))] = path
        return dict(sorted(found.items(), key=lambda item: item[0].lower()))

    def load_preset(self, path: Path) -> Loaded:
        """Read a preset.

        Args:
            path: Preset file.

        Returns:
            Its values and problems.
        """
        return self._read(path)

    def save_preset(self, name: str, tab: str, values: dict[str, Scalar]) -> Path:
        """Write a preset with the given values of one tab.

        Args:
            name: Preset name.
            tab: ``documents`` or ``photos``.
            values: Values of that tab.

        Returns:
            The preset file.

        Raises:
            OSError: If the file cannot be written.
        """
        path = self.presets_dir / f"{tab}-{slug(name)}.toml"
        self._write(path, values, tab, name)
        return path
