"""Remember the scanners found last time, so the window can start without waiting.

Searching SANE devices takes several seconds on network scanners (11 s were
measured with an airscan device), and so does reading a device's options.
The cache keeps the last search result, the options per device and the last
selected device. It is only a cache: a missing or broken file means "nothing
known", and deleting it is harmless.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.infrastructure.app_log import LOGGER

FORMAT = 1
"""Version of the file layout; files of another version are ignored."""


@dataclass
class KnownDevices:
    """What is known about the scanners from earlier runs.

    Attributes:
        devices: Result of the last search.
        selected: Last selected device name, or None.
        options: Options per device name.
    """

    devices: list[DeviceInfo] = field(default_factory=list)
    selected: str | None = None
    options: dict[str, DeviceOptions] = field(default_factory=dict)


def _options(data: dict[str, Any]) -> DeviceOptions:
    """Rebuild options from their JSON form.

    Args:
        data: Fields as written by ``asdict``.

    Returns:
        The options.
    """
    return DeviceOptions(tuple(data["sources"]), tuple(data["modes"]),
                         tuple(int(d) for d in data["resolutions"]),
                         data.get("max_width_mm"), data.get("max_height_mm"))


class DeviceCache:
    """Read and write the device cache file (JSON)."""

    def __init__(self, path: Path) -> None:
        """Store the location.

        Args:
            path: Cache file, e.g. ``~/.cache/scanbench/devices.json``.
        """
        self.path = path

    def load(self) -> KnownDevices:
        """Return the remembered devices; nothing if the file is missing or broken.

        Returns:
            The known devices.
        """
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("format") != FORMAT:
                return KnownDevices()
            return KnownDevices([DeviceInfo(**d) for d in data["devices"]],
                                data.get("selected"),
                                {k: _options(v) for k, v in data["options"].items()})
        except FileNotFoundError:
            return KnownDevices()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logging.getLogger(LOGGER).warning("device cache %s ignored: %s", self.path, exc)
            return KnownDevices()

    def save(self, known: KnownDevices) -> None:
        """Write the known devices; a failure is logged, not raised.

        Args:
            known: What to remember.
        """
        data = {"format": FORMAT, "devices": [asdict(d) for d in known.devices],
                "selected": known.selected,
                "options": {k: asdict(v) for k, v in known.options.items()}}
        partial = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            partial.write_text(json.dumps(data, indent=1), encoding="utf-8")
            partial.replace(self.path)          # atomic: never a half-written cache
        except OSError as exc:
            logging.getLogger(LOGGER).warning("device cache %s not written: %s", self.path, exc)
