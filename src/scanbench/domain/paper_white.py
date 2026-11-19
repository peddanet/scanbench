"""Make the paper of a scanned document pure white.

The paper of a scan is never pure white: the lid, the lamp and the paper
itself give a light grey or cream tone. Printed, that tone becomes a faint
area that ends at the printer's margin and looks like a frame. Scaling every
channel so that the paper tone becomes 255 removes the tint and the frame.
"""

import numpy as np
from numpy.typing import NDArray

PERCENTILE = 90.0
"""Brightness percentile taken as paper white; text and pictures cover less than
the darkest 90 % of a typical page only rarely, so this hits the paper."""

MIN_PAPER = 140
"""A page whose paper estimate is darker than this is left alone (dark photo,
black page): stretching it would only brighten the picture."""

KNEE = 248
"""Values at or above this after scaling become pure white, removing the
paper's grain without touching light text."""


def paper_tone(pixels: NDArray[np.uint8]) -> NDArray[np.float64]:
    """Estimate the paper colour of a page.

    Args:
        pixels: Grey (H x W) or RGB (H x W x 3) page.

    Returns:
        One value per channel.
    """
    flat = pixels.reshape(-1, 1 if pixels.ndim == 2 else pixels.shape[2])
    sample = flat[:: max(1, len(flat) // 200_000)]          # enough for a percentile
    return np.percentile(sample, PERCENTILE, axis=0)


def to_paper_white(pixels: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Return the page with its paper tone mapped to pure white.

    Args:
        pixels: Grey or RGB page.

    Returns:
        The corrected page; unchanged if the paper is too dark to be paper.
    """
    tone = paper_tone(pixels)
    if float(tone.min()) < MIN_PAPER or float(tone.min()) >= 254:
        return pixels
    scaled = pixels.astype(np.float32) * (255.0 / tone.astype(np.float32))
    scaled[scaled >= KNEE] = 255.0
    return np.clip(scaled, 0, 255).astype(np.uint8)
