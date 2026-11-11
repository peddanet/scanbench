"""Tests for image store, cropper and photo detector."""

import functools
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from scan_fakes import page, write_png
from scenes import DPI, Placed, scan
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.image_format import ImageFormat
from scanbench.domain.scan_error import ScanError
from scanbench.infrastructure.image_cropper import ImageCropper
from scanbench.infrastructure.image_store import ImageStore
from scanbench.infrastructure.photo_detector import PhotoDetector, region_from_points

MM = DPI / 25.4


def test_store_round_trip(tmp_path: Path) -> None:
    """Resolution, rotation and both output formats.

    Args:
        tmp_path: Temporary directory of the test.
    """
    store = ImageStore()
    source = write_png(tmp_path / "p.png", page(200, 60, 80), 150)
    assert store.resolution(source, 0) == 150
    turned = store.turned_copy(source, tmp_path / "t.png", 1, 150)
    pixels = store.load_rgb(turned)
    assert pixels.shape == (60, 80, 3)
    assert pixels[0, -1].tolist() == [0, 0, 0]     # mark moved to the top-right corner
    kept = store.turned_copy(source, tmp_path / "k.png", 0, 150)
    assert store.load_rgb(kept).shape == (80, 60, 3)
    jpeg = store.save(pixels, tmp_path / "x.jpg", ImageFormat.JPEG, 300)
    png = store.save(pixels, tmp_path / "x.png", ImageFormat.PNG, 300)
    with Image.open(jpeg) as opened:
        assert opened.format == "JPEG"
    assert store.resolution(png, 0) == 300
    rgba = tmp_path / "a.png"
    Image.new("RGBA", (4, 4)).save(rgba)
    assert store.resolution(rgba, 72) == 72
    with Image.open(store.turned_copy(rgba, tmp_path / "b.png", 2, 72)) as opened:
        assert opened.mode == "RGB"


def test_store_errors(tmp_path: Path) -> None:
    """Unreadable and unwritable files raise ScanError.

    Args:
        tmp_path: Temporary directory of the test.
    """
    (tmp_path / "bad.png").write_text("no image", encoding="utf-8")
    with pytest.raises(ScanError, match="cannot read"):
        ImageStore().load_rgb(tmp_path / "bad.png")
    with pytest.raises(ScanError, match="cannot write"):
        ImageStore.save(page(1), tmp_path / "missing" / "x.png", ImageFormat.PNG, 72)


def test_cropper_deskews_and_turns() -> None:
    """A skewed photo comes out straight, with its size, turned as asked."""
    photo = Placed(60, 40, 60, 50, 7.0, None, 3)
    pixels = scan([photo], 120, 100)
    region = photo.region()
    result = ImageCropper.crop(pixels, region)
    assert result.shape[:2] == (round(region.height), round(region.width))
    turned = ImageCropper.crop(pixels, region.turned(1))
    assert turned.shape[:2] == (round(region.width), round(region.height))
    assert np.array_equal(turned, np.rot90(result, k=-1))


def test_region_from_points_prefers_small_skew() -> None:
    """A box turned by nearly 90 degrees is a portrait box with small skew."""
    points = np.array([[0, 0], [10, 0], [10, 20], [0, 20]], dtype=np.float32)
    region = region_from_points(points, 2.0)
    assert (region.width, region.height, region.angle) == (20.0, 40.0, 0.0)
    diamond = np.array([[0, 10], [10, 0], [20, 10], [10, 20]], dtype=np.float32)
    assert region_from_points(diamond, 1.0).angle == 45.0


LAYOUTS = {
    "three postcards with grey borders": [
        Placed(140, 90, 78, 52, 1.0, None, 1), Placed(140, 90, 80, 150, -1.5, 235, 2),
        Placed(140, 90, 79, 248, 0.7, 215, 3)],
    "three landscape and one portrait": [
        Placed(100, 70, 58, 45, 1.2, None, 1), Placed(100, 70, 58, 125, -0.8, 240, 2),
        Placed(100, 70, 58, 205, 0, 200, 3), Placed(70, 100, 160, 125, -1.0, None, 4)],
    "photos in the corner of the glass": [
        Placed(150, 100, 75, 50, 0, None, 5), Placed(150, 100, 75, 155, 0.4, None, 6)],
    "white border on white lid": [Placed(150, 100, 100, 80, 3, 250, 7)],
}


def _distance(region: CropRegion, photo: Placed) -> float:
    """Return the distance of a region centre from a photo centre in millimetres.

    Args:
        region: Detected region.
        photo: Placed photo.

    Returns:
        Manhattan distance.
    """
    return abs(region.cx / MM - photo.cx_mm) + abs(region.cy / MM - photo.cy_mm)


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_detector_finds_every_photo(name: str) -> None:
    """Count, position, size and skew match the placed photos.

    Args:
        name: Layout to test.
    """
    placed = LAYOUTS[name]
    found = PhotoDetector().detect(scan(placed), DPI)
    assert len(found) == len(placed)
    for truth in placed:
        best = min(found, key=functools.partial(_distance, photo=truth))
        assert abs(best.cx / MM - truth.cx_mm) < 2 and abs(best.cy / MM - truth.cy_mm) < 2
        assert abs(best.width / MM - truth.width_mm) < 3
        assert abs(best.height / MM - truth.height_mm) < 3
        assert abs(best.angle - truth.angle) < 0.5


def test_detector_ignores_empty_glass_and_specks() -> None:
    """An empty scan and small specks give no regions."""
    empty = scan([])
    assert not PhotoDetector().detect(empty, DPI)
    speck = scan([Placed(10, 10, 50, 50)])
    assert not PhotoDetector().detect(speck, DPI)


def test_detector_skips_sparse_shapes() -> None:
    """A thin diagonal line has a large box but little area."""
    pixels = scan([])
    for offset in range(4):
        diagonal = np.arange(100, 800)
        pixels[diagonal + offset, diagonal] = 30
    assert not PhotoDetector().detect(pixels, DPI)
    assert CropRegion(0, 0, 1, 1).quarter_turns == 0
