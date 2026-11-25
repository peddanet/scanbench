"""Fixed identity of the application, shared by desktop integration and GUI."""

APP_NAME = "scanbench"
"""Human-readable application name, also the command name."""

APP_ID = "io.github.peddanet.scanbench"
"""Reverse-DNS application ID; desktop file and icon are named after it.

Wayland compositors match the window to the launcher entry through this ID,
which the GUI passes to ``QGuiApplication.setDesktopFileName``.
"""

ICON_FILE = "scanbench.svg"
"""Program icon in the package folder ``scanbench/data``. Installed into the
icon theme under the application ID (``<APP_ID>.svg``)."""
