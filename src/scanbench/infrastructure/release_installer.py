"""Install a release tag with ``install.sh`` and report the active release."""

import os
from pathlib import Path

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.shell import Shell


class ReleaseInstaller:
    """Install releases into versioned venvs and read which one is active."""

    def __init__(self, paths: AppPaths, shell: Shell) -> None:
        """Store the paths and the shell that runs in the clone.

        Args:
            paths: Resolver of the release directories.
            shell: Shell whose working directory is the clone.
        """
        self._paths = paths
        self._shell = shell

    def active_version(self) -> Version | None:
        """Return the release the ``venv`` link points at.

        Returns:
            The active version, or None if no versioned release is installed.
        """
        link = self._paths.release.venv_link
        if not link.is_symlink():
            return None
        try:
            return Version.parse(Path(os.readlink(link)).name)
        except ValueError:
            return None

    def install(self, version: Version) -> None:
        """Install a release; ``install.sh`` checks the reported version.

        Args:
            version: Release to install.

        Raises:
            UpdateError: If the installation fails.
        """
        script = str(self._shell.cwd / "install.sh")
        if self._shell.live("bash", script, version.tag) != 0:
            raise UpdateError(f"installation of {version.tag} failed")
