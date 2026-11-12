#!/usr/bin/env python3
"""Write the options table of the user guide from the settings schema.

Usage (normal user, in the repository)::

    python3 tools/settings_table.py          # rewrite docs/user/README.md
    python3 tools/settings_table.py --check  # exit 1 if the table is outdated

The table lies between the markers ``<!-- settings-table:start -->`` and
``<!-- settings-table:end -->``. A test runs ``--check``, so the guide cannot
drift from the program.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# pylint: disable=wrong-import-position
from scanbench.domain.settings_schema import DEFINITIONS  # noqa: E402

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "user" / "README.md"
"""The user guide."""

START, END = "<!-- settings-table:start -->", "<!-- settings-table:end -->"
"""Markers around the generated table."""


def table() -> str:
    """Return the options table as Markdown.

    Returns:
        One row per setting.
    """
    lines = ["| Tab | Setting | Section | Values | Built-in | File key | Meaning |",
             "|---|---|---|---|---|---|---|"]
    for item in DEFINITIONS:
        if item.choices:
            values = " / ".join(label for label, _ in item.choices)
            if item.device:
                values += " (as offered by the scanner)"
        elif item.bounds is not None:
            values = f"{item.bounds[0]} to {item.bounds[1]} {item.unit}".strip()
        elif isinstance(item.default, bool):
            values = "on / off"
        elif isinstance(item.default, int):
            values = f"as offered by the scanner ({item.unit})"
        else:
            values = "folder"
        lines.append(f"| {item.tab} | {item.label} | {item.group} | {values} | "
                     f"{item.text(item.default)} | `{item.key}` | {item.help} |")
    return "\n".join(lines)


def updated(text: str) -> str:
    """Return the guide with a fresh table.

    Args:
        text: Current guide.

    Returns:
        The guide with the table between the markers replaced.

    Raises:
        ValueError: If the markers are missing.
    """
    head, start, rest = text.partition(START)
    _old, end, tail = rest.partition(END)
    if not start or not end:
        raise ValueError(f"markers {START} / {END} missing in {GUIDE}")
    return f"{head}{START}\n{table()}\n{END}{tail}"


def main() -> int:
    """Rewrite or check the guide.

    Returns:
        0 if written or current, 1 if ``--check`` finds an outdated table.
    """
    text = GUIDE.read_text(encoding="utf-8")
    fresh = updated(text)
    if "--check" in sys.argv[1:]:
        if fresh != text:
            print("the settings table in docs/user/README.md is outdated; "
                  "run python3 tools/settings_table.py")
            return 1
        return 0
    GUIDE.write_text(fresh, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
