"""Release version in Semantic Versioning form."""

import re
from dataclasses import dataclass

_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True, order=True)
class Version:
    """A ``MAJOR.MINOR.PATCH`` version; instances sort numerically.

    Attributes:
        major: Incompatible changes.
        minor: Compatible new functions.
        patch: Compatible fixes.
    """

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> "Version":
        """Parse ``X.Y.Z`` or a tag ``vX.Y.Z``.

        Args:
            text: Version or tag text.

        Returns:
            The version.

        Raises:
            ValueError: If the text is not a version.
        """
        match = _PATTERN.match(text.strip())
        if match is None:
            raise ValueError(f"not a version: {text!r}")
        return cls(int(match[1]), int(match[2]), int(match[3]))

    def __str__(self) -> str:
        """Return ``X.Y.Z``.

        Returns:
            The version text.
        """
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def tag(self) -> str:
        """Release tag of this version.

        Returns:
            ``vX.Y.Z``.
        """
        return f"v{self}"
