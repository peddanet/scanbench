"""Collaborators shared by the release workflows."""

from dataclasses import dataclass

from scanbench.application.progress import Progress
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.dev_environment import DevEnvironment
from scanbench.infrastructure.git_repo import GitRepo
from scanbench.infrastructure.git_versions import GitVersions
from scanbench.infrastructure.github_cli import GitHubCli
from scanbench.infrastructure.release_installer import ReleaseInstaller


@dataclass(frozen=True)
class ReleaseContext:
    """Everything a release workflow needs, wired by the composition root.

    Attributes:
        paths: Resolver of the application directories.
        git: Git adapter on the clone.
        versions: Reader of release tags and version lines.
        github: GitHub CLI adapter.
        dev: Development venv and gates of the clone.
        installer: Installer of release tags.
        progress: Numbered output and CI summary.
    """

    paths: AppPaths
    git: GitRepo
    versions: GitVersions
    github: GitHubCli
    dev: DevEnvironment
    installer: ReleaseInstaller
    progress: Progress
