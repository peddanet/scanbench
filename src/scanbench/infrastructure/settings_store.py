"""Small persistent user settings in a JSON file."""

import json
from pathlib import Path


class SettingsStore:
    """Remember choices such as the album folder across restarts.

    The file lives in the configuration directory; a broken file is
    ignored and replaced on the next change.
    """

    def __init__(self, path: Path) -> None:
        """Load the settings file if it exists.

        Args:
            path: JSON file.
        """
        self._path = path
        self._data: dict[str, str] = {}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self._data = {str(k): str(v) for k, v in loaded.items()}
        except (OSError, ValueError):
            pass

    def get(self, key: str, default: str = "") -> str:
        """Return a value.

        Args:
            key: Setting name.
            default: Value if the setting is unknown.

        Returns:
            The value.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        """Change a value and write the file at once.

        Args:
            key: Setting name.
            value: New value.
        """
        self._data[key] = value
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=1, sort_keys=True) + "\n",
                                  encoding="utf-8")
        except OSError:
            pass   # settings are a convenience; scanning must not fail because of them
