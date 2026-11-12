"""Find delivered patch archives in the download folder."""

import hashlib
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

    def all_archives(self) -> list[PatchArchive]:
        """Return every delivered archive in the folder, with all copies.

        Returns:
            Archives in name order.
        """
        candidates = sorted(self._folder.glob("scanbench-*-patch*.tar.gz")) \
            if self._folder.is_dir() else []
        return [a for a in map(PatchArchive.from_path, candidates) if a is not None]

    def newest_per_version(self) -> dict[Version, PatchArchive]:
        """Return one archive per version: highest delivery number, then newest copy.

        Returns:
            Mapping of version to archive.
        """
        best: dict[Version, PatchArchive] = {}
        for archive in self.all_archives():
            rank = (archive.build, archive.path.stat().st_mtime)
            known = best.get(archive.version)
            if known is None or rank >= (known.build, known.path.stat().st_mtime):
                best[archive.version] = archive
        return best

    def obsolete(self, released: Version | None, keep: list[PatchArchive]) -> list[PatchArchive]:
        """Return the archives that are no longer needed.

        These are archives of released versions and older deliveries or copies
        of a version whose newest delivery is still pending.

        Args:
            released: Newest released version, or None.
            keep: Archives still to be applied.

        Returns:
            Archives to move out of the download folder.
        """
        kept = {a.path for a in keep}
        return [a for a in self.all_archives() if a.path not in kept and (
            (released is not None and a.version <= released)
            or a.version in {k.version for k in keep})]

    @staticmethod
    def digest(archive: PatchArchive) -> str:
        """Return the SHA-256 of an archive (identifies one delivery).

        Args:
            archive: The archive.

        Returns:
            Hex digest.
        """
        return hashlib.sha256(archive.path.read_bytes()).hexdigest()

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
