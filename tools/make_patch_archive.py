#!/usr/bin/env python3
"""Build a delivery archive ``scanbench-X.Y.Z-patch-N.tar.gz`` from git commits.

Usage (normal user, in the repository)::

    python3 tools/make_patch_archive.py BASE_REF OUT_DIR [--build N]

The archive holds the patches ``BASE_REF..HEAD`` (``git format-patch``) and a
file ``BASE`` with the version of ``BASE_REF``; ``scanbench update`` uses it to
check that every archive follows the version it was built on. X.Y.Z is the
version of ``HEAD``.
"""

import argparse
import re
import subprocess  # nosec B404 - runs git with fixed arguments
import sys
import tarfile
import tempfile
from pathlib import Path

VERSION_FILE = "src/scanbench/__init__.py"
"""File with the ``__version__`` line."""


def _git(*args: str) -> str:
    """Run git and return its output.

    Args:
        *args: Git arguments.

    Returns:
        Standard output.
    """
    return subprocess.run(["git", *args], check=True, capture_output=True,  # nosec B603 B607
                          text=True).stdout


def version_at(ref: str) -> str:
    """Return the version line of a commit.

    Args:
        ref: Git reference.

    Returns:
        The version, e.g. ``0.2.8``.

    Raises:
        ValueError: If the file has no version line.
    """
    match = re.search(r'__version__ = "([^"]+)"', _git("show", f"{ref}:{VERSION_FILE}"))
    if match is None:
        raise ValueError(f"no version line in {ref}:{VERSION_FILE}")
    return match[1]


def build(base: str, out_dir: Path, number: int) -> Path:
    """Write the archive.

    Args:
        base: Commit the patches are based on (the previous delivery).
        out_dir: Target folder.
        number: Delivery number N of this version.

    Returns:
        The archive path.
    """
    name = f"scanbench-{version_at('HEAD')}-patch-{number}"
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / name
        folder.mkdir()
        _git("format-patch", "-q", f"{base}..HEAD", "-o", str(folder))
        (folder / "BASE").write_text(version_at(base) + "\n", encoding="utf-8")
        target = out_dir / f"{name}.tar.gz"
        with tarfile.open(target, "w:gz") as tar:
            tar.add(folder, arcname=name)
    return target


def main() -> int:
    """Parse the arguments and build the archive.

    Returns:
        Exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("base", help="commit of the previous delivery")
    parser.add_argument("out_dir", type=Path, help="folder for the archive")
    parser.add_argument("--build", type=int, default=1, help="delivery number N (default 1)")
    args = parser.parse_args()
    print(build(args.base, args.out_dir, args.build))
    return 0


if __name__ == "__main__":
    sys.exit(main())
