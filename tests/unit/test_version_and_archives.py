"""Tests for Version, PatchArchive and ArchiveFinder."""

import os
from pathlib import Path

import pytest

from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.version import Version
from scanbench.infrastructure.archive_finder import ArchiveFinder


def test_version_parse_order_and_tag() -> None:
    """Versions parse with or without v, sort numerically and print as X.Y.Z."""
    assert Version.parse("v0.10.0") > Version.parse("0.9.9")
    assert str(Version.parse(" 1.2.3 ")) == "1.2.3"
    assert Version(1, 2, 3).tag == "v1.2.3"
    with pytest.raises(ValueError):
        Version.parse("1.2")


def test_archive_names() -> None:
    """Originals and browser copies are recognised, other files not."""
    copy = PatchArchive.from_path(Path("scanbench-0.2.0-patch(2).tar.gz"))
    assert copy is not None and copy.copy == 2 and str(copy.version) == "0.2.0"
    assert PatchArchive.from_path(Path("scanbench-0.2.0-patch.tar.gz")) is not None
    assert PatchArchive.from_path(Path("other-0.2.0-patch.tar.gz")) is None


def test_finder_newest_copy_and_pending(tmp_path: Path) -> None:
    """The newest copy per version wins; only versions after the release count.

    Args:
        tmp_path: Temporary directory of the test.
    """
    for name, mtime in [("scanbench-0.1.1-patch.tar.gz", 100),
                        ("scanbench-0.1.1-patch(1).tar.gz", 200),
                        ("scanbench-0.1.0-patch.tar.gz", 50),
                        ("scanbench-0.1.2-patch.tar.gz", 300),
                        ("scanbench-x-patch.tar.gz", 300)]:
        path = tmp_path / name
        path.write_bytes(b"")
        os.utime(path, (mtime, mtime))
    finder = ArchiveFinder(tmp_path)
    assert finder.newest_per_version()[Version(0, 1, 1)].copy == 1
    pending = finder.pending(Version(0, 1, 0))
    assert [str(a.version) for a in pending] == ["0.1.1", "0.1.2"]
    assert len(finder.pending(None)) == 3


def test_finder_without_folder(tmp_path: Path) -> None:
    """A missing download folder yields nothing.

    Args:
        tmp_path: Temporary directory of the test.
    """
    assert not ArchiveFinder(tmp_path / "missing").pending(None)
