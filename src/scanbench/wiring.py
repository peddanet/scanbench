"""Composition of the release workflows from their real adapters."""

import functools
import time
from collections.abc import Callable
from pathlib import Path

from scanbench.application.progress import Progress
from scanbench.application.release_context import ReleaseContext
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.dev_environment import DevEnvironment
from scanbench.infrastructure.git_repo import GitRepo
from scanbench.infrastructure.git_versions import GitVersions
from scanbench.infrastructure.github_cli import GitHubCli
from scanbench.infrastructure.release_installer import ReleaseInstaller
from scanbench.infrastructure.shell import Shell

flush_print = functools.partial(print, flush=True)
"""Print that flushes at once, so the GUI dialog shows progress immediately."""


def release_context(paths: AppPaths, clone: Path,
                    out: Callable[[str], object] = flush_print) -> ReleaseContext:
    """Create the release collaborators for a clone.

    Args:
        paths: Resolver of the installation directories.
        clone: Maintainer's git clone.
        out: Function that prints one line.

    Returns:
        The wired context.
    """
    shell = Shell(clone)
    versions = GitVersions(shell)
    return ReleaseContext(paths=paths, git=GitRepo(shell, versions), versions=versions,
                          github=GitHubCli(shell, time.sleep), dev=DevEnvironment(clone),
                          installer=ReleaseInstaller(paths, shell), progress=Progress(out))
