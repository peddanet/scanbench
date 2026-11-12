"""Tests of the handover of open work to the next release."""

from pathlib import Path

from scan_fakes import page, write_png
from scanbench.application.document_session import Page
from scanbench.application.photo_session import PhotoScan
from scanbench.application.session_handover import STATE_FILE, Handover, SessionHandover
from scanbench.domain.crop_region import CropRegion
from scanbench.infrastructure.app_paths import AppPaths


def _work(root: Path) -> Path:
    """Create a work directory with the two sub-directories.

    Args:
        root: Where to create it.

    Returns:
        The work directory.
    """
    for sub in ("photos", "documents"):
        (root / sub).mkdir(parents=True)
    return root


def test_round_trip(tmp_path: Path) -> None:
    """State and raw scans arrive in the new work directory; the handover is gone.

    Args:
        tmp_path: Temporary directory of the test.
    """
    old = _work(tmp_path / "old")
    photo = PhotoScan(write_png(old / "photos" / "s.png", page(1), 75), 75,
                      [CropRegion(1, 2, 3, 4, 0.5, 3)], preview=True)
    pages = [Page(write_png(old / "documents" / f"{n}.png", page(n), 300), 300, n, n)
             for n in (1, 2)]
    handover = SessionHandover(tmp_path / "sessions" / "handover")
    handover.save(Handover("pixma:1", 1, photo, pages))
    handover.save(Handover("pixma:1", 1, photo, pages))      # replaces an old one
    new = _work(tmp_path / "new")
    taken = handover.take(new)
    assert taken is not None and (taken.device, taken.tab) == ("pixma:1", 1)
    assert taken.photo is not None and taken.photo.preview and taken.photo.dpi == 75
    assert taken.photo.regions == photo.regions and taken.photo.path.parent == new / "photos"
    assert [(p.quarter_turns, p.batch, p.path.parent) for p in taken.pages] == \
        [(1, 1, new / "documents"), (2, 2, new / "documents")]
    assert not handover.directory.exists() and handover.take(new) is None


def test_empty_and_broken(tmp_path: Path) -> None:
    """An empty state works; a broken one is dropped.

    Args:
        tmp_path: Temporary directory of the test.
    """
    handover = SessionHandover(tmp_path / "h")
    handover.save(Handover())
    taken = handover.take(_work(tmp_path / "w"))
    assert taken is not None and taken.photo is None and not taken.pages
    handover.directory.mkdir()
    (handover.directory / STATE_FILE).write_text("{", encoding="utf-8")
    assert handover.take(tmp_path / "w") is None and not handover.directory.exists()


def test_sessions_dir() -> None:
    """Sessions live below SCANBENCH_HOME or in the XDG data directory."""
    home = Path("/home/u")
    assert AppPaths({"SCANBENCH_HOME": "/opt/sb"}, home).sessions_dir == Path("/opt/sb/sessions")
    assert AppPaths({}, home).sessions_dir == home / ".local/share/scanbench/sessions"
