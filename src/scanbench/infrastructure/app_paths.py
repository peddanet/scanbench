"""Locations of configuration, logs, installed release and desktop files."""

from collections.abc import Mapping
from pathlib import Path

from scanbench.app_info import APP_NAME
from scanbench.infrastructure.release_layout import ReleaseLayout


class AppPaths:
    """Resolve all directories the application reads or writes (XDG layout).

    Category first, then tool (dev-conventions v8): configuration below
    ``$XDG_CONFIG_HOME``, state (logs, update lock) below ``$XDG_STATE_HOME``,
    re-creatable work files below ``$XDG_CACHE_HOME``, installed releases and
    sessions below ``$XDG_DATA_HOME``. Desktop file and icon also go below
    ``$XDG_DATA_HOME``, because desktop environments only search there.

    The single-root layout of older releases (``SCANBENCH_HOME``) is no longer
    supported; ``LegacyLayout`` moves its files here once.
    """

    def __init__(self, environ: Mapping[str, str], home: Path) -> None:
        """Store the environment and the home directory.

        Args:
            environ: Environment variables, usually ``os.environ``.
            home: Home directory of the user.
        """
        self._environ = environ
        self._home = home
        self.home = home

    def _xdg(self, variable: str, default: str) -> Path:
        """Return an XDG base directory, honouring an absolute override.

        Args:
            variable: Name of the XDG variable, e.g. ``XDG_CONFIG_HOME``.
            default: Path relative to the home directory if unset or relative.

        Returns:
            The base directory.
        """
        value = self._environ.get(variable, "")
        # The XDG specification says relative values are invalid and ignored.
        if value and Path(value).is_absolute():
            return Path(value)
        return self._home / default

    @property
    def config_dir(self) -> Path:
        """Directory of settings and presets.

        Returns:
            ``$XDG_CONFIG_HOME/scanbench``.
        """
        return self._xdg("XDG_CONFIG_HOME", ".config") / APP_NAME

    def _state(self) -> Path:
        """Return the directory of state that survives a restart.

        Returns:
            ``$XDG_STATE_HOME/scanbench``; holds ``logs/`` and the update lock.
        """
        return self._xdg("XDG_STATE_HOME", ".local/state") / APP_NAME

    @property
    def log_dir(self) -> Path:
        """Directory of log files.

        Returns:
            ``$XDG_STATE_HOME/scanbench/logs``.
        """
        return self._state() / "logs"

    @property
    def cache_dir(self) -> Path:
        """Directory of the work files of running sessions (raw scans).

        Raw scans can be large, so they go to disk and not to ``/tmp``,
        which is a RAM file system on many distributions.

        Returns:
            ``$XDG_CACHE_HOME/scanbench``.
        """
        return self._xdg("XDG_CACHE_HOME", ".cache") / APP_NAME

    @property
    def release_dir(self) -> Path:
        """Directory that holds the venvs of the installed releases.

        Returns:
            ``$XDG_DATA_HOME/scanbench``.
        """
        return self._xdg("XDG_DATA_HOME", ".local/share") / APP_NAME

    @property
    def sessions_dir(self) -> Path:
        """Directory of saved sessions and of the handover to a new release.

        Returns:
            ``$XDG_DATA_HOME/scanbench/sessions``.
        """
        return self.release_dir / "sessions"

    @property
    def applications_dir(self) -> Path:
        """Directory searched by desktops for ``.desktop`` files.

        Returns:
            The per-user applications directory.
        """
        return self._xdg("XDG_DATA_HOME", ".local/share") / "applications"

    @property
    def icon_dir(self) -> Path:
        """Directory of scalable application icons in the hicolor theme.

        Returns:
            The per-user icon directory.
        """
        data = self._xdg("XDG_DATA_HOME", ".local/share")
        return data / "icons" / "hicolor" / "scalable" / "apps"

    @property
    def release(self) -> ReleaseLayout:
        """Layout of the installation below the release directory.

        Returns:
            Versioned venvs, active link, archive store and the update lock
            (below ``$XDG_STATE_HOME/scanbench``).
        """
        return ReleaseLayout(self.release_dir, self._state() / "update.lock")

    @property
    def clone_dir(self) -> Path:
        """Maintainer's git clone used by ``update`` and ``publish``.

        Returns:
            ``$SCANBENCH_CLONE`` or ``~/Projects/scanbench``.
        """
        value = self._environ.get("SCANBENCH_CLONE", "")
        return Path(value).expanduser() if value else self._home / "Projects" / "scanbench"

    @property
    def downloads_dir(self) -> Path:
        """Folder searched for delivered patch archives.

        Returns:
            ``$XDG_DOWNLOAD_DIR`` if absolute, else ``~/Downloads``.
        """
        return self._xdg("XDG_DOWNLOAD_DIR", "Downloads")
