"""Tests for ScanimageBackend, with scripted output and with SANE's test device."""

import shutil
from pathlib import Path

import pytest

from fakes import FakeShell, failed, ok
from scan_fakes import OPTIONS
from scanbench.domain.color_mode import ColorMode
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.paper_format import A4
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource
from scanbench.infrastructure.scanimage_backend import TEST_DEVICE, ScanimageBackend
from scanbench.infrastructure.shell import Shell

HAS_SANE = shutil.which("scanimage") is not None


def test_devices_parsed_and_test_device_added() -> None:
    """Device lines are split; the test device is added on request."""
    shell = FakeShell(script={("scanimage", "-f"): [ok("a:1|Canon|MX920|multi\nbad\n")]})
    found = ScanimageBackend(shell).devices(include_test=True)
    assert [d.name for d in found] == ["a:1", TEST_DEVICE.name]
    assert found[0].model == "MX920"


def test_devices_failure_and_missing_program(tmp_path: Path) -> None:
    """Errors become ScanError with a hint.

    Args:
        tmp_path: Temporary directory of the test.
    """
    shell = FakeShell(script={("scanimage",): [failed("io error")]})
    with pytest.raises(ScanError, match="io error"):
        ScanimageBackend(shell).devices()
    with pytest.raises(ScanError, match="options"):
        ScanimageBackend(shell).options("x")
    missing = Shell(tmp_path, which=lambda _name: None)
    with pytest.raises(ScanError, match="sane-utils"):
        ScanimageBackend(missing).devices()


def test_arguments_and_feeder(tmp_path: Path) -> None:
    """Source, mode, resolution and clamped area are passed; feeder uses batch mode.

    Args:
        tmp_path: Temporary directory of the test.
    """
    (tmp_path / "doc-001.png").write_bytes(b"x")
    (tmp_path / "doc-002.png").write_bytes(b"x")
    (tmp_path / "doc-003.png").write_bytes(b"")          # empty file is ignored
    shell = FakeShell(script={("scanimage",): [failed("Document feeder out of documents")]})
    settings = ScanSettings(ScanSource.ADF_DUPLEX, ColorMode.LINEART, 280, A4)
    pages = ScanimageBackend(shell).scan("dev", settings, OPTIONS, tmp_path, "doc")
    assert [p.name for p in pages] == ["doc-001.png", "doc-002.png"]
    argv = shell.calls[0]
    assert "--source=ADF Duplex" in argv and "--mode=Lineart" in argv
    assert "--resolution=300" in argv
    assert argv[argv.index("-x") + 1] == "210" and argv[argv.index("-y") + 1] == "297"
    assert any(a.startswith("--batch=") for a in argv)


def test_scan_errors(tmp_path: Path) -> None:
    """Unsupported settings and empty results raise ScanError.

    Args:
        tmp_path: Temporary directory of the test.
    """
    plain = DeviceOptions(("Flatbed",), ("Gray",), ())
    backend = ScanimageBackend(FakeShell(script={("scanimage",): [failed("busy")]}))
    with pytest.raises(ScanError, match="does not offer"):
        backend.scan("dev", ScanSettings(), plain, tmp_path, "a")
    with pytest.raises(ScanError, match="busy"):
        backend.scan("dev", ScanSettings(mode=ColorMode.GRAY), plain, tmp_path, "a")
    shell = FakeShell()
    with pytest.raises(ScanError, match="no message"):
        ScanimageBackend(shell).scan("dev", ScanSettings(mode=ColorMode.GRAY), plain,
                                     tmp_path, "b")
    assert not any(a.startswith("--resolution") for a in shell.calls[0])


@pytest.mark.skipif(not HAS_SANE, reason="scanimage (sane-utils) not installed")
def test_real_test_device(tmp_path: Path) -> None:
    """The SANE test backend scans a flatbed page and a full feeder.

    Args:
        tmp_path: Temporary directory of the test.
    """
    backend = ScanimageBackend(Shell(tmp_path))
    options = backend.options("test")
    assert ScanSource.ADF in options.available_sources()
    flatbed = backend.scan("test", ScanSettings(resolution=75), options, tmp_path, "f")
    assert len(flatbed) == 1 and flatbed[0].stat().st_size > 0
    feeder = backend.scan("test", ScanSettings(ScanSource.ADF, ColorMode.GRAY, 75), options,
                          tmp_path, "a")
    assert len(feeder) == 10
