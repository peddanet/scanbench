"""Unit tests of the device cache file."""

from pathlib import Path

from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.infrastructure.device_cache import DeviceCache, KnownDevices

MX920 = DeviceInfo("airscan:w0:Canon MX920 series", "Canon", "MX920 series", "eSCL network scanner")
OPTIONS = DeviceOptions(("Flatbed", "ADF"), ("Color", "Gray"), (75, 300, 600), 216.0, 297.0)


def test_round_trip(tmp_path: Path) -> None:
    """Devices, selection and options survive writing and reading.

    Args:
        tmp_path: Temporary directory of the test.
    """
    cache = DeviceCache(tmp_path / "sub" / "devices.json")
    assert cache.load() == KnownDevices()
    cache.save(KnownDevices([MX920], MX920.name, {MX920.name: OPTIONS}))
    assert cache.load() == KnownDevices([MX920], MX920.name, {MX920.name: OPTIONS})
    assert not (tmp_path / "sub" / "devices.tmp").exists()


def test_broken_or_foreign_files_are_ignored(tmp_path: Path) -> None:
    """A damaged file, an unknown format or an unwritable place mean "nothing known".

    Args:
        tmp_path: Temporary directory of the test.
    """
    path = tmp_path / "devices.json"
    for text in ("{not json", '{"format": 99}', '{"format": 1, "devices": [{"x": 1}]}'):
        path.write_text(text, encoding="utf-8")
        assert DeviceCache(path).load() == KnownDevices()
    blocker = tmp_path / "file"
    blocker.write_text("", encoding="utf-8")
    DeviceCache(blocker / "devices.json").save(KnownDevices([MX920]))   # logged, not raised
