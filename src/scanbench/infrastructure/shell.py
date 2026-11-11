"""Run external programs with argument lists, never through a shell."""

import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from scanbench.domain.command_result import CommandResult
from scanbench.domain.update_error import UpdateError


class Shell:
    """Execute programs in a working directory.

    Programs are looked up with ``shutil.which`` and called with argument
    lists, so no shell interprets the arguments. Reading calls to remote
    services can be retried, because short network losses happen.
    """

    def __init__(self, cwd: Path, which: Callable[[str], str | None] = shutil.which,
                 sleep: Callable[[float], None] = time.sleep,
                 env: dict[str, str] | None = None) -> None:
        """Store the working directory and the injectable helpers.

        Args:
            cwd: Working directory of every command.
            which: Program lookup.
            sleep: Pause function used between retries.
            env: Environment of the commands; None inherits ours.
        """
        self.cwd = cwd
        self._which = which
        self._sleep = sleep
        self._env = env

    def _argv(self, argv: tuple[str, ...]) -> list[str]:
        """Replace the program name by its absolute path.

        Args:
            argv: Program and arguments.

        Returns:
            The argument list.

        Raises:
            UpdateError: If the program is not on PATH.
        """
        exe = self._which(argv[0])
        if exe is None:
            raise UpdateError(f"program '{argv[0]}' not found on PATH")
        return [exe, *argv[1:]]

    def run(self, *argv: str, check: bool = True, stdin: str | None = None) -> CommandResult:
        """Run a command and capture its output.

        Args:
            *argv: Program and arguments.
            check: Raise if the command fails.
            stdin: Text passed to the standard input of the command.

        Returns:
            The result.

        Raises:
            UpdateError: If the command cannot start, or if ``check`` is set and
                it fails.
        """
        try:
            done = subprocess.run(self._argv(argv), cwd=self.cwd, capture_output=True,
                                  text=True, input=stdin, env=self._env, check=False)
        except OSError as exc:
            raise UpdateError(f"'{argv[0]}' could not start in {self.cwd}: {exc}") from exc
        result = CommandResult(done.returncode, done.stdout, done.stderr)
        if check and not result.ok:
            detail = (result.stderr or result.stdout).strip().splitlines()[-3:]
            raise UpdateError(f"'{' '.join(argv)}' failed: {' | '.join(detail)}")
        return result

    def read(self, *argv: str, attempts: int = 5, delay: float = 10.0) -> CommandResult:
        """Run a reading command, retrying on failure.

        Args:
            *argv: Program and arguments.
            attempts: Number of tries.
            delay: Seconds between tries.

        Returns:
            The first successful result.

        Raises:
            UpdateError: If every attempt fails.
        """
        result = CommandResult(1)
        for attempt in range(attempts):
            result = self.run(*argv, check=False)
            if result.ok:
                return result
            if attempt + 1 < attempts:
                self._sleep(delay)
        raise UpdateError(f"'{' '.join(argv)}' failed {attempts} times: "
                          f"{result.stderr.strip()[:200]}")

    def live(self, *argv: str) -> int:
        """Run a command whose output goes straight to our standard output.

        Args:
            *argv: Program and arguments.

        Returns:
            Exit status of the command.

        Raises:
            UpdateError: If the command cannot start.
        """
        try:
            return subprocess.run(self._argv(argv), cwd=self.cwd, env=self._env,
                                  check=False).returncode
        except OSError as exc:
            raise UpdateError(f"'{argv[0]}' could not start in {self.cwd}: {exc}") from exc
