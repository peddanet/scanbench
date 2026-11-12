"""Start the Qt application with the identity the desktop expects."""

import logging
import sys
from importlib import resources
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from scanbench import __version__
from scanbench.app_info import APP_ID, APP_NAME
from scanbench.application.session_handover import SessionHandover
from scanbench.infrastructure.app_log import LOGGER, AppLog
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.ui.main_window import MainWindow
from scanbench.ui.release_watcher import ReleaseWatcher
from scanbench.ui.update_dialog import UpdateDialog
from scanbench.ui.workbench import Workbench, build_workbench


HANDOVER_DIR = "handover"
"""Directory below the sessions directory used for release switches."""


class GuiApplication:
    """Configure the Qt application, wire window, update dialog and watcher."""

    def __init__(self, version_text: str, paths: AppPaths, is_release: bool) -> None:
        """Store what the window needs.

        Args:
            version_text: Version shown in the status bar.
            paths: Resolver of the installation directories.
            is_release: False when running from a source checkout; then the
                watcher is off, so a development window never switches into
                the installed release.
        """
        self._version_text = version_text
        self._paths = paths
        self._is_release = is_release
        self.window: MainWindow | None = None
        self.dialog: UpdateDialog | None = None
        self.watcher: ReleaseWatcher | None = None
        self.workbench: Workbench | None = None

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

    def open_update(self) -> UpdateDialog:
        """Show the update dialog and start ``scanbench update --yes``.

        Returns:
            The dialog.
        """
        program = str(Path(sys.prefix) / "bin" / "scanbench")
        self.dialog = UpdateDialog(program, ["update", "--yes"], self.window)
        self.dialog.succeeded.connect(self._after_update)
        self.dialog.show()
        self.dialog.start()
        return self.dialog

    def _after_update(self) -> None:
        """Switch automatically if the update installed a newer release."""
        installed = self.watcher.installed() if self.watcher else None
        if self.window is not None and installed is not None \
                and installed > Version.parse(__version__):
            self.window.offer_switch(str(installed), automatic=True)

    def _on_new_release(self, version: str) -> None:
        """Offer the switch to a release installed outside this window.

        While the update dialog of this window is still running, the dialog
        takes care of the switch itself.

        Args:
            version: The installed release.
        """
        running = self.dialog is not None and \
            self.dialog.process.state() != QProcess.ProcessState.NotRunning
        if self.window is not None and not running:
            self.window.offer_switch(version, automatic=False)

    def restart(self, _version: str) -> bool:
        """Start the active release and close this window.

        The open work (scanner, tab, waiting photo scan, document pages) is
        handed over, so the new window continues where this one stopped.

        Returns:
            True if the new process was started.
        """
        launcher = self._paths.release.stable_launcher
        if not launcher.exists():
            return False
        handover = self.handover()
        if self.workbench is not None and self.window is not None:
            handover.save(self.workbench.handover(self.window.tabs.currentIndex()))
        started = bool(QProcess.startDetached(str(launcher), [])[0])
        logging.getLogger(LOGGER).info("switch to the new release: %s",
                                       "started" if started else "start failed")
        if started:
            QApplication.quit()
        else:
            handover.clear()
        return started

    def handover(self) -> SessionHandover:
        """Return the handover between this window and the next release.

        Returns:
            The handover in the sessions directory.
        """
        return SessionHandover(self._paths.sessions_dir / HANDOVER_DIR)

    def _take_over(self, bench: Workbench, window: MainWindow) -> None:
        """Continue the work handed over by the previous release, if any.

        Args:
            bench: The new workbench.
            window: The new window.
        """
        handover = self.handover().take(Path(bench.work.name))
        if handover is None:
            return
        bench.restore(handover)
        window.tabs.setCurrentIndex(handover.tab)
        window.show_message("Continuing the work of the previous version")

    def show(self) -> MainWindow:
        """Create, wire and show the main window.

        Returns:
            The shown window.
        """
        bench = self.workbench = build_workbench(self._paths)
        self.window = MainWindow(self._version_text, tabs=(bench.documents, bench.photos),
                                 header=bench.devices)
        for source in (bench.devices, bench.documents, bench.photos):
            source.message.connect(self.window.show_message)
        self.window.statusBar().insertPermanentWidget(0, bench.progress)
        bench.runner.started.connect(lambda: self._set_busy(True))
        bench.runner.finished.connect(lambda: self._set_busy(False))
        self.window.update_requested.connect(self.open_update)
        self.window.switch_requested.connect(self.restart)
        self.window.cancel_requested.connect(bench.progress.cancel)
        if self._is_release:
            self.watcher = ReleaseWatcher(self._paths.release.venv_link, Version.parse(__version__),
                                          parent=self.window)
            self.watcher.new_release.connect(self._on_new_release)
        self._take_over(bench, self.window)
        for problem in bench.problems:
            self.window.show_message(problem)          # all in the log, the last one visible
        self.window.show()
        bench.devices.restore()
        bench.devices.refresh()
        return self.window

    def _set_busy(self, busy: bool) -> None:
        """Forward job start and end to the window (postpones release switches).

        Args:
            busy: True when a job starts.
        """
        if self.window is not None:
            self.window.set_busy(busy)

    def close(self) -> None:
        """Wait for running jobs and remove the session's raw scans."""
        if self.workbench is not None:
            self.workbench.close()
            self.workbench = None

    def run(self, argv: list[str]) -> int:
        """Run the event loop until the window is closed.

        Args:
            argv: Command line handed to Qt.

        Returns:
            Exit status of the event loop.
        """
        existing = QApplication.instance()
        app = existing if isinstance(existing, QApplication) else QApplication(argv)
        self.configure(app)
        log = AppLog(self._paths.log_dir)
        log.start(self._version_text)
        try:
            self.show()
            return app.exec()
        finally:
            self.close()
            log.stop()
