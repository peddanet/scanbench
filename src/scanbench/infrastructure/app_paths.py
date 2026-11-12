"""Locations of configuration, logs, installed release and desktop files."""

from collections.abc import Mapping
from pathlib import Path

from scanbench.app_info import APP_NAME
from scanbench.infrastructure.release_layout import ReleaseLayout


class AppPaths:
    """Resolve all directories the application reads or writes.

    Two layouts are supported:

    * XDG layout (default): configuration below ``$XDG_CONFIG_HOME``, logs
      below ``$XDG_STATE_HOME``, the installed release below
      ``$XDG_DATA_HOME``.
    * Single-root layout: if ``SCANBENCH_HOME`` is set, configuration, logs and
      release all live below that one directory (e.g. ``~/scripts/scanbench.d``).

    Desktop file and icon always go below ``$XDG_DATA_HOME``, because desktop
    environments only search there.
    """

    def __init__(self, environ: Mapping[str, str], home: Path) -> None:
        """Store the environment and the home directory.

        Args:
            environ: Environment variables, usually ``os.environ``.
            home: Home directory of the user.
        """
        self._environ = environ
        self._home = home

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

    def _root(self) -> Path | None:
        """Return the single-root directory if ``SCANBENCH_HOME`` is set.

        Returns:
            The expanded directory, or None for the XDG layout.
        """
        value = self._environ.get("SCANBENCH_HOME", "")
        return Path(value).expanduser() if value else None

    @property
    def config_dir(self) -> Path:
        """Directory of settings and device profiles.

        Returns:
            The configuration directory.
        """
        root = self._root()
        if root is not None:
            return root / "config"
        return self._xdg("XDG_CONFIG_HOME", ".config") / APP_NAME

    @property
    def log_dir(self) -> Path:
        """Directory of log files.

        Returns:
            The log directory.
        """
        root = self._root()
        if root is not None:
            return root / "logs"
        return self._xdg("XDG_STATE_HOME", ".local/state") / APP_NAME / "logs"

    @property
    def cache_dir(self) -> Path:
        """Directory of the work files of running sessions (raw scans).

        Raw scans can be large, so they go to disk and not to ``/tmp``,
        which is a RAM file system on many distributions.

        Returns:
            The cache directory.
        """
        root = self._root()
        if root is not None:
            return root / "cache"
        return self._xdg("XDG_CACHE_HOME", ".cache") / APP_NAME

    @property
    def release_dir(self) -> Path:
        """Directory that holds the venv of the installed release.

        Returns:
            The release directory.
        """
        root = self._root()
        if root is not None:
            return root
        return self._xdg("XDG_DATA_HOME", ".local/share") / APP_NAME

    @property
    def sessions_dir(self) -> Path:
        """Directory of saved sessions and of the handover to a new release.

        Returns:
            The sessions directory.
        """
        root = self._root()
        if root is not None:
            return root / "sessions"
        return self._xdg("XDG_DATA_HOME", ".local/share") / APP_NAME / "sessions"

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
            Versioned venvs, active link, archive store and lock file.
        """
        return ReleaseLayout(self.release_dir)

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
