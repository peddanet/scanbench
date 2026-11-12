"""Tests for free frame editing: grips, move, resize, rotate, summary."""

import math

import pytest

from scanbench.domain import frame_edit
from scanbench.domain.crop_region import CropRegion
from scanbench.domain.frame_handle import FrameHandle
from scanbench.domain.frame_history import FrameHistory
from scanbench.domain.scan_area import ScanArea

FRAME = CropRegion(100.0, 100.0, 60.0, 40.0)
"""Axis-parallel frame from (70, 80) to (130, 120)."""


def test_local_and_scan_coordinates_are_inverse() -> None:
    """Converting to the frame axes and back returns the point."""
    region = CropRegion(50, 60, 30, 20, 33.0)
    u, v = frame_edit.to_local(region, 71.0, 44.0)
    assert frame_edit.to_scan(region, u, v) == pytest.approx((71.0, 44.0))


def test_handle_points() -> None:
    """Corners, sides and the rotation grip sit where expected."""
    assert frame_edit.handle_point(FRAME, FrameHandle.TOP_LEFT, 10) == pytest.approx((70, 80))
    assert frame_edit.handle_point(FRAME, FrameHandle.RIGHT, 10) == pytest.approx((130, 100))
    assert frame_edit.handle_point(FRAME, FrameHandle.ROTATE, 10) == pytest.approx((100, 70))
    assert (FrameHandle.BOTTOM.sx, FrameHandle.BOTTOM.sy) == (0, 1)


def test_resize_keeps_the_opposite_side() -> None:
    """Dragging the right side or a corner moves only that side or corner."""
    wider = frame_edit.resized(FRAME, FrameHandle.RIGHT, 150, 0, 5)
    assert (wider.width, wider.height) == (80, 40) and wider.cx == 110 and wider.cy == 100
    corner = frame_edit.resized(FRAME, FrameHandle.TOP_LEFT, 60, 70, 5)
    assert (corner.width, corner.height) == (70, 50)
    assert (corner.cx, corner.cy) == (95, 95)
    tiny = frame_edit.resized(FRAME, FrameHandle.BOTTOM, 0, 0, 5)
    assert tiny.height == 5 and tiny.cy == pytest.approx(82.5)


def test_resize_of_a_turned_frame_follows_its_axes() -> None:
    """On a frame turned by 90 degrees the "right" grip points down."""
    turned = CropRegion(100, 100, 60, 40, 90.0)
    longer = frame_edit.resized(turned, FrameHandle.RIGHT, 100, 150, 5)
    assert longer.width == pytest.approx(80) and longer.cy == pytest.approx(110)


def test_rotate_towards_and_steps() -> None:
    """The top points at the mouse; Shift steps snap; angles stay in (-180, 180]."""
    right = frame_edit.rotated_towards(FRAME, 200, 100)
    assert right.angle == pytest.approx(90)
    below = frame_edit.rotated_towards(FRAME, 100, 200)
    assert below.angle == pytest.approx(180)
    left = frame_edit.rotated_towards(FRAME, 0, 100)
    assert left.angle == pytest.approx(-90)
    x = 100 + 100 * math.sin(math.radians(1.3))
    y = 100 - 100 * math.cos(math.radians(1.3))
    assert frame_edit.rotated_towards(FRAME, x, y, 0.5).angle == pytest.approx(1.5)


def test_move_turn_and_summary() -> None:
    """Small steps and the text of the details line."""
    assert frame_edit.moved(FRAME, 3, -2).cx == 103
    assert frame_edit.turned_by(FRAME, -0.1).angle == pytest.approx(-0.1)
    region = CropRegion(0, 0, 1000, 700, -0.84, 1)
    assert frame_edit.summary(region, 254) == \
        "100 x 70 mm, skew -0.8°, saved turned 90° clockwise"
    assert "saved as framed" in frame_edit.summary(FRAME, 254)


def test_transfer_bounding_area_and_merge() -> None:
    """Frames move to an area scan, enclose an area and merge into one."""
    region = CropRegion(100, 50, 40, 20, 2.0, 1)
    moved_over = frame_edit.transferred(region, 4.0, 300, 100)
    assert (moved_over.cx, moved_over.cy, moved_over.width, moved_over.height) == \
        (100, 100, 160, 80)
    assert (moved_over.angle, moved_over.quarter_turns) == (2.0, 1)
    left, top, width, height = frame_edit.bounding_area_mm(
        [CropRegion(100, 100, 100, 100), CropRegion(300, 200, 100, 100)], 254, 1.0)
    assert (left, top) == pytest.approx((4.0, 4.0))
    assert (width, height) == pytest.approx((32.0, 22.0))
    joined = frame_edit.merged([CropRegion(50, 50, 100, 100), CropRegion(50, 150, 100, 100)])
    assert (joined.cx, joined.cy, joined.width, joined.height) == pytest.approx((50, 100, 100, 200))


def test_frame_history_undo_redo() -> None:
    """Steps are recorded, undone and redone; a new edit drops redo steps."""
    first, second, third = (CropRegion(i, i, 10, 10) for i in (1, 2, 3))
    history = FrameHistory(limit=2)
    history.reset([first])
    assert not history.can_undo() and history.undo() is None and history.redo() is None
    history.record([first])
    assert not history.can_undo()
    history.record([second])
    history.record([third])
    history.record([first, third])
    assert history.undo() == (third,) and history.undo() == (second,)
    assert history.undo() is None
    assert history.can_redo() and history.redo() == (third,)
    history.record([])
    assert not history.can_redo() and history.current == ()


def test_scan_area_clamped() -> None:
    """Areas are kept inside the glass."""
    assert ScanArea(-5, 10, 300, 400).clamped(216, 297) == ScanArea(0, 10, 216, 287)
    assert ScanArea(250, 300, 10, 10).clamped(216, 297) == ScanArea(216, 297, 0, 0)
