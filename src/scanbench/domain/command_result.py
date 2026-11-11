"""Result of an external command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    """Exit status and captured output of one command.

    Attributes:
        returncode: Exit status.
        stdout: Captured standard output.
        stderr: Captured standard error.
    """

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        """Whether the command succeeded.

        Returns:
            True for exit status 0.
        """
        return self.returncode == 0
