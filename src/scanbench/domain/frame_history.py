"""Undo and redo for the frames of one scan."""

from collections.abc import Sequence

from scanbench.domain.crop_region import CropRegion

State = tuple[CropRegion, ...]
"""All frames of a scan at one moment (immutable)."""


class FrameHistory:
    """Snapshots of the frame list (Memento): every edit can be undone and redone.

    Frames are immutable value objects, so a snapshot is just the tuple of
    frames; no copying is needed.
    """

    def __init__(self, limit: int = 200) -> None:
        """Start with an empty history.

        Args:
            limit: Maximum number of undo steps kept.
        """
        self._limit = limit
        self._undo: list[State] = []
        self._redo: list[State] = []
        self.current: State = ()

    def reset(self, regions: Sequence[CropRegion]) -> None:
        """Forget all steps and start from these frames.

        Args:
            regions: Frames of a newly shown scan.
        """
        self._undo.clear()
        self._redo.clear()
        self.current = tuple(regions)

    def record(self, regions: Sequence[CropRegion]) -> None:
        """Store an edit; the redo steps become invalid.

        Args:
            regions: Frames after the edit.
        """
        state = tuple(regions)
        if state == self.current:
            return
        self._undo.append(self.current)
        del self._undo[:-self._limit]
        self._redo.clear()
        self.current = state

    def undo(self) -> State | None:
        """Go one step back.

        Returns:
            The previous frames, or None if there is nothing to undo.
        """
        if not self._undo:
            return None
        self._redo.append(self.current)
        self.current = self._undo.pop()
        return self.current

    def redo(self) -> State | None:
        """Go one step forward again.

        Returns:
            The frames after the undone edit, or None.
        """
        if not self._redo:
            return None
        self._undo.append(self.current)
        self.current = self._redo.pop()
        return self.current

    def can_undo(self) -> bool:
        """Whether an undo step exists.

        Returns:
            True if undo is possible.
        """
        return bool(self._undo)

    def can_redo(self) -> bool:
        """Whether a redo step exists.

        Returns:
            True if redo is possible.
        """
        return bool(self._redo)
