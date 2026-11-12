"""Free editing of a photo frame: move, resize, rotate, describe."""

import math
from dataclasses import replace

from scanbench.domain.crop_region import CropRegion
from scanbench.domain.frame_handle import FrameHandle

MIN_SIDE_MM = 5.0
"""A frame never becomes smaller than this."""


def to_local(region: CropRegion, x: float, y: float) -> tuple[float, float]:
    """Convert a scan point into the frame's own axes (origin in its centre).

    Args:
        region: The frame.
        x: Scan x in pixels.
        y: Scan y in pixels.

    Returns:
        ``(u, v)``: u along the frame's width, v along its height.
    """
    rad = math.radians(region.angle)
    dx, dy = x - region.cx, y - region.cy
    return dx * math.cos(rad) + dy * math.sin(rad), -dx * math.sin(rad) + dy * math.cos(rad)


def to_scan(region: CropRegion, u: float, v: float) -> tuple[float, float]:
    """Convert a point in the frame's axes back into scan pixels.

    Args:
        region: The frame.
        u: Offset along the width.
        v: Offset along the height.

    Returns:
        Scan x and y.
    """
    rad = math.radians(region.angle)
    return (region.cx + u * math.cos(rad) - v * math.sin(rad),
            region.cy + u * math.sin(rad) + v * math.cos(rad))


def handle_point(region: CropRegion, handle: FrameHandle, rotate_gap: float) -> tuple[float, float]:
    """Return where a grip sits on the scan.

    Args:
        region: The frame.
        handle: The grip.
        rotate_gap: Distance of the rotation grip above the top edge, in pixels.

    Returns:
        Scan x and y of the grip.
    """
    if handle is FrameHandle.ROTATE:
        return to_scan(region, 0.0, -region.height / 2 - rotate_gap)
    return to_scan(region, handle.sx * region.width / 2, handle.sy * region.height / 2)


def moved(region: CropRegion, dx: float, dy: float) -> CropRegion:
    """Shift a frame.

    Args:
        region: The frame.
        dx: Shift in x, pixels.
        dy: Shift in y, pixels.

    Returns:
        The shifted frame.
    """
    return replace(region, cx=region.cx + dx, cy=region.cy + dy)


def resized(region: CropRegion, handle: FrameHandle, x: float, y: float,
            min_side: float) -> CropRegion:
    """Drag a side or corner grip to a scan point; the opposite side stays.

    Args:
        region: The frame.
        handle: A side or corner grip (not ``ROTATE``).
        x: Scan x of the mouse.
        y: Scan y of the mouse.
        min_side: Minimum side length in pixels.

    Returns:
        The resized frame with unchanged angle.
    """
    u, v = to_local(region, x, y)
    centre_u, centre_v, width, height = 0.0, 0.0, region.width, region.height
    if handle.sx:
        fixed = -handle.sx * region.width / 2
        width = max(min_side, handle.sx * (u - fixed))
        centre_u = fixed + handle.sx * width / 2
    if handle.sy:
        fixed = -handle.sy * region.height / 2
        height = max(min_side, handle.sy * (v - fixed))
        centre_v = fixed + handle.sy * height / 2
    cx, cy = to_scan(region, centre_u, centre_v)
    return replace(region, cx=cx, cy=cy, width=width, height=height)


def rotated_towards(region: CropRegion, x: float, y: float, step: float = 0.0) -> CropRegion:
    """Turn the frame so that its top points at a scan point.

    Args:
        region: The frame.
        x: Scan x of the mouse.
        y: Scan y of the mouse.
        step: Snap the angle to multiples of this many degrees; 0 for none.

    Returns:
        The turned frame; ``angle`` lies in (-180, 180].
    """
    angle = math.degrees(math.atan2(x - region.cx, region.cy - y))
    if step > 0:
        angle = round(angle / step) * step
    angle = -((-angle + 180) % 360 - 180)
    return replace(region, angle=angle)


def turned_by(region: CropRegion, degrees: float) -> CropRegion:
    """Change the skew by a small amount.

    Args:
        region: The frame.
        degrees: Change, positive clockwise.

    Returns:
        The turned frame.
    """
    return replace(region, angle=round(region.angle + degrees, 3))


def transferred(region: CropRegion, factor: float, dx: float, dy: float) -> CropRegion:
    """Carry a frame over to another scan of the same glass.

    Used when a preview scan was followed by a scan of a smaller area at a
    higher resolution: new = old x factor - offset.

    Args:
        region: Frame in pixels of the first scan.
        factor: Resolution of the new scan divided by that of the first.
        dx: Left edge of the new scan, in pixels of the new scan.
        dy: Top edge of the new scan, in pixels of the new scan.

    Returns:
        The frame in pixels of the new scan, with angle and turns unchanged.
    """
    return replace(region, cx=region.cx * factor - dx, cy=region.cy * factor - dy,
                   width=region.width * factor, height=region.height * factor)


def bounding_area_mm(regions: list[CropRegion], dpi: int,
                     margin_mm: float) -> tuple[float, float, float, float]:
    """Return the rectangle around all frames, with a margin, in millimetres.

    Args:
        regions: Frames in scan pixels.
        dpi: Resolution of that scan.
        margin_mm: Margin added on every side.

    Returns:
        Left, top, width, height in millimetres.
    """
    mm = 25.4 / dpi
    xs = [x for r in regions for x, _ in r.corners()]
    ys = [y for r in regions for _, y in r.corners()]
    left, top = min(xs) * mm - margin_mm, min(ys) * mm - margin_mm
    return (left, top, max(xs) * mm + margin_mm - left, max(ys) * mm + margin_mm - top)


def merged(regions: list[CropRegion]) -> CropRegion:
    """Join frames into one, e.g. after one photo was split by mistake.

    The result has the skew and turn of the first frame and encloses all
    corners of all frames.

    Args:
        regions: At least one frame.

    Returns:
        The enclosing frame.
    """
    first = regions[0]
    local = [to_local(first, x, y) for r in regions for x, y in r.corners()]
    us, vs = [u for u, _ in local], [v for _, v in local]
    cx, cy = to_scan(first, (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2)
    return replace(first, cx=cx, cy=cy, width=max(us) - min(us), height=max(vs) - min(vs))


def summary(region: CropRegion, dpi: int) -> str:
    """Describe size, skew and output turn of a frame.

    Args:
        region: The frame.
        dpi: Resolution of the scan.

    Returns:
        E.g. ``101 x 71 mm, skew -0.8°, saved turned 90° clockwise``.
    """
    mm = 25.4 / dpi
    turn = {0: "saved as framed", 1: "saved turned 90° clockwise",
            2: "saved turned 180°", 3: "saved turned 90° counter-clockwise"}
    width, height = region.width * mm, region.height * mm
    return (f"{width:.0f} x {height:.0f} mm, skew {region.angle:+.1f}°, "
            f"{turn[region.quarter_turns % 4]}")
