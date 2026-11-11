"""Test doubles shared by several test modules."""

from pathlib import Path

from scanbench.domain.command_result import CommandResult
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell


class FakeShell(Shell):
    """Shell that records commands and returns scripted results.

    A script entry maps a command prefix to a list of results; each call
    consumes the first result, the last one is repeated. Unscripted commands
    succeed with empty output.
    """

    def __init__(self, cwd: Path = Path("/clone"),
                 script: dict[tuple[str, ...], list[CommandResult]] | None = None,
                 env: dict[str, str] | None = None) -> None:
        """Store the script.

        Args:
            cwd: Pretended working directory.
            script: Results per command prefix.
            env: Environment passed by the caller (recorded only).
        """
        super().__init__(cwd, which=lambda name: name, sleep=lambda _s: None, env=env)
        self.env = env
        self.script = script or {}
        self.calls: list[tuple[str, ...]] = []
        self.stdin: list[str | None] = []

    def _result(self, argv: tuple[str, ...]) -> CommandResult:
        """Return the scripted result of a command.

        Args:
            argv: Program and arguments.

        Returns:
            The result.
        """
        self.calls.append(argv)
        for prefix, results in self.script.items():
            if argv[:len(prefix)] == prefix:
                return results.pop(0) if len(results) > 1 else results[0]
        return CommandResult(0)

    def run(self, *argv: str, check: bool = True, stdin: str | None = None) -> CommandResult:
        """Record and answer a command.

        Args:
            *argv: Program and arguments.
            check: Raise on failure.
            stdin: Recorded standard input.

        Returns:
            The scripted result.

        Raises:
            UpdateError: If ``check`` is set and the result failed.
        """
        self.stdin.append(stdin)
        result = self._result(argv)
        if check and not result.ok:
            raise UpdateError(f"{' '.join(argv)} failed")
        return result

    def read(self, *argv: str, attempts: int = 5, delay: float = 10.0) -> CommandResult:
        """Record and answer a reading command (no retries needed in tests).

        Args:
            *argv: Program and arguments.
            attempts: Ignored.
            delay: Ignored.

        Returns:
            The scripted result.
        """
        return self.run(*argv)

    def live(self, *argv: str) -> int:
        """Record a live command.

        Args:
            *argv: Program and arguments.

        Returns:
            The scripted exit status.
        """
        return self._result(argv).returncode


def ok(stdout: str = "") -> CommandResult:
    """Return a successful result.

    Args:
        stdout: Standard output.

    Returns:
        The result.
    """
    return CommandResult(0, stdout)


def failed(stderr: str = "error", stdout: str = "") -> CommandResult:
    """Return a failed result.

    Args:
        stderr: Standard error.
        stdout: Standard output.

    Returns:
        The result.
    """
    return CommandResult(1, stdout, stderr)
