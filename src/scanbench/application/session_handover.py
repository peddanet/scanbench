"""Hand the open work over to the next release when the program switches.

Switching to a newly installed release starts a new process. Without a
handover the raw scans of the old process are deleted with its work
directory, and the new window starts empty. Before the switch the old
process writes the state and copies the raw scans into a handover
directory; the new process takes them over once and deletes the directory.
"""

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from scanbench.application.document_session import Page
from scanbench.application.photo_session import PhotoScan
from scanbench.domain.crop_region import CropRegion

STATE_FILE = "handover.json"
"""Name of the state file in the handover directory."""


@dataclass
class Handover:
    """What the window was doing.

    Attributes:
        device: Selected SANE device, or None.
        tab: Index of the open tab.
        photo: Photo scan waiting for confirmation, or None.
        pages: Pages of the document being scanned.
    """

    device: str | None = None
    tab: int = 0
    photo: PhotoScan | None = None
    pages: list[Page] = field(default_factory=list)


class SessionHandover:
    """Write and take over a handover directory (Memento)."""

    def __init__(self, directory: Path) -> None:
        """Store the location.

        Args:
            directory: Handover directory, e.g. ``$SCANBENCH_HOME/sessions/handover``.
        """
        self.directory = directory

    def clear(self) -> None:
        """Delete the handover directory."""
        shutil.rmtree(self.directory, ignore_errors=True)

    def _copy(self, source: Path, name: str) -> str:
        """Copy a raw scan into the handover directory.

        Args:
            source: Raw scan.
            name: File name in the handover directory.

        Returns:
            The file name.
        """
        shutil.copy2(source, self.directory / name)
        return name

    def save(self, handover: Handover) -> None:
        """Write the state and copy the raw scans.

        Args:
            handover: State of the window.
        """
        self.clear()
        self.directory.mkdir(parents=True)
        state: dict[str, Any] = {"device": handover.device, "tab": handover.tab,
                                 "photo": None, "pages": []}
        photo = handover.photo
        if photo is not None:
            state["photo"] = {"file": self._copy(photo.path, "photo" + photo.path.suffix),
                              "dpi": photo.dpi, "preview": photo.preview,
                              "regions": [asdict(r) for r in photo.regions]}
        for number, page in enumerate(handover.pages, 1):
            state["pages"].append({
                "file": self._copy(page.path, f"page-{number:03d}{page.path.suffix}"),
                "dpi": page.dpi, "quarter_turns": page.quarter_turns, "batch": page.batch})
        (self.directory / STATE_FILE).write_text(json.dumps(state, indent=1) + "\n",
                                                 encoding="utf-8")

    def take(self, work_dir: Path) -> Handover | None:
        """Move a waiting handover into a work directory and delete it.

        Args:
            work_dir: Work directory of the new session; ``photos`` and
                ``documents`` below it receive the raw scans.

        Returns:
            The state, or None if there is none or it cannot be read.
        """
        state_file = self.directory / STATE_FILE
        if not state_file.is_file():
            return None
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            result = Handover(state["device"], int(state["tab"]))
            photo = state["photo"]
            if photo is not None:
                path = Path(shutil.copy2(self.directory / photo["file"],
                                         work_dir / "photos" / photo["file"]))
                result.photo = PhotoScan(path, int(photo["dpi"]),
                                         [CropRegion(**r) for r in photo["regions"]],
                                         bool(photo["preview"]))
            for page in state["pages"]:
                path = Path(shutil.copy2(self.directory / page["file"],
                                         work_dir / "documents" / page["file"]))
                result.pages.append(Page(path, int(page["dpi"]), int(page["quarter_turns"]),
                                         int(page["batch"])))
        except (OSError, ValueError, KeyError, TypeError):
            result = None
        self.clear()
        return result
