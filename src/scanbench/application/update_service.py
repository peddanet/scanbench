"""Use case ``scanbench update``: apply all pending patch archives and install."""

import shutil
from collections.abc import Callable
from contextlib import AbstractContextManager

from scanbench.application.hotfix_release import HotfixRelease
from scanbench.application.release_context import ReleaseContext
from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.archive_finder import ArchiveFinder

Chooser = Callable[[list[PatchArchive]], list[PatchArchive]]
"""Selects which pending archives to apply (interactive prompt or all)."""


class UpdateService:
    """Find pending archives, release them one by one, install the newest.

    Versions are applied strictly in ascending order, because every patch is
    based on the release before it. Two updates must not run in parallel;
    the lock enforces that.
    """

    def __init__(self, ctx: ReleaseContext, finder: ArchiveFinder, choose: Chooser,
                 lock: AbstractContextManager[object]) -> None:
        """Store the collaborators.

        Args:
            ctx: Shared release collaborators.
            finder: Finder of archives in the download folder.
            choose: Selection of the archives to apply.
            lock: Lock held for the whole update.
        """
        self._ctx = ctx
        self._finder = finder
        self._choose = choose
        self._lock = lock

    def _released(self) -> Version | None:
        """Check the clone and return the newest released version.

        Returns:
            The newest tag on GitHub, or None.

        Raises:
            UpdateError: If the clone or its remote is missing.
        """
        git = self._ctx.git
        if not git.is_clone():
            raise UpdateError(f"no git clone at {git.root}; set SCANBENCH_CLONE or --clone")
        if not git.has_remote():
            raise UpdateError("the clone has no remote 'origin'; run 'scanbench publish' first")
        self._ctx.progress.step("read release state from GitHub")
        git.fetch()
        released = self._ctx.versions.released_version()
        self._ctx.progress.info(f"released: {released or 'nothing'}; "
                                f"active here: {self._ctx.installer.active_version() or 'none'}")
        return released

    def _install(self, target: Version | None) -> None:
        """Install the target release unless it is already active.

        Args:
            target: Newest released version.
        """
        ctx = self._ctx
        if target is None or ctx.installer.active_version() == target:
            return
        ctx.progress.step(f"install {target.tag} into a new venv and switch to it")
        ctx.installer.install(target)
        ctx.progress.info("running scanbench windows switch at their next idle moment")

    def _store(self, archives: list[PatchArchive]) -> None:
        """Move archives out of the download folder into the archive store.

        Args:
            archives: Applied or no longer needed archives.
        """
        store = self._ctx.paths.release.archive_store
        store.mkdir(parents=True, exist_ok=True)
        for archive in archives:
            if archive.path.exists():
                shutil.move(str(archive.path), str(store / archive.path.name))
                self._ctx.progress.info(f"archived {archive.path.name} -> {store}")

    def _list(self, pending: list[PatchArchive]) -> None:
        """Show the pending archives in the order they will be applied.

        Args:
            pending: Pending archives, ascending.
        """
        progress = self._ctx.progress
        # the summary line is read by the progress bar of the update dialog
        progress.info("pending: " + (", ".join(str(a.version) for a in pending) or "none"))
        if not pending:
            return
        progress.info("applied in this order:")
        for number, archive in enumerate(pending, 1):
            base = self._finder.base(archive)
            built_on = f"  (built on {base})" if base is not None else ""
            progress.info(f"  {number}. {archive.version}  {archive.path.name}{built_on}")

    def _check_chain(self, released: Version | None, chosen: list[PatchArchive]) -> None:
        """Make sure every archive fits the version before it, before anything changes.

        An archive that names its base (``BASE`` file) must follow exactly that
        version; archives without a base are not checked.

        Args:
            released: Newest released version, or None.
            chosen: Archives to apply, ascending.

        Raises:
            UpdateError: If an archive is built on a version that is not there.
        """
        current = released
        for archive in chosen:
            base = self._finder.base(archive)
            if base is not None and base != current:
                if current is None or base > current:
                    raise UpdateError(
                        f"{archive.version} is built on {base}, which is neither released nor "
                        f"in the download folder; download scanbench-{base}-patch-*.tar.gz "
                        f"and run the update again")
                raise UpdateError(
                    f"{archive.version} is built on {base}, but {current} comes first; "
                    f"keep only the archives of one delivery chain in the download folder")
            current = archive.version

    def run(self) -> int:
        """Execute the update and print the summary, also on failure.

        Returns:
            0 on success, 1 on failure.
        """
        progress = self._ctx.progress
        progress.header("scanbench update")
        try:
            with self._lock:
                released = self._released()
                pending = self._finder.pending(released)
                self._store(self._finder.obsolete(released, pending))
                self._list(pending)
                chosen = self._choose(pending) if pending else []
                self._check_chain(released, chosen)
                for archive in chosen:
                    HotfixRelease(self._ctx).run(archive)
                newest = chosen[-1].version if chosen else released
                self._install(newest)
                self._store(chosen)
                self._store(self._finder.obsolete(newest, []))
        except UpdateError as exc:
            progress.summary(f"FAILED: {exc}")
            return 1
        progress.summary(f"DONE: scanbench {newest or 'not released yet'} is current")
        return 0
