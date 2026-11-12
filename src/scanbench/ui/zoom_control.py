"""Zoom of the frame editor: buttons, keyboard and Ctrl + mouse wheel."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QGraphicsView

if TYPE_CHECKING:
    from scanbench.ui.region_view import RegionView

STEP = 1.25
"""Zoom factor per step."""

LIMITS = (0.05, 16.0)
"""Smallest and largest view scale."""


class ZoomControl(QObject):
    """Zoom in and out around the mouse or the view centre.

    "Fit" shows the whole scan and keeps it fitted when the window is
    resized; any other zoom keeps its scale.
    """

    def __init__(self, view: "RegionView") -> None:
        """Watch the mouse wheel of the view.

        Args:
            view: The frame editor view.
        """
        super().__init__(view)
        self._view = view
        view.viewport().installEventFilter(self)
        view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def scale(self) -> float:
        """Return the current view scale.

        Returns:
            1.0 means one preview pixel per screen pixel.
        """
        return float(self._view.transform().m11())

    def zoom_by(self, factor: float) -> None:
        """Change the zoom by a factor, within the limits.

        Args:
            factor: Values above 1 zoom in.
        """
        current = self.scale()
        target = min(max(current * factor, LIMITS[0]), LIMITS[1])
        self._view.mode.fit = False
        self._view.scale(target / current, target / current)
        self._view.set_regions(self._view.regions, self._view.selected_index(), notify=False)

    def zoom_in(self) -> None:
        """One step closer."""
        self.zoom_by(STEP)

    def zoom_out(self) -> None:
        """One step away."""
        self.zoom_by(1 / STEP)

    def actual_size(self) -> None:
        """Show one scan pixel per screen pixel."""
        self.zoom_by(1 / (self.scale() * self._view.scale_factor))

    def fit(self) -> None:
        """Show the whole scan and keep it fitted."""
        self._view.mode.fit = True
        self._view.fitInView(self._view.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._view.set_regions(self._view.regions, self._view.selected_index(), notify=False)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (Qt API)
        """Zoom with Ctrl + mouse wheel.

        Args:
            watched: The viewport.
            event: The event.

        Returns:
            True if the event was used for zooming.
        """
        if isinstance(event, QWheelEvent) \
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_by(STEP if event.angleDelta().y() > 0 else 1 / STEP)
            return True
        return super().eventFilter(watched, event)
