"""A delivered patch archive ``scanbench-X.Y.Z-patch-N.tar.gz``."""

import re
from dataclasses import dataclass
from pathlib import Path

from scanbench.domain.version import Version

_NAME = re.compile(r"^scanbench-(\d+\.\d+\.\d+)-patch(?:-(\d+))?(?: ?\((\d+)\))?\.tar\.gz$")
"""File name: version, optional delivery number N, optional browser copy number
such as ``... -patch-2(1).tar.gz``. Names without N (before 0.2.4) count as N = 0."""


@dataclass(frozen=True)
class PatchArchive:
    """One archive in the download folder.

    Attributes:
        version: Release the archive produces.
        path: Location of the archive.
        copy: Browser copy number; 0 for the original name.
        build: Delivery number of this version; a later delivery has a higher one.
    """

    version: Version
    path: Path
    copy: int
    build: int = 0

    @classmethod
    def from_path(cls, path: Path) -> "PatchArchive | None":
        """Recognise an archive by its file name.

        Args:
            path: Candidate file.

        Returns:
            The archive, or None if the name does not match.
        """
        match = _NAME.match(path.name)
        if match is None:
            return None
        return cls(Version.parse(match[1]), path, int(match[3] or 0), int(match[2] or 0))
