"""Fake adapters for the release workflow tests."""

from pathlib import Path

from fakes import FakeShell

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.dev_environment import DevEnvironment
from scanbench.infrastructure.git_repo import GitRepo
from scanbench.infrastructure.git_versions import GitVersions
from scanbench.infrastructure.github_cli import GitHubCli
from scanbench.infrastructure.release_installer import ReleaseInstaller

Log = list[str]


class FakeVersions(GitVersions):
    """Versions held in memory."""

    def __init__(self, released: Version | None, line: Version) -> None:
        """Set the initial state.

        Args:
            released: Newest tag on the remote.
            line: Version line of the checkout.
        """
        super().__init__(FakeShell())
        self.released, self.line = released, line
        self.refs: dict[str, Version] = {}

    def released_version(self) -> Version | None:
        """Return the released version.

        Returns:
            The version.
        """
        return self.released

    def version_line(self) -> Version:
        """Return the checked-out version.

        Returns:
            The version.
        """
        return self.line

    def version_on(self, ref: str) -> Version | None:
        """Return the version on a ref.

        Args:
            ref: The ref.

        Returns:
            The version, if known.
        """
        return self.refs.get(ref)


class FakeGit(GitRepo):
    """Records git operations; applying patches sets the version line."""

    def __init__(self, log: Log, versions: FakeVersions, root: Path,
                 remote: bool = True) -> None:
        """Store the shared log.

        Args:
            log: Shared call log.
            versions: Version state changed by ``apply``.
            root: Pretended clone root.
            remote: Whether ``origin`` exists.
        """
        super().__init__(FakeShell(root), versions)
        self.log, self.fake_versions, self.remote = log, versions, remote
        self.next_line: Version | None = None

    def has_remote(self) -> bool:
        """Return whether origin exists.

        Returns:
            The configured flag.
        """
        return self.remote

    def fetch(self) -> None:
        """Record."""
        self.log.append("fetch")

    def switch(self, branch: str, start: str | None = None) -> None:
        """Record.

        Args:
            branch: Branch.
            start: Start point.
        """
        self.log.append(f"switch {branch}")

    def pull(self) -> None:
        """Record."""
        self.log.append("pull")

    def apply(self, patches: list[Path]) -> None:
        """Record and move the version line forward.

        Args:
            patches: Patch files.
        """
        self.log.append(f"apply {len(patches)}")
        if self.next_line is not None:
            self.fake_versions.line = self.next_line

    def push(self, ref: str) -> None:
        """Record.

        Args:
            ref: Ref.
        """
        self.log.append(f"push {ref}")

    def tag(self, version: Version) -> None:
        """Record.

        Args:
            version: Version.
        """
        self.log.append(f"tag {version.tag}")

    def delete_branch(self, branch: str) -> None:
        """Record.

        Args:
            branch: Branch.
        """
        self.log.append(f"delete {branch}")


class FakeGitHub(GitHubCli):
    """Records GitHub operations."""

    def __init__(self, log: Log, fail_checks: bool = False) -> None:
        """Store the shared log.

        Args:
            log: Shared call log.
            fail_checks: Make ``wait_checks`` fail.
        """
        super().__init__(FakeShell(), lambda _s: None)
        self.log, self.fail_checks = log, fail_checks

    def open_pr(self, base: str, head: str, title: str) -> str:
        """Record.

        Args:
            base: Base.
            head: Head.
            title: Title.

        Returns:
            A fake URL.
        """
        self.log.append(f"pr {head}->{base}")
        return f"https://pr/{head}"

    def wait_checks(self, url: str) -> None:
        """Record or fail.

        Args:
            url: URL.

        Raises:
            UpdateError: If configured to fail.
        """
        self.log.append("checks")
        if self.fail_checks:
            raise UpdateError("CI failed")

    def merge(self, url: str) -> None:
        """Record.

        Args:
            url: URL.
        """
        self.log.append("merge")

    def update_branch(self, url: str) -> None:
        """Record.

        Args:
            url: URL.
        """
        self.log.append("update-branch")

    def wait_run(self, ref: str, event: str) -> str:
        """Record.

        Args:
            ref: Ref.
            event: Event.

        Returns:
            A fake URL.
        """
        self.log.append(f"run {ref} {event}")
        return f"https://run/{ref}"

    def dispatch(self, branch: str) -> None:
        """Record.

        Args:
            branch: Branch.
        """
        self.log.append(f"dispatch {branch}")

    def create_repo(self, repo: str, description: str) -> None:
        """Record.

        Args:
            repo: Repository.
            description: Description.
        """
        self.log.append(f"create {repo}")

    def configure_repo(self, repo: str) -> None:
        """Record.

        Args:
            repo: Repository.
        """
        self.log.append("configure")

    def protect(self, repo: str, branch: str) -> None:
        """Record.

        Args:
            repo: Repository.
            branch: Branch.
        """
        self.log.append(f"protect {branch}")


class FakeDev(DevEnvironment):
    """Records preparation and gate runs."""

    def __init__(self, log: Log) -> None:
        """Store the shared log.

        Args:
            log: Shared call log.
        """
        super().__init__(Path("/clone"))
        self.log = log

    def prepare(self) -> None:
        """Record."""
        self.log.append("prepare")

    def gates(self) -> None:
        """Record."""
        self.log.append("gates")


class FakeInstaller(ReleaseInstaller):
    """Remembers the active release."""

    def __init__(self, log: Log, paths: AppPaths, active: Version | None) -> None:
        """Store the state.

        Args:
            log: Shared call log.
            paths: Paths of the installation.
            active: Initially active release.
        """
        super().__init__(paths, FakeShell())
        self.log, self.active = log, active

    def active_version(self) -> Version | None:
        """Return the active release.

        Returns:
            The version.
        """
        return self.active

    def install(self, version: Version) -> None:
        """Record and activate.

        Args:
            version: Release.
        """
        self.log.append(f"install {version.tag}")
        self.active = version
