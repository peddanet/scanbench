#!/usr/bin/env python3
"""Gate 0: refuse private terms in tracked files, file paths and commit messages.

The deny list lives outside the repository, one term per line (case
insensitive, ``#`` starts a comment):

* ``$SCANBENCH_PRIVACY_DENY`` if set, else
* ``$SCANBENCH_HOME/privacy/deny.txt`` if ``SCANBENCH_HOME`` is set, else
* ``~/.config/scanbench/privacy/deny.txt``.

Typical entries: the scanner's IP address, host names, user names, album
names. Without a list the gate passes neutrally (this is the case in CI).
Text of PDF files is extracted with ``pdftotext`` if available.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def deny_list_path() -> Path:
    """Return the location of the deny list.

    Returns:
        Path of the deny list file (it may not exist).
    """
    explicit = os.environ.get("SCANBENCH_PRIVACY_DENY")
    if explicit:
        return Path(explicit).expanduser()
    home = os.environ.get("SCANBENCH_HOME")
    base = Path(home).expanduser() if home else Path.home() / ".config" / "scanbench"
    return base / "privacy" / "deny.txt"


def load_terms(path: Path) -> list[str]:
    """Read the deny terms.

    Args:
        path: Deny list file.

    Returns:
        Lower-case terms without comments and blank lines.
    """
    terms = []
    for line in path.read_text(encoding="utf-8").splitlines():
        term = line.split("#", 1)[0].strip().lower()
        if term:
            terms.append(term)
    return terms


def git(*args: str) -> str:
    """Run a read-only git command in the repository.

    Args:
        *args: Arguments after ``git``.

    Returns:
        Standard output of the command.
    """
    exe = shutil.which("git") or "git"
    return subprocess.run([exe, *args], capture_output=True, text=True, check=True).stdout


def file_text(path: Path) -> str:
    """Return the searchable text of a tracked file.

    Args:
        path: File below the repository root.

    Returns:
        Extracted PDF text, or the file decoded leniently.
    """
    pdftotext = shutil.which("pdftotext")
    if path.suffix.lower() == ".pdf" and pdftotext:
        result = subprocess.run([pdftotext, str(path), "-"], capture_output=True,
                                text=True, check=False)
        return result.stdout
    return path.read_bytes().decode("utf-8", errors="ignore")


def findings(terms: list[str]) -> list[str]:
    """Search paths, contents and commit messages for the terms.

    Args:
        terms: Lower-case deny terms.

    Returns:
        One line per finding.
    """
    found = []
    for name in git("ls-files").splitlines():
        path = Path(name)
        if not path.is_file():
            continue
        text = file_text(path).lower()
        for term in terms:
            if term in name.lower():
                found.append(f"path      {name}: '{term}'")
            if term in text:
                found.append(f"content   {name}: '{term}'")
    # A fresh repository has no commits yet; git log would fail there.
    exe = shutil.which("git") or "git"
    has_commits = subprocess.run([exe, "rev-parse", "--verify", "-q", "HEAD"],
                                 capture_output=True, check=False).returncode == 0
    log = git("log", "--format=%B", "--all").lower() if has_commits else ""
    found.extend(f"commit    message contains '{t}'" for t in terms if t in log)
    return found


def main() -> int:
    """Run the gate.

    Returns:
        0 if nothing was found or no list exists, 1 on findings.
    """
    path = deny_list_path()
    if not path.is_file():
        print(f"no deny list at {path}: gate neutral (PASS)")
        return 0
    terms = load_terms(path)
    result = findings(terms)
    for line in result:
        print(line)
    print(f"{len(terms)} terms checked, {len(result)} findings")
    return 1 if result else 0


if __name__ == "__main__":
    sys.exit(main())
