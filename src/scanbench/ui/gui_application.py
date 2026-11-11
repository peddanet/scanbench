"""Start the Qt application with the identity the desktop expects."""

from importlib import resources

from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from scanbench.app_info import APP_ID, APP_NAME
from scanbench.ui.main_window import MainWindow


class GuiApplication:
    """Configure the Qt application and run the main window."""

    def __init__(self, version_text: str) -> None:
        """Store the version text for the window.

        Args:
            version_text: Version shown in the status bar.
        """
        self._version_text = version_text
        self.window: MainWindow | None = None

    @staticmethod
    def configure(app: QGuiApplication) -> None:
        """Set name, desktop file name and window icon.

        The desktop file name lets Wayland compositors map windows to the
        launcher entry, so the dock shows the right icon.

        Args:
            app: The application object to configure.
        """
        app.setApplicationName(APP_NAME)
        app.setDesktopFileName(APP_ID)
        svg = resources.files("scanbench.resources").joinpath("icons", f"{APP_ID}.svg")
        pixmap = QPixmap()
        pixmap.loadFromData(svg.read_bytes(), "SVG")
        app.setWindowIcon(QIcon(pixmap))

    def show(self) -> MainWindow:
        """Create and show the main window.

        Returns:
            The shown window.
        """
        self.window = MainWindow(self._version_text)
        self.window.show()
        return self.window

    def run(self, argv: list[str]) -> int:
        """Run the event loop until the window is closed.

        Args:
            argv: Command line handed to Qt (Qt options such as ``-platform``).

        Returns:
            Exit status of the event loop.
        """
        existing = QApplication.instance()
        app = existing if isinstance(existing, QApplication) else QApplication(argv)
        self.configure(app)
        self.show()
        return app.exec()
