"""Git operations on the maintainer's clone."""

from pathlib import Path

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.git_refs import GitRefs
from scanbench.infrastructure.git_versions import GitVersions
from scanbench.infrastructure.shell import Shell


class GitRepo:
    """Adapter for the git commands of the release workflow."""

    def __init__(self, shell: Shell, versions: GitVersions) -> None:
        """Store the shell that runs in the clone.

        Args:
            shell: Shell whose working directory is the clone.
            versions: Reader of versions, used to guard the release tag.
        """
        self._shell = shell
        self._versions = versions
        self.refs = GitRefs(shell)

    @property
    def root(self) -> Path:
        """Root directory of the clone.

        Returns:
            The clone directory.
        """
        return self._shell.cwd

    def is_clone(self) -> bool:
        """Whether the root is a git working tree.

        Returns:
            True if ``<root>/.git`` exists.
        """
        return (self.root / ".git").exists()

    def has_remote(self) -> bool:
        """Whether the remote ``origin`` exists.

        Returns:
            True if ``origin`` is configured.
        """
        return "origin" in self._shell.run("git", "remote").stdout.split()

    def fetch(self) -> None:
        """Fetch branches and tags from ``origin``."""
        self._shell.read("git", "fetch", "origin", "--tags", "--prune")

    def switch(self, branch: str, start: str | None = None) -> None:
        """Switch to a branch, creating it from ``start`` if it does not exist.

        Args:
            branch: Branch name.
            start: Start point for a new branch; None requires the branch to exist.
        """
        if self.refs.has_branch(branch) or start is None:
            self._shell.run("git", "switch", branch)
        else:
            self._shell.run("git", "switch", "-c", branch, start)

    def pull(self) -> None:
        """Fast-forward the current branch to its upstream."""
        self._shell.read("git", "pull", "--ff-only")

    def apply(self, patches: list[Path]) -> None:
        """Apply a patch series as commits; undo everything on failure.

        Args:
            patches: Patch files in order.

        Raises:
            UpdateError: If a patch does not apply.
        """
        result = self._shell.run("git", "am", *map(str, patches), check=False)
        if not result.ok:
            self._shell.run("git", "am", "--abort", check=False)
            raise UpdateError(f"patches do not apply: {result.stdout.strip()[-300:]}")

    def push(self, ref: str) -> None:
        """Push a branch or tag to ``origin``.

        The gates ran right before on the same commit, so the pre-push hook is
        skipped; the CI enforces the gates again.

        Args:
            ref: Branch or tag name.
        """
        self._shell.read("git", "push", "--no-verify", "-u", "origin", ref)

    def tag(self, version: Version) -> None:
        """Create the annotated release tag if the version line matches.

        Args:
            version: Release to tag.

        Raises:
            UpdateError: If the checked-out version differs.
        """
        if self._versions.version_line() != version:
            raise UpdateError(f"version line is {self._versions.version_line()}, not {version}")
        exists = self._shell.run("git", "rev-parse", "--verify", "-q",
                                 f"refs/tags/{version.tag}", check=False).ok
        if not exists:
            self._shell.run("git", "tag", "-a", version.tag, "-m", f"scanbench {version}")

    def delete_branch(self, branch: str) -> None:
        """Delete a local branch if it exists (after its pull request was merged).

        Args:
            branch: Branch name.
        """
        self._shell.run("git", "branch", "-D", branch, check=False)
