"""Bring one delivered patch archive through git-flow to a tagged release."""

import tarfile
import tempfile
from pathlib import Path

from scanbench.application.release_context import ReleaseContext
from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.archive_finder import ArchiveFinder


class HotfixRelease:
    """Apply one archive on the hotfix path, as in mediatools.

    ``hotfix/X`` from ``main`` -> ``git am`` -> gates -> pull request into
    ``main`` (CI 1/3) -> merge -> tag ``vX`` (CI 2/3) -> ``merge/hotfix-X`` ->
    pull request into ``develop`` (CI 3/3) -> merge. Every step checks the
    current state first, so a repeated run continues where a failed one
    stopped.
    """

    def __init__(self, ctx: ReleaseContext) -> None:
        """Store the collaborators.

        Args:
            ctx: Shared release collaborators.
        """
        self._ctx = ctx

    @staticmethod
    def _patches(archive: PatchArchive, target: Path) -> list[Path]:
        """Unpack the archive and return its patch files in order.

        Args:
            archive: The delivered archive.
            target: Empty directory to unpack into.

        Returns:
            Sorted ``*.patch`` files.

        Raises:
            UpdateError: If the archive contains no patch.
        """
        with tarfile.open(archive.path, "r:gz") as tar:
            tar.extractall(target, filter="data")
        patches = sorted(target.rglob("*.patch"))
        if not patches:
            raise UpdateError(f"{archive.path.name} contains no patch")
        return patches

    def _apply(self, archive: PatchArchive) -> None:
        """Create the hotfix branch and apply the patches unless already done.

        Args:
            archive: The delivered archive.

        Raises:
            UpdateError: If the result does not carry the archive's version.
        """
        ctx, version = self._ctx, archive.version
        ctx.progress.step(f"{version}: branch hotfix/{version} from main, apply patches")
        ctx.git.switch("main")
        ctx.git.pull()
        self._drop_stale_branch(archive)
        ctx.git.switch(f"hotfix/{version}", start="main")
        if ctx.versions.version_line() != version:
            with tempfile.TemporaryDirectory() as tmp:
                ctx.git.apply(self._patches(archive, Path(tmp)))
            ctx.git.refs.set_config(self._key(version), ArchiveFinder.digest(archive))
        if ctx.versions.version_line() != version:
            raise UpdateError(f"after applying, the version line is "
                              f"{ctx.versions.version_line()}, not {version}")

    @staticmethod
    def _key(version: Version) -> str:
        """Return the git configuration key that records the applied delivery.

        Args:
            version: Release being built.

        Returns:
            E.g. ``scanbench.hotfix-0-2-3``.
        """
        return f"scanbench.hotfix-{str(version).replace('.', '-')}"

    def _drop_stale_branch(self, archive: PatchArchive) -> None:
        """Discard a local hotfix branch that was built from another delivery.

        A failed run leaves ``hotfix/X``; a corrected delivery of the same
        version must not reuse its commits. A branch already pushed is not
        discarded silently.

        Args:
            archive: The delivery to apply.

        Raises:
            UpdateError: If the stale branch is already on GitHub.
        """
        ctx, branch = self._ctx, f"hotfix/{archive.version}"
        refs = ctx.git.refs
        if not refs.has_branch(branch) or \
                refs.get_config(self._key(archive.version)) == ArchiveFinder.digest(archive):
            return
        if refs.on_remote(branch):
            raise UpdateError(f"{branch} on GitHub was built from another delivery of "
                              f"{archive.version}; close its pull request and delete the "
                              f"branch on GitHub and locally, then run the update again")
        ctx.git.delete_branch(branch)
        ctx.progress.info(f"discarded local {branch}: built from another delivery")

    def _into_main(self, version: Version) -> None:
        """Run the gates, push, and merge the hotfix into ``main``.

        Args:
            version: Release being built.
        """
        ctx = self._ctx
        ctx.progress.step(f"{version}: quality gates (local)")
        ctx.dev.prepare()
        ctx.dev.gates()
        ctx.progress.step(f"{version}: pull request into main")
        ctx.git.push(f"hotfix/{version}")
        url = ctx.github.open_pr("main", f"hotfix/{version}", f"Release {version}")
        ctx.progress.ci("CI 1/3", "pull request into main", url)
        ctx.github.wait_checks(url)
        ctx.github.merge(url)

    def _tag(self, version: Version) -> None:
        """Tag the release on ``main`` and wait for the tag run.

        Args:
            version: Release being built.
        """
        ctx = self._ctx
        ctx.progress.step(f"{version}: tag {version.tag} on main")
        ctx.git.switch("main")
        ctx.git.pull()
        ctx.git.tag(version)
        ctx.git.push(version.tag)
        ctx.progress.ci("CI 2/3", f"tag {version.tag}: matrix + release check",
                        ctx.github.wait_run(version.tag, "push"))

    def _into_develop(self, version: Version) -> None:
        """Merge the released ``main`` back into ``develop``.

        Args:
            version: Release being built.
        """
        ctx, branch = self._ctx, f"merge/hotfix-{version}"
        ctx.progress.step(f"{version}: back-merge into develop")
        ctx.git.switch(branch, start="main")
        ctx.git.push(branch)
        url = ctx.github.open_pr("develop", branch, f"Merge release {version} into develop")
        ctx.github.update_branch(url)
        ctx.progress.ci("CI 3/3", "back-merge into develop", url)
        ctx.github.wait_checks(url)
        ctx.github.merge(url)
        ctx.git.switch("develop")
        ctx.git.pull()
        for local in (f"hotfix/{version}", branch):
            ctx.git.delete_branch(local)

    def run(self, archive: PatchArchive) -> None:
        """Bring the archive to a tagged, back-merged release.

        Args:
            archive: The delivered archive.
        """
        version = archive.version
        main = self._ctx.versions.version_on("origin/main")
        if main is None or main < version:
            self._apply(archive)
            self._into_main(version)
        else:
            self._ctx.progress.step(f"{version}: already merged into main, continuing")
        self._tag(version)
        develop = self._ctx.versions.version_on("origin/develop")
        if develop is None or develop < version:
            self._into_develop(version)
