"""A printer known to CUPS."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PrinterInfo:
    """One CUPS destination.

    Attributes:
        name: CUPS queue name.
        is_default: Whether it is the system default.
    """

    name: str
    is_default: bool
