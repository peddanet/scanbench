"""Unit tests of the paper white correction."""

from pathlib import Path

import numpy as np
from PIL import Image

from scanbench.domain.paper_white import paper_tone, to_paper_white
from scanbench.infrastructure.image_store import ImageStore


def _page(paper: tuple[int, int, int]) -> np.ndarray:
    """Return a page of cream paper with black text lines.

    Args:
        paper: Paper colour.

    Returns:
        RGB page.
    """
    page = np.empty((200, 140, 3), np.uint8)
    page[:] = paper
    page[20:200:20, 10:130] = (20, 20, 25)                  # ten text lines
    return page


def test_cream_paper_becomes_white_and_text_stays_dark() -> None:
    """The paper tone goes to 255 in every channel; text keeps its darkness."""
    page = _page((236, 229, 214))
    assert tuple(paper_tone(page).round()) == (236.0, 229.0, 214.0)
    white = to_paper_white(page)
    assert tuple(white[5, 5]) == (255, 255, 255)
    assert white[20, 50].max() < 40


def test_grey_pages_and_pages_without_paper() -> None:
    """Grey pages work; dark or already white pages are left alone."""
    grey = np.full((100, 100), 228, np.uint8)
    assert int(to_paper_white(grey)[0, 0]) == 255
    dark = np.full((50, 50, 3), 90, np.uint8)
    assert to_paper_white(dark) is dark
    white = np.full((50, 50, 3), 255, np.uint8)
    assert to_paper_white(white) is white


def test_store_whitens_files_in_place(tmp_path: Path) -> None:
    """Page files are corrected with their resolution; line art is skipped.

    Args:
        tmp_path: Temporary directory of the test.
    """
    path = tmp_path / "p.png"
    Image.fromarray(_page((230, 230, 225))).save(path, dpi=(300, 300))
    ImageStore().whiten(path)
    with Image.open(path) as image:
        assert image.getpixel((5, 5)) == (255, 255, 255)
        assert round(image.info["dpi"][0]) == 300
    line = tmp_path / "l.png"
    Image.new("1", (20, 20), 1).save(line)
    before = line.read_bytes()
    assert ImageStore().whiten(line) == line and line.read_bytes() == before
