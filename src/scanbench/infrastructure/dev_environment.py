"""Development venv of the clone and the quality gates run inside it."""

import os
from pathlib import Path

from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell


class DevEnvironment:
    """Keep ``<clone>/.venv`` current and run ``tools/check.sh`` in it.

    The installed release has no gate tools; the gates always run in the
    development venv of the clone, exactly as the pre-push hook would.
    """

    def __init__(self, clone: Path, shell_factory: type[Shell] = Shell) -> None:
        """Store the clone.

        Args:
            clone: Root of the maintainer's clone.
            shell_factory: Class used to create shells (replaceable in tests).
        """
        self._clone = clone
        self._venv = clone / ".venv"
        self._shell_factory = shell_factory

    def environment(self) -> dict[str, str]:
        """Return our environment with the development venv activated.

        Returns:
            Environment variables for the gate run.
        """
        env = dict(os.environ)
        env["VIRTUAL_ENV"] = str(self._venv)
        env["PATH"] = f"{self._venv / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        return env

    def prepare(self) -> None:
        """Create the venv if missing and install the clone with its dev tools."""
        plain = self._shell_factory(self._clone)
        if not (self._venv / "bin" / "python").exists():
            plain.run("python3", "-m", "venv", str(self._venv))
        pip = str(self._venv / "bin" / "pip")
        plain.run(pip, "install", "--quiet", "-e", ".[dev]")

    def gates(self) -> None:
        """Run all six gates with live, staged output.

        Raises:
            UpdateError: If a gate fails.
        """
        shell = self._shell_factory(self._clone, env=self.environment())
        if shell.live(str(self._clone / "tools" / "check.sh")) != 0:
            raise UpdateError("quality gates failed; see the stage output above")
