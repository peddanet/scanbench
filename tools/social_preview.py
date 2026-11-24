#!/usr/bin/env python3
"""Render docs/images/social-preview.svg into the PNG that GitHub shows.

GitHub wants 1280 x 640 pixels, PNG/JPG/GIF, below 1 MB (repository
settings, "Social preview"). Qt renders the SVG offscreen, so no display and
no extra tool are needed. Privilege level: normal user; writes only the PNG.

Usage: python3 tools/social_preview.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
"""Repository root."""

SOURCE = ROOT / "docs" / "images" / "social-preview.svg"
"""Editable source of the picture."""

TARGET = SOURCE.with_suffix(".png")
"""Rendered picture, uploaded to GitHub by hand."""

SIZE = (1280, 640)
"""Width and height required by GitHub."""


def render(source: Path, target: Path) -> None:
    """Render the SVG into a PNG of the required size.

    Args:
        source: SVG file.
        target: PNG file to write.

    Raises:
        ValueError: If the SVG cannot be read or the PNG not written.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # pylint: disable=import-outside-toplevel  # Qt needs the platform set first
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication.instance() or QGuiApplication([])
    renderer = QSvgRenderer(str(source))
    if not renderer.isValid():
        raise ValueError(f"cannot read {source}")
    image = QImage(*SIZE, QImage.Format.Format_RGB32)
    image.fill(QColor("#263238"))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    if not image.save(str(target)):          # format from the suffix .png
        raise ValueError(f"cannot write {target}")
    del app


def main() -> int:
    """Render the social preview and report the result.

    Returns:
        0 on success.
    """
    render(SOURCE, TARGET)
    print(f"{TARGET.relative_to(ROOT)}: {TARGET.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
