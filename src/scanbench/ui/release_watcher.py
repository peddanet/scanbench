"""Notice when a newer release has been installed while the window is open."""

import os
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from scanbench.domain.version import Version


class ReleaseWatcher(QObject):
    """Poll the ``venv`` link of the installation and report newer releases.

    ``install.sh`` installs every release into ``venvs/X.Y.Z`` and switches
    the link afterwards; reading the link target is cheap and needs no
    import of the new release.
    """

    new_release = Signal(str)
    """Emitted once per newer release with its version text."""

    def __init__(self, link: Path, running: Version, interval_ms: int = 30_000,
                 parent: QObject | None = None) -> None:
        """Start polling.

        Args:
            link: The ``venv`` link of the installation.
            running: Version of the running program.
            interval_ms: Poll interval in milliseconds.
            parent: Qt parent object.
        """
        super().__init__(parent)
        self._link = link
        self._running = running
        self._announced: Version | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)
        self._timer.start(interval_ms)

    def installed(self) -> Version | None:
        """Return the version the link points at.

        Returns:
            The installed version, or None without a versioned installation.
        """
        if not self._link.is_symlink():
            return None
        try:
            return Version.parse(Path(os.readlink(self._link)).name)
        except ValueError:
            return None

    def check(self) -> None:
        """Emit ``new_release`` if a newer release is installed."""
        installed = self.installed()
        if installed is not None and installed > self._running \
                and installed != self._announced:
            self._announced = installed
            self.new_release.emit(str(installed))
