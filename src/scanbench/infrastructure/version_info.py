"""Version text that distinguishes an installed release from a source checkout."""

from pathlib import Path

from scanbench import __version__


class VersionInfo:
    """Build the version text shown by ``--version`` and in the GUI.

    Code imported from a git clone reports
    ``X.Y.Z (source checkout PATH, not an installed release)``, so that a
    development environment is never mistaken for an installation.
    """

    def __init__(self, package_dir: Path, version: str = __version__) -> None:
        """Store where the package was imported from.

        Args:
            package_dir: Directory of the imported ``scanbench`` package.
            version: Version string of the package.
        """
        self._package_dir = package_dir
        self._version = version

    def checkout_root(self) -> Path | None:
        """Return the repository root if the package lives in a source tree.

        A source tree is recognised by ``src/scanbench`` below a directory that
        contains both ``pyproject.toml`` and ``.git``.

        Returns:
            The repository root, or None for an installed release.
        """
        src_dir = self._package_dir.parent
        root = src_dir.parent
        is_tree = src_dir.name == "src" and (root / "pyproject.toml").is_file()
        return root if is_tree and (root / ".git").exists() else None

    def text(self) -> str:
        """Return the version text.

        Returns:
            The bare version, or the version with a source-checkout marker.
        """
        root = self.checkout_root()
        if root is None:
            return self._version
        return f"{self._version} (source checkout {root}, not an installed release)"
