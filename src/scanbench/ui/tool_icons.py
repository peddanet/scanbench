"""Symbols of the frame editor tools: the desktop's icon theme, else drawn ones.

Standard actions use names of the freedesktop Icon Naming Specification
(e.g. ``zoom-in``), so they look like the rest of the desktop. Tools without
a standard name (draw frame, guides, exact values) and every tool on a
system without an icon theme get a simple drawn symbol in the text colour.
"""

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPen, QPixmap

SIZE = 24
"""Edge of the drawn symbols in pixels."""

THEME_NAMES = {"undo": "edit-undo", "redo": "edit-redo", "zoom_in": "zoom-in",
               "zoom_out": "zoom-out", "fit": "zoom-fit-best", "actual": "zoom-original",
               "previous": "go-previous", "next": "go-next"}
"""Icon theme names of the standard actions."""

GUIDE_COLOUR = QColor(230, 0, 140)
"""Colour of guide lines, as in the scan view."""

Drawing = Callable[[QPainter], None]
"""Draws a symbol on a SIZE x SIZE canvas."""


def _arrow(painter: QPainter, back: bool) -> None:
    """Draw a curved undo or redo arrow.

    Args:
        painter: Active painter.
        back: True for undo.
    """
    painter.drawArc(QRectF(5, 7, 14, 12), 0 if back else 180 * 16, 180 * 16 if back else -180 * 16)
    tip = QPointF(5, 13) if back else QPointF(19, 13)
    side = 1 if back else -1
    painter.drawLine(tip, tip + QPointF(-3 * side, -4))
    painter.drawLine(tip, tip + QPointF(4 * side, -2))


def _lens(painter: QPainter, sign: str) -> None:
    """Draw a magnifier with a plus, minus or text inside.

    Args:
        painter: Active painter.
        sign: ``+``, ``-``, ``fit`` or ``1:1``.
    """
    painter.drawEllipse(QRectF(3, 3, 13, 13))
    painter.drawLine(QPointF(14, 14), QPointF(21, 21))
    if sign in "+-":
        painter.drawLine(QPointF(6.5, 9.5), QPointF(12.5, 9.5))
    if sign == "+":
        painter.drawLine(QPointF(9.5, 6.5), QPointF(9.5, 12.5))
    if sign == "fit":
        painter.drawRect(QRectF(6.5, 6.5, 6, 6))
    if sign == "1:1":
        font = painter.font()
        font.setPixelSize(7)
        painter.setFont(font)
        painter.drawText(QRectF(3, 3, 13, 13), Qt.AlignmentFlag.AlignCenter, "1:1")


def _frame(painter: QPainter) -> None:
    """Draw a dashed frame with a plus: draw a new frame.

    Args:
        painter: Active painter.
    """
    pen = painter.pen()
    dashed = QPen(pen)
    dashed.setStyle(Qt.PenStyle.DashLine)
    painter.setPen(dashed)
    painter.drawRect(QRectF(3, 5, 14, 12))
    painter.setPen(pen)
    painter.drawLine(QPointF(19, 15), QPointF(19, 22))
    painter.drawLine(QPointF(15.5, 18.5), QPointF(22.5, 18.5))


def _guide(painter: QPainter, horizontal: bool, crossed: bool = False) -> None:
    """Draw a dashed guide line, optionally crossed out.

    Args:
        painter: Active painter.
        horizontal: Direction of the line.
        crossed: Draw a cross over it (remove guides).
    """
    pen = painter.pen()
    guide = QPen(GUIDE_COLOUR, 2, Qt.PenStyle.DashLine)
    painter.setPen(guide)
    if horizontal:
        painter.drawLine(QPointF(2, 12), QPointF(22, 12))
    if not horizontal or crossed:
        painter.drawLine(QPointF(12, 2), QPointF(12, 22))
    painter.setPen(pen)
    if crossed:
        painter.drawLine(QPointF(5, 5), QPointF(19, 19))
        painter.drawLine(QPointF(19, 5), QPointF(5, 19))


def _values(painter: QPainter) -> None:
    """Draw a ruler with ticks: exact values.

    Args:
        painter: Active painter.
    """
    painter.drawRect(QRectF(2, 8, 20, 8))
    for x in range(5, 21, 3):
        painter.drawLine(QPointF(x, 8), QPointF(x, 11 if x % 2 else 13))


def _chevron(painter: QPainter, back: bool) -> None:
    """Draw a chevron: previous or next photo.

    Args:
        painter: Active painter.
        back: True for previous.
    """
    x1, x2 = (15, 8) if back else (9, 16)
    painter.drawLine(QPointF(x1, 5), QPointF(x2, 12))
    painter.drawLine(QPointF(x2, 12), QPointF(x1, 19))


DRAWINGS: dict[str, Drawing] = {
    "undo": lambda p: _arrow(p, True), "redo": lambda p: _arrow(p, False),
    "zoom_in": lambda p: _lens(p, "+"), "zoom_out": lambda p: _lens(p, "-"),
    "fit": lambda p: _lens(p, "fit"), "actual": lambda p: _lens(p, "1:1"),
    "draw": _frame, "h_guide": lambda p: _guide(p, True),
    "v_guide": lambda p: _guide(p, False), "no_guides": lambda p: _guide(p, True, True),
    "values": _values, "previous": lambda p: _chevron(p, True),
    "next": lambda p: _chevron(p, False)}
"""Drawn symbol per tool key."""


def drawn(key: str) -> QIcon:
    """Return the drawn symbol of a tool in the text colour of the palette.

    Args:
        key: Tool key, e.g. ``draw``.

    Returns:
        The icon.
    """
    pixmap = QPixmap(SIZE, SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    colour = QGuiApplication.palette().color(QPalette.ColorRole.ButtonText)
    painter.setPen(QPen(colour, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    DRAWINGS[key](painter)
    painter.end()
    return QIcon(pixmap)


def tool_icon(key: str) -> QIcon:
    """Return the symbol of a tool: from the icon theme if it has one.

    Args:
        key: Tool key.

    Returns:
        The icon.
    """
    name = THEME_NAMES.get(key)
    if name is not None and QIcon.hasThemeIcon(name):
        return QIcon.fromTheme(name)
    return drawn(key)
