"""Layout of an installation: versioned venvs, active link, archives, lock."""

from pathlib import Path


class ReleaseLayout:
    """Paths below the release directory written by ``install.sh``.

    ``venvs/X.Y.Z`` holds one venv per release; ``venv`` is a symbolic link
    to the active one. A running program keeps using its own venv while a
    newer release is installed next to it.
    """

    def __init__(self, root: Path) -> None:
        """Store the release directory.

        Args:
            root: The release directory, e.g. ``~/.local/share/scanbench``.
        """
        self.root = root

    @property
    def venv_link(self) -> Path:
        """Symbolic link to the venv of the active release.

        Returns:
            ``<root>/venv``.
        """
        return self.root / "venv"

    @property
    def stable_launcher(self) -> Path:
        """Launcher that always starts the active release.

        Returns:
            ``<root>/venv/bin/scanbench``.
        """
        return self.venv_link / "bin" / "scanbench"

    @property
    def archive_store(self) -> Path:
        """Directory that keeps applied patch archives.

        Returns:
            ``<root>/releases``.
        """
        return self.root / "releases"

    @property
    def lock_file(self) -> Path:
        """Lock file that prevents parallel updates.

        Returns:
            ``<root>/update.lock``.
        """
        return self.root / "update.lock"
