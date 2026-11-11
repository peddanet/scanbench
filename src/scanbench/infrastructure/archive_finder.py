"""Find delivered patch archives in the download folder."""

from pathlib import Path

from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.version import Version


class ArchiveFinder:
    """Select the archives an update has to apply."""

    def __init__(self, folder: Path) -> None:
        """Store the folder to search.

        Args:
            folder: Usually ``~/Downloads``.
        """
        self._folder = folder

    def newest_per_version(self) -> dict[Version, PatchArchive]:
        """Return one archive per version; the most recently saved copy wins.

        Returns:
            Mapping of version to archive.
        """
        best: dict[Version, PatchArchive] = {}
        candidates = sorted(self._folder.glob("scanbench-*-patch*.tar.gz")) \
            if self._folder.is_dir() else []
        for path in candidates:
            archive = PatchArchive.from_path(path)
            if archive is None:
                continue
            known = best.get(archive.version)
            if known is None or path.stat().st_mtime >= known.path.stat().st_mtime:
                best[archive.version] = archive
        return best

    def pending(self, released: Version | None) -> list[PatchArchive]:
        """Return the archives newer than the released version, ascending.

        Every patch is based on the release before it, so the order matters.

        Args:
            released: Newest released version, or None if nothing is released.

        Returns:
            Archives to apply, oldest first.
        """
        found = self.newest_per_version()
        return [found[v] for v in sorted(found) if released is None or v > released]
