"""Tests for the scanning and printing value objects."""

import math

import pytest

from scanbench.domain.color_mode import ColorMode
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.duplex_order import DuplexOrder
from scanbench.domain.paper_format import A4, PHOTO_PRESETS, PaperFormat
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.printer_option import PrinterOption
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource

TEST_BACKEND = """
All options specific to device `test':
    --mode Gray|Color [Gray]
    --resolution 1..1200dpi (in steps of 1) [50]
    --source Flatbed|Automatic Document Feeder [Flatbed]
    -l 0..200mm (in steps of 1) [0]
    -x 0..200mm (in steps of 1) [80]
    -y 0..200mm (in steps of 1) [100]
"""

MULTIFUNCTION = """
    --resolution auto|75|150|300|600|1200dpi [75]
    --mode auto|Color|Gray|Lineart [Color]
    --source Flatbed|Automatic Document Feeder|ADF Duplex [Flatbed]
    -x 0..216.069mm [216.069]
    -y 0..297.011mm [297.011]
"""

LPOPTIONS = """PageSize/Media Size: *A4 Letter 10x15cm
InputSlot/Paper Source: *Auto Cassette PhotoTray CDTray
MediaType/Media Type: *plain glossy
broken line without colon
Empty/Nothing:
"""


def test_parse_range_device() -> None:
    """A continuous resolution range is reduced to common values."""
    options = DeviceOptions.parse(TEST_BACKEND)
    assert options.resolutions == (75, 150, 300, 600, 1200)
    assert options.sources == ("Flatbed", "Automatic Document Feeder")
    assert (options.max_width_mm, options.max_height_mm) == (200.0, 200.0)
    assert options.available_sources() == [ScanSource.FLATBED, ScanSource.ADF]
    assert options.available_modes() == [ColorMode.COLOR, ColorMode.GRAY]
    assert options.mode_name(ColorMode.LINEART) is None


def test_parse_list_device_with_duplex() -> None:
    """Listed resolutions, duplex feeder and line art are recognised."""
    options = DeviceOptions.parse(MULTIFUNCTION)
    assert options.resolutions == (75, 150, 300, 600, 1200)
    assert options.source_name(ScanSource.ADF) == "Automatic Document Feeder"
    assert options.source_name(ScanSource.ADF_DUPLEX) == "ADF Duplex"
    assert options.mode_name(ColorMode.LINEART) == "Lineart"
    assert options.max_width_mm == pytest.approx(216.069)


def test_parse_empty_output() -> None:
    """Missing options give empty results."""
    options = DeviceOptions.parse("")
    assert options == DeviceOptions((), (), (), None, None)
    assert not DeviceOptions.parse("    --resolution 1..50dpi [50]").resolutions


def test_printer_options() -> None:
    """lpoptions output yields keys, labels, choices and defaults."""
    options = PrinterOption.parse_all(LPOPTIONS)
    assert [o.key for o in options] == ["PageSize", "InputSlot", "MediaType", "Empty"]
    slot = options[1]
    assert slot.label == "Paper Source" and slot.default == "Auto"
    assert slot.choices == ("Auto", "Cassette", "PhotoTray", "CDTray")
    assert options[3].choices == () and options[3].default == ""


def test_crop_region_edits() -> None:
    """Turning wraps around, straightening removes skew, corners are rotated."""
    region = CropRegion(100, 100, 40, 20, 10.0)
    assert region.turned(-1).quarter_turns == 3
    assert region.turned(1).turned(4).quarter_turns == 1
    assert region.straightened().angle == 0.0
    top_left = region.corners()[0]
    rad = math.radians(10)
    assert top_left[0] == pytest.approx(100 - 20 * math.cos(rad) + 10 * math.sin(rad))
    assert top_left[1] == pytest.approx(100 - 20 * math.sin(rad) - 10 * math.cos(rad))


def test_crop_region_clamped_to_frame() -> None:
    """A region sticking out of the scan is shrunk around its centre."""
    region = CropRegion(10, 50, 40, 20).clamped(100, 100)
    assert region.width == pytest.approx(20) and region.height == pytest.approx(10)
    right = CropRegion(90, 50, 40, 20).clamped(100, 100)
    assert right.width == pytest.approx(20)
    assert CropRegion(50, 50, 20, 20).clamped(100, 100).width == 20


def test_fit_and_snap_to_presets() -> None:
    """Near matches snap to the preset, keeping the orientation."""
    dpi = 254          # 10 pixels per millimetre
    landscape = CropRegion(500, 500, 1510, 1008)
    snapped = landscape.snapped(PHOTO_PRESETS, dpi)
    assert (snapped.width, snapped.height) == (1500, 1000)
    portrait = CropRegion(500, 500, 1012, 1490).snapped(PHOTO_PRESETS, dpi)
    assert (portrait.width, portrait.height) == (1000, 1500)
    odd = CropRegion(500, 500, 700, 700)
    assert odd.snapped(PHOTO_PRESETS, dpi) is odd
    assert odd.fitted(PHOTO_PRESETS[0], dpi).width == 1300   # square counts as landscape


def test_small_value_objects() -> None:
    """Formats, qualities, settings, devices and duplex order."""
    assert A4.pixels(254) == (2100, 2970)
    assert PaperFormat("x", 25.4, 50.8).pixels(100) == (100, 200)
    assert PdfQuality.ORIGINAL.setting is None
    assert PdfQuality.PREPRESS.setting == "/prepress" and "Prepress" in PdfQuality.PREPRESS.label
    assert ScanSettings().paper == A4 and ScanSettings().resolution == 300
    assert DeviceInfo("n", "V", "M", "k").label == "V M (n)"
    assert DuplexOrder.FRONTS_THEN_BACKS.arrange([1, 2, 3, 6, 5, 4]) == [1, 4, 2, 5, 3, 6]
    assert DuplexOrder.FRONTS_THEN_BACKS.arrange([1, 2, 3]) == [1, 3, 2]
    assert DuplexOrder.INTERLEAVED.arrange([1, 2]) == [1, 2]
