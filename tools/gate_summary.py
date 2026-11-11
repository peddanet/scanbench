#!/usr/bin/env python3
"""Turn the JSON summary of tools/check.sh into a Markdown table.

Used by CI to fill the job summary page:
``python3 tools/gate_summary.py gates.json >> "$GITHUB_STEP_SUMMARY"``.
"""

import json
import sys
from pathlib import Path

ICON = {"PASS": "PASS", "FAIL": "**FAIL**"}
"""Text per status; plain words, readable without emoji support."""


def to_markdown(summary: dict[str, object]) -> str:
    """Render the stages as a Markdown table.

    Args:
        summary: Parsed JSON written by ``tools/check.sh --json``.

    Returns:
        The table with a heading.
    """
    rows = ["### scanbench quality gates", "", "| Stage | Gate | Result | Seconds |",
            "|---|---|---|---|"]
    stages = summary.get("stages", [])
    if isinstance(stages, list):
        for stage in stages:
            rows.append(f"| [{stage['n']}] | {stage['gate']} | "
                        f"{ICON.get(stage['status'], stage['status'])} | {stage['seconds']} |")
    return "\n".join(rows) + "\n"


def main(argv: list[str]) -> int:
    """Print the table for the given JSON file.

    Args:
        argv: Command line; ``argv[1]`` is the JSON file.

    Returns:
        0 on success, 2 on wrong usage, 1 if the file is missing.
    """
    if len(argv) != 2:
        print("usage: gate_summary.py GATES.json", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"no gate summary at {path}", file=sys.stderr)
        return 1
    print(to_markdown(json.loads(path.read_text(encoding="utf-8"))), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
