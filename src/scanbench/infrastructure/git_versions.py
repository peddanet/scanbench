"""Versions known to git: release tags on the remote, version lines on refs."""

import re

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.shell import Shell

_VERSION_LINE = re.compile(r'^__version__ = "(\d+\.\d+\.\d+)"$', re.MULTILINE)


class GitVersions:
    """Read release tags and ``__version__`` lines of the clone."""

    def __init__(self, shell: Shell) -> None:
        """Store the shell that runs in the clone.

        Args:
            shell: Shell whose working directory is the clone.
        """
        self._shell = shell

    def released_version(self) -> Version | None:
        """Return the newest release tag on the remote.

        Returns:
            The newest ``vX.Y.Z`` on ``origin``, or None.
        """
        out = self._shell.read("git", "ls-remote", "--tags", "--refs", "origin", "v*").stdout
        versions = []
        for line in out.splitlines():
            try:
                versions.append(Version.parse(line.rsplit("/", 1)[-1]))
            except ValueError:
                continue
        return max(versions, default=None)

    def version_line(self) -> Version:
        """Return the version of the checked-out ``__init__.py``.

        Returns:
            The version.

        Raises:
            UpdateError: If the version line is missing.
        """
        text = (self._shell.cwd / "src" / "scanbench" / "__init__.py").read_text(encoding="utf-8")
        match = _VERSION_LINE.search(text)
        if match is None:
            raise UpdateError("no version line in src/scanbench/__init__.py")
        return Version.parse(match[1])

    def version_on(self, ref: str) -> Version | None:
        """Return the version line of ``__init__.py`` on another ref.

        Args:
            ref: Branch, tag or remote ref, e.g. ``origin/main``.

        Returns:
            The version, or None if the ref or the line does not exist.
        """
        shown = self._shell.run("git", "show", f"{ref}:src/scanbench/__init__.py", check=False)
        match = _VERSION_LINE.search(shown.stdout) if shown.ok else None
        return Version.parse(match[1]) if match else None
