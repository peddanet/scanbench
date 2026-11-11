"""What the user chose in the print dialog."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PrintJob:
    """Printer, copies and driver options of one print job.

    Attributes:
        printer: CUPS queue name.
        copies: Number of copies.
        options: Options passed as ``lp -o key=value``.
    """

    printer: str
    copies: int = 1
    options: dict[str, str] = field(default_factory=dict)
