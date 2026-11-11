"""A delivered patch archive ``scanbench-X.Y.Z-patch.tar.gz``."""

import re
from dataclasses import dataclass
from pathlib import Path

from scanbench.domain.version import Version

_NAME = re.compile(r"^scanbench-(\d+\.\d+\.\d+)-patch(?: ?\((\d+)\))?\.tar\.gz$")
"""File name, including browser copies such as ``... -patch(1).tar.gz``."""


@dataclass(frozen=True)
class PatchArchive:
    """One archive in the download folder.

    Attributes:
        version: Release the archive produces.
        path: Location of the archive.
        copy: Browser copy number; 0 for the original name.
    """

    version: Version
    path: Path
    copy: int

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
        return cls(Version.parse(match[1]), path, int(match[2] or 0))
