"""External program the application uses, with its importance."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolRequirement:
    """An external program and why the application needs it.

    Attributes:
        name: Executable name as searched on ``PATH``.
        required: True if core functions fail without the program.
        purpose: Short English description shown by ``scanbench doctor``.
        package_hint: Debian/Ubuntu package that usually provides the program.
    """

    name: str
    required: bool
    purpose: str
    package_hint: str

    def label(self) -> str:
        """Return the importance as a fixed-width label.

        Returns:
            ``"required"`` or ``"optional"``.
        """
        return "required" if self.required else "optional"
