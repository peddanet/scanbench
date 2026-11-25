#!/usr/bin/env python3
"""Gate 0: refuse terms and identities that allow conclusions about private data.

Same rules as ``tools/privacy_scan.py`` of mediatools (dev-conventions
handover v8); only the locations of the lists differ, and tag annotations
are searched as well.

The terms are never part of the repository - a list of them would itself
reveal what it protects. Both lists live in the configuration, one entry per
line, ``#`` starts a comment (samples with invented content: ``examples/privacy/``):

* deny list (forbidden terms, at least 3 characters): ``$SCANBENCH_PRIVACY_DENY``
  if set, else ``$XDG_CONFIG_HOME/scanbench/privacy/denylist.txt``
  (default ``~/.config/scanbench/privacy/``). The older name ``deny.txt`` in
  the same folder is still read, with a hint to rename it;
* allow list (allowed phrases): ``$SCANBENCH_PRIVACY_ALLOW`` if set, else
  ``allowlist.txt`` next to the deny list. Allowed phrases are blanked out
  before the search, so a term stays forbidden everywhere except inside an
  allowed phrase - e.g. the term ``level`` with the allowed phrase
  ``sea level``.

Scanned are the contents of all tracked files (PDFs via ``pdftotext`` if
installed), the tracked file paths, all commit messages, the annotations of
all tags and the identities: author and committer of every commit, tagger of
every tag. Matching ignores case; a term must not be part of a longer word
(``cat`` does not match ``concatenate``).

Every e-mail address of an identity must be a no-reply address
(``*@users.noreply.github.com``, ``noreply@github.com``,
``noreply@anthropic.com``) or stand on its own line in the allow list.
Findings name the commit or tag and show the address masked. A no-reply
address and a name equal to its login are not searched for terms: they are
the public pseudonym the conventions prescribe.

**A gate must never pass because its input is missing:** without any local
term the scan fails (exit 2). Only in CI (``CI=true``, always set by GitHub
Actions), which has no local list by design, it is skipped and says so.

Exit codes: 0 clean or skipped in CI, 1 terms or private addresses found,
2 no local terms.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NO_REPLY = re.compile(r"^[^@\s]+@users\.noreply\.github\.com$|^noreply@github\.com$"
                      r"|^noreply@anthropic\.com$", re.IGNORECASE)
"""No-reply addresses: GitHub per-user and shared, co-author trailer."""

MIN_LENGTH = 3
"""Shorter terms are ignored: they would match too much."""


def config_dir(environ: dict[str, str], home: Path) -> Path:
    """Return the configuration directory of scanbench.

    Args:
        environ: Environment variables.
        home: Home directory.

    Returns:
        ``$XDG_CONFIG_HOME/scanbench`` (absolute value only) or
        ``~/.config/scanbench``.
    """
    value = environ.get("XDG_CONFIG_HOME", "")
    base = Path(value) if value and Path(value).is_absolute() else home / ".config"
    return base / "scanbench"


def deny_list_path(environ: dict[str, str], home: Path) -> tuple[Path, str]:
    """Return the deny list to use and a hint if it has an old name.

    Args:
        environ: Environment variables.
        home: Home directory.

    Returns:
        Path of the deny list (it may not exist) and a hint, empty if none.
    """
    explicit = environ.get("SCANBENCH_PRIVACY_DENY", "")
    if explicit:
        return Path(explicit).expanduser(), ""
    current = config_dir(environ, home) / "privacy" / "denylist.txt"
    if current.is_file():
        return current, ""
    old = current.with_name("deny.txt")
    if old.is_file():
        return old, f"old name {old} - please rename it to {current}"
    return current, ""


def allow_list_path(environ: dict[str, str], deny: Path) -> Path:
    """Return the allow list to use.

    Args:
        environ: Environment variables.
        deny: The deny list in use.

    Returns:
        Path of the allow list (it may not exist).
    """
    explicit = environ.get("SCANBENCH_PRIVACY_ALLOW", "")
    return Path(explicit).expanduser() if explicit else deny.with_name("allowlist.txt")


def read_list(path: Path) -> list[str]:
    """Read a local list.

    Args:
        path: List file.

    Returns:
        Entries without comments and empty lines; empty if the file is missing.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            return [entry for entry in (line.split("#", 1)[0].strip() for line in handle)
                    if entry]
    except FileNotFoundError:
        return []


def mask(address: str) -> str:
    """Hide an e-mail address except its shape.

    Args:
        address: The address.

    Returns:
        First letter of the local part and of the domain, the rest replaced,
        e.g. ``p***@g***.com``.
    """
    local, _, domain = address.partition("@")
    name, _, suffix = domain.rpartition(".")
    return f"{local[:1]}***@{name[:1]}***.{suffix}" if name else f"{local[:1]}***@***"


def _phrase(text: str) -> str:
    """Build the regular expression of one allowed phrase.

    Word boundaries are required only where the phrase begins or ends with a
    letter or digit, so ``top-level`` does not cover ``stop-level`` while
    ``key=`` may be followed by anything.

    Args:
        text: Allowed phrase.

    Returns:
        Regular expression.
    """
    start = r"(?<![a-z0-9])" if text[0].isalnum() else ""
    end = r"(?![a-z0-9])" if text[-1].isalnum() else ""
    return start + re.escape(text) + end


class PrivacyScan:
    """Searches the repository for local terms and private identities.

    Attributes:
        repo: Repository root.
        terms: Terms to search for (lower case, longest first).
        pattern: Compiled alternation of all terms, or None.
        allowed: Compiled alternation of the allowed phrases, or None.
        allowed_count: Number of allowed phrases.
        allowed_addresses: Addresses accepted as identities.
        findings: ``(location, term or reason)`` pairs.
    """

    def __init__(self, repo: str, terms: list[str], allowed: list[str] | None = None) -> None:
        """Prepare the search.

        Args:
            repo: Repository root.
            terms: Terms to search for.
            allowed: Phrases in which a term is permitted; addresses accepted
                as identities.
        """
        self.repo = repo
        self.terms = sorted({t.strip().lower() for t in terms if len(t.strip()) >= MIN_LENGTH},
                            key=len, reverse=True)
        self.pattern = re.compile(
            r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in self.terms) + r")(?![a-z0-9])",
            re.IGNORECASE) if self.terms else None
        phrases = sorted({a.strip() for a in allowed or [] if a.strip()}, key=len, reverse=True)
        self.allowed = re.compile("|".join(_phrase(a) for a in phrases),
                                  re.IGNORECASE) if phrases else None
        self.allowed_count = len(phrases)
        self.allowed_addresses = {a.strip().lower() for a in allowed or [] if "@" in a}
        self.findings: list[tuple[str, str]] = []

    def _git(self, *args: str) -> str:
        """Run a read-only git command in the repository.

        Args:
            *args: git arguments.

        Returns:
            Standard output.
        """
        git = shutil.which("git") or "git"
        return subprocess.run([git, "-C", self.repo, *args], capture_output=True, text=True,
                              errors="surrogateescape", check=True).stdout

    def _text_of(self, path: str) -> str | None:
        """Return the searchable text of a tracked file.

        Args:
            path: Path relative to the repository.

        Returns:
            Text, or None for binary files that cannot be converted and for
            files deleted in the working copy.
        """
        full = os.path.join(self.repo, path)
        if not os.path.isfile(full):
            return None
        with open(full, "rb") as handle:
            data = handle.read()
        if path.lower().endswith(".pdf"):
            tool = shutil.which("pdftotext")
            if tool is None:
                print(f"warning: pdftotext missing, not scanned: {path}", file=sys.stderr)
                return None
            return subprocess.run([tool, full, "-"], capture_output=True, text=True,
                                  errors="replace", check=False).stdout
        if b"\0" in data:
            return None
        return data.decode("utf-8", errors="replace")

    def _search(self, location: str, text: str) -> None:
        """Record every term found in a text.

        Args:
            location: Where the text comes from.
            text: Text to search.
        """
        if self.pattern is None:
            return
        for number, line in enumerate(text.splitlines(), 1):
            if self.allowed is not None:
                line = self.allowed.sub(lambda m: " " * len(m.group(0)), line)
            for match in self.pattern.finditer(line):
                self.findings.append((f"{location}:{number}", match.group(1)))

    def identities(self) -> list[tuple[str, str, str]]:
        """List the identities of the history.

        Returns:
            ``(location, name, address)`` for author and committer of every
            commit and the tagger of every annotated tag.
        """
        result: list[tuple[str, str, str]] = []
        log = self._git("log", "--all", "--format=%h%x00%an%x00%ae%x00%cn%x00%ce")
        for line in log.splitlines():
            parts = line.split("\0")
            if len(parts) == 5:
                result.append((f"commit {parts[0]} author", parts[1], parts[2]))
                result.append((f"commit {parts[0]} committer", parts[3], parts[4]))
        tags = self._git("for-each-ref", "refs/tags",
                         "--format=%(refname:short)%00%(taggername)%00%(taggeremail)")
        for line in tags.splitlines():
            parts = line.split("\0")
            if len(parts) == 3 and (parts[1] or parts[2]):
                result.append((f"tag {parts[0]} tagger", parts[1], parts[2].strip("<>")))
        return result

    def check_identities(self) -> None:
        """Search names and addresses for terms; demand no-reply addresses.

        A no-reply address is a pseudonym GitHub publishes for the account
        (``<id>+<login>@users.noreply.github.com``); it and a name equal to its
        login are the identity the conventions prescribe, so they are not
        searched for terms (a deny list may hold the login to keep it out of
        files).
        """
        for location, name, address in self.identities():
            if NO_REPLY.match(address):
                login = address.split("@", 1)[0].rpartition("+")[2].lower()
                if name.strip().lower() != login:
                    self._search(f"{location} name", name)
                continue
            self._search(f"{location} name", name)
            self._search(f"{location} e-mail", address)
            if address.lower() not in self.allowed_addresses:
                self.findings.append((location, f"not a no-reply address: {mask(address)}"))

    def run(self) -> int:
        """Scan files, paths, commit messages, tag annotations and identities.

        Returns:
            0 if clean (or skipped in CI), 1 if something was found, 2 if
            there are no local terms outside CI.
        """
        if self.pattern is None:
            if os.environ.get("CI") == "true":
                print("privacy scan skipped in CI: no local terms by design "
                      "(the deny list exists only on the developer's machine)")
                return 0
            print("privacy scan FAILED: no local terms - a scan without terms checks "
                  "nothing.\n  Create the lists from the samples: CONTRIBUTING.md, "
                  "\"Local files of a developer\".", file=sys.stderr)
            return 2
        for path in self._git("ls-files", "-z").split("\0"):
            if not path:
                continue
            self._search(f"path {path}", path)
            text = self._text_of(path)
            if text is not None:
                self._search(path, text)
        self._search("commit messages", self._git("log", "--all", "--format=commit %h%n%B"))
        self._search("tag annotations",
                     self._git("for-each-ref", "refs/tags",
                               "--format=tag %(refname:short)%0a%(contents)"))
        self.check_identities()
        for location, term in self.findings:
            print(f"{location}: {term}")
        print(f"privacy scan: {len(self.terms)} term(s), {self.allowed_count} allowed "
              f"phrase(s), {len(self.findings)} finding(s)")
        return 1 if self.findings else 0


def main() -> int:
    """Command-line entry point.

    Returns:
        Exit code.
    """
    environ = dict(os.environ)
    deny, hint = deny_list_path(environ, Path.home())
    if hint:
        print(hint)
    repo = str(Path(__file__).resolve().parent.parent)
    return PrivacyScan(repo, read_list(deny), read_list(allow_list_path(environ, deny))).run()


if __name__ == "__main__":
    sys.exit(main())
