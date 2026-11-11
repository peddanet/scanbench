"""Use case ``scanbench publish``: first publication of the clone on GitHub."""

from scanbench.application.release_context import ReleaseContext
from scanbench.domain.update_error import UpdateError

DESCRIPTION = "Document and photo-album scanning for Linux, built on SANE"
"""Repository description shown on GitHub."""


class FirstPublication:
    """Publish a local clone: repository, branches, settings, protection, tag.

    Runs once, after the first patch series was applied by hand. Every step
    checks the current state, so a repeated run continues after a failure.
    """

    def __init__(self, ctx: ReleaseContext, repo: str) -> None:
        """Store the collaborators and the repository name.

        Args:
            ctx: Shared release collaborators.
            repo: ``OWNER/NAME`` on GitHub.
        """
        self._ctx = ctx
        self._repo = repo

    def _create(self) -> None:
        """Run the gates, create the repository and push both branches.

        Raises:
            UpdateError: If the clone does not exist.
        """
        ctx = self._ctx
        if not ctx.git.is_clone():
            raise UpdateError(f"no git clone at {ctx.git.root}; set SCANBENCH_CLONE or --clone")
        ctx.progress.step("quality gates (local)")
        ctx.dev.prepare()
        ctx.dev.gates()
        ctx.progress.step(f"create github.com/{self._repo}, push main and develop")
        if not ctx.git.has_remote():
            ctx.github.create_repo(self._repo, DESCRIPTION)
        ctx.git.switch("main")
        ctx.git.push("main")
        ctx.git.switch("develop", start="main")
        ctx.git.push("develop")

    def _protect(self) -> None:
        """Configure merging, run the CI once, protect both branches."""
        ctx = self._ctx
        ctx.progress.step("merge commits only, default branch main")
        ctx.github.configure_repo(self._repo)
        ctx.progress.step("first CI run on develop (registers the check 'gates')")
        ctx.github.dispatch("develop")
        url = ctx.github.wait_run("develop", "workflow_dispatch")
        ctx.progress.ci("CI", "manual run on develop", url)
        ctx.progress.step("branch protection for main and develop")
        for branch in ("develop", "main"):
            ctx.github.protect(self._repo, branch)

    def _release(self) -> str:
        """Tag the version on ``main``, wait for the tag run, install it.

        Returns:
            The released version.
        """
        ctx = self._ctx
        ctx.git.switch("main")
        version = ctx.versions.version_line()
        ctx.progress.step(f"tag {version.tag} on main")
        ctx.git.tag(version)
        ctx.git.push(version.tag)
        ctx.progress.ci("CI", f"tag {version.tag}: matrix + release check",
                        ctx.github.wait_run(version.tag, "push"))
        ctx.progress.step(f"install {version.tag}")
        if ctx.installer.active_version() != version:
            ctx.installer.install(version)
        return str(version)

    def run(self) -> int:
        """Execute the publication and print the summary, also on failure.

        Returns:
            0 on success, 1 on failure.
        """
        progress = self._ctx.progress
        progress.header(f"scanbench publish -> github.com/{self._repo}")
        try:
            self._create()
            self._protect()
            version = self._release()
        except UpdateError as exc:
            progress.summary(f"FAILED: {exc}")
            return 1
        progress.summary(f"DONE: scanbench {version} published and installed")
        return 0
