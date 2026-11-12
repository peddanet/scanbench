"""Queries on branches and the git configuration of the maintainer's clone."""

from scanbench.infrastructure.shell import Shell


class GitRefs:
    """Branch existence and stored values of the clone (part of ``GitRepo``)."""

    def __init__(self, shell: Shell) -> None:
        """Store the command runner.

        Args:
            shell: Runner whose working directory is the clone.
        """
        self._shell = shell

    def has_branch(self, branch: str) -> bool:
        """Whether a local branch exists.

        Args:
            branch: Branch name.

        Returns:
            True if ``refs/heads/BRANCH`` exists.
        """
        return self._shell.run("git", "rev-parse", "--verify", "-q",
                               f"refs/heads/{branch}", check=False).ok

    def on_remote(self, branch: str) -> bool:
        """Whether a branch exists on ``origin`` (as of the last fetch).

        Args:
            branch: Branch name.

        Returns:
            True if ``refs/remotes/origin/BRANCH`` exists.
        """
        return self._shell.run("git", "rev-parse", "--verify", "-q",
                               f"refs/remotes/origin/{branch}", check=False).ok

    def get_config(self, key: str) -> str:
        """Read a value from the clone's git configuration.

        Args:
            key: E.g. ``scanbench.hotfix-0-2-3``.

        Returns:
            The value, or an empty string if it is not set.
        """
        result = self._shell.run("git", "config", "--get", key, check=False)
        return result.stdout.strip() if result.ok else ""

    def set_config(self, key: str, value: str) -> None:
        """Store a value in the clone's git configuration.

        Args:
            key: E.g. ``scanbench.hotfix-0-2-3``.
            value: Value to store.
        """
        self._shell.run("git", "config", key, value)
