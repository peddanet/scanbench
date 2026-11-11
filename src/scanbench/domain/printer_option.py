"""A driver option of a printer, parsed from ``lpoptions -l``."""

import re
from dataclasses import dataclass

_LINE = re.compile(r"^(?P<key>[^/:]+)/(?P<label>[^:]+):\s*(?P<choices>.*)$")


@dataclass(frozen=True)
class PrinterOption:
    """One PPD option such as paper source, media type or quality.

    Attributes:
        key: Option name passed to ``lp -o key=value``.
        label: Human-readable name from the driver.
        choices: Possible values.
        default: Current default value.
    """

    key: str
    label: str
    choices: tuple[str, ...]
    default: str

    @classmethod
    def parse_all(cls, text: str) -> list["PrinterOption"]:
        """Parse the output of ``lpoptions -p PRINTER -l``.

        Lines look like ``InputSlot/Paper Source: *Auto Cassette Tray``; the
        value marked with ``*`` is the default.

        Args:
            text: Command output.

        Returns:
            The options in driver order.
        """
        options = []
        for line in text.splitlines():
            match = _LINE.match(line.strip())
            if match is None:
                continue
            values = match["choices"].split()
            default = next((v[1:] for v in values if v.startswith("*")), values[0] if values
                           else "")
            choices = tuple(v.lstrip("*") for v in values)
            options.append(cls(match["key"].strip(), match["label"].strip(), choices, default))
        return options
