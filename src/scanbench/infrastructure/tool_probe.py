"""Look up external programs on ``PATH``."""

import shutil
from collections.abc import Callable


class ToolProbe:
    """Find the absolute path of external programs.

    The lookup function is injected so tests do not depend on the programs
    installed on the machine that runs them.
    """

    def __init__(self, which: Callable[[str], str | None] = shutil.which) -> None:
        """Store the lookup function.

        Args:
            which: Function that maps a program name to its path or None.
        """
        self._which = which

    def locate(self, name: str) -> str | None:
        """Return the absolute path of a program.

        Args:
            name: Program name, e.g. ``scanimage``.

        Returns:
            The path, or None if the program is not on ``PATH``.
        """
        return self._which(name)
