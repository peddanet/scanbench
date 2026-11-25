"""One-time move of files from the single-root layout of older releases.

Releases up to 0.3.x could keep configuration, logs, cache, sessions and the
update lock below one folder, ``$SCANBENCH_HOME`` (e.g.
``~/scripts/scanbench.d``). A launcher entry written by those releases also set
``SCANBENCH_HOME`` to the release folder ``~/.local/share/scanbench``, so a
program started from the menu kept ``config/`` and ``logs/`` there.

This module moves such files (also the privacy lists of a developer) into
the XDG layout of ``AppPaths``:

* nothing is overwritten: an entry whose target exists stays where it is and
  is reported;
* every move is reported and appended to ``<log dir>/layout-move.log``;
* folders emptied by the move are removed;
* installed releases (``venvs/``) are never moved - a venv holds absolute
  paths and a running program would lose its own files; ``install.sh``
  installs them again;
* the cache is not moved: it is re-creatable and is only reported.
"""

import shutil
import time
from collections.abc import Mapping
from pathlib import Path

from scanbench.infrastructure.app_paths import AppPaths

OLD_DEFAULT_ROOT = Path("scripts") / "scanbench.d"
"""Single-root folder of older installations, relative to the home directory."""

REPORT_FILE = "layout-move.log"
"""File in the log directory that keeps the report of every move."""


class LegacyLayout:
    """Find and move files of the old single-root layout.

    Attributes:
        paths: Target directories (XDG layout).
        environ: Environment variables, read for ``SCANBENCH_HOME``.
    """

    def __init__(self, paths: AppPaths, environ: Mapping[str, str]) -> None:
        """Store target directories and environment.

        Args:
            paths: Target directories.
            environ: Environment variables, usually ``os.environ``.
        """
        self.paths = paths
        self.environ = environ
        self._report: list[str] = []

    def roots(self) -> list[Path]:
        """Return the existing single-root folders that may hold old files.

        Returns:
            ``$SCANBENCH_HOME`` if set, ``~/scripts/scanbench.d`` and the
            release folder, each once and only if it exists.
        """
        candidates = [self.paths.home / OLD_DEFAULT_ROOT, self.paths.release_dir]
        value = self.environ.get("SCANBENCH_HOME", "")
        if value:
            candidates.insert(0, Path(value).expanduser())
        found: list[Path] = []
        for root in candidates:
            if root.is_dir() and all(not _same(root, other) for other in found):
                found.append(root)
        return found

    def _targets(self, root: Path) -> list[tuple[Path, Path]]:
        """Return the old entries of one root and where they belong.

        Args:
            root: A single-root folder.

        Returns:
            ``(source, target)`` pairs whose source exists and differs from
            the target.
        """
        pairs = [(root / "config", self.paths.config_dir),
                 (root / "privacy", self.paths.config_dir / "privacy"),
                 (root / "logs", self.paths.log_dir),
                 (root / "sessions", self.paths.sessions_dir),
                 (root / "releases", self.paths.release.archive_store),
                 (root / "update.lock", self.paths.release.lock_file)]
        return [(source, target) for source, target in pairs
                if (source.exists() or source.is_symlink()) and not _same(source, target)]

    def _move(self, source: Path, target: Path) -> None:
        """Move one entry without overwriting anything.

        Args:
            source: Old file or folder.
            target: New place.
        """
        if not target.exists() and not target.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            self._report.append(f"moved: {source} -> {target}")
        elif source.is_dir() and not source.is_symlink() and target.is_dir():
            for child in sorted(source.iterdir()):
                self._move(child, target / child.name)
            _remove_if_empty(source)
        else:
            self._report.append(f"kept, target exists: {source} (target {target})")

    def _notes(self, root: Path) -> None:
        """Report what is deliberately not moved from one root.

        Args:
            root: A single-root folder.
        """
        cache = root / "cache"
        if cache.is_dir() and not _same(cache, self.paths.cache_dir):
            self._report.append(f"not moved, re-creatable (may be deleted): {cache}")
        venvs = root / "venvs"
        if venvs.is_dir() and not _same(root, self.paths.release_dir):
            self._report.append(f"not moved: installed releases in {venvs} - install again "
                                f"with install.sh, then delete {root}")

    def run(self) -> list[str]:
        """Move all old files once.

        Returns:
            One line per move, kept entry, note or error; empty if there was
            nothing to do.
        """
        self._report = []
        if self.environ.get("SCANBENCH_HOME"):
            self._report.append("SCANBENCH_HOME is no longer used; scanbench keeps its "
                                "files in the XDG folders (user guide, section 3)")
        for root in self.roots():
            for source, target in self._targets(root):
                try:
                    self._move(source, target)
                except OSError as error:
                    self._report.append(f"could not move {source}: {error}")
            self._notes(root)
            if not _same(root, self.paths.release_dir):
                _remove_if_empty(root)
        self._write_report()
        return list(self._report)

    def _write_report(self) -> None:
        """Append the report of a run that moved or kept something."""
        if not any(line.startswith(("moved", "kept", "could not")) for line in self._report):
            return
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.paths.log_dir.mkdir(parents=True, exist_ok=True)
            with (self.paths.log_dir / REPORT_FILE).open("a", encoding="utf-8") as handle:
                handle.writelines(f"{stamp} {line}\n" for line in self._report)
        except OSError as error:
            self._report.append(f"could not write {REPORT_FILE}: {error}")


def _same(first: Path, second: Path) -> bool:
    """Tell whether two paths name the same place.

    Args:
        first: A path.
        second: Another path.

    Returns:
        True if both resolve to the same absolute path.
    """
    return first.resolve(strict=False) == second.resolve(strict=False)


def _remove_if_empty(folder: Path) -> None:
    """Remove a folder if it is empty; never raise.

    Args:
        folder: Folder to remove.
    """
    try:
        folder.rmdir()
    except OSError:
        pass
