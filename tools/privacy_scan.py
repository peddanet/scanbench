#!/usr/bin/env python3
"""Gate 0: refuse private terms and private identities in the repository.

Checked: tracked file paths and contents (PDF text via ``pdftotext`` if
available), commit messages, tag annotations, and the identities of the whole
history - author and committer of every commit, tagger of every annotated tag.

The lists live outside the repository, one entry per line (``#`` starts a
comment, case does not matter). Samples: ``examples/privacy/``.

* Deny list (terms): ``$SCANBENCH_PRIVACY_DENY`` if set, else
  ``$XDG_CONFIG_HOME/scanbench/privacy/denylist.txt``. The older name
  ``privacy/deny.txt`` (below ``$SCANBENCH_HOME`` or
  ``~/.config/scanbench``) is still read, with a hint to rename it.
* Allow list (identities): ``$SCANBENCH_PRIVACY_ALLOW`` if set, else
  ``allowlist.txt`` next to the deny list. Each line is one e-mail address
  that may appear as author, committer or tagger although it is no no-reply
  address. A listed address is also exempt from the term check; the name is
  not.

Every identity must use a no-reply address or stand alone in the allow list.

Exit status: 0 = nothing found, 1 = findings, 2 = no terms to check. A gate
must never pass silently because its input is missing, so a missing or empty
deny list fails - except in CI (``CI=true``), where no private list exists and
the gate is skipped with a notice.
"""

import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

NO_REPLY_SUFFIXES = ("@users.noreply.github.com",)
"""Domains of per-user no-reply addresses."""

NO_REPLY_ADDRESSES = ("noreply@github.com", "noreply@anthropic.com")
"""Shared no-reply addresses (GitHub merge commits, co-author trailers)."""

SAMPLES = ("examples/privacy/denylist.sample.txt", "examples/privacy/allowlist.sample.txt")
"""Samples of the lists: their invented terms would match themselves after
``cp -n``, so their contents are not searched (their paths are)."""

SEP = "\x1f"
"""Field separator in git output (unit separator, never part of a name)."""


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
    old = [config_dir(environ, home) / "privacy" / "deny.txt"]
    root = environ.get("SCANBENCH_HOME", "")
    if root:
        old.insert(0, Path(root).expanduser() / "privacy" / "deny.txt")
    for path in old:
        if path.is_file():
            return path, f"old name {path} - please rename it to {current}"
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


def load_entries(path: Path) -> list[str]:
    """Read a list file.

    Args:
        path: List file; a missing file gives an empty list.

    Returns:
        Lower-case entries without comments and blank lines.
    """
    if not path.is_file():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip().lower()
        if entry:
            entries.append(entry)
    return entries


def git(*args: str) -> str:
    """Run a read-only git command in the repository.

    Args:
        *args: Arguments after ``git``.

    Returns:
        Standard output of the command.
    """
    exe = shutil.which("git") or "git"
    return subprocess.run([exe, *args], capture_output=True, text=True, check=True).stdout


def has_commits() -> bool:
    """Tell whether the repository has a commit (a fresh one has none).

    Returns:
        True if ``HEAD`` exists.
    """
    exe = shutil.which("git") or "git"
    return subprocess.run([exe, "rev-parse", "--verify", "-q", "HEAD"],
                          capture_output=True, check=False).returncode == 0


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


def file_findings(terms: list[str]) -> list[str]:
    """Search tracked paths and contents for the terms.

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
        text = "" if name in SAMPLES else file_text(path).lower()
        for term in terms:
            if term in name.lower():
                found.append(f"path      {name}: '{term}'")
            if term in text:
                found.append(f"content   {name}: '{term}'")
    return found


def identities() -> Counter[tuple[str, str, str]]:
    """Collect author, committer and tagger identities of the whole history.

    Returns:
        Count per (role, name, lower-case e-mail address).
    """
    found: Counter[tuple[str, str, str]] = Counter()
    fmt = SEP.join(("%an", "%ae", "%cn", "%ce"))
    for line in git("log", "--all", f"--format={fmt}").splitlines():
        author, a_mail, committer, c_mail = line.split(SEP)
        found[("author", author, a_mail.lower())] += 1
        found[("committer", committer, c_mail.lower())] += 1
    tag_fmt = "%(taggername)%1f%(taggeremail)"
    for line in git("for-each-ref", f"--format={tag_fmt}", "refs/tags").splitlines():
        tagger, mail = line.split(SEP)
        if tagger:                      # lightweight tags have no tagger
            found[("tagger", tagger, mail.strip("<>").lower())] += 1
    return found


def is_no_reply(mail: str) -> bool:
    """Tell whether an address is a no-reply address.

    Args:
        mail: Lower-case e-mail address.

    Returns:
        True for GitHub per-user no-reply addresses and the shared ones.
    """
    return mail in NO_REPLY_ADDRESSES or mail.endswith(NO_REPLY_SUFFIXES)


def identity_findings(terms: list[str], allowed: list[str]) -> list[str]:
    """Check every identity against no-reply rule, allow list and terms.

    Args:
        terms: Lower-case deny terms.
        allowed: Lower-case e-mail addresses from the allow list.

    Returns:
        One line per finding.
    """
    found = []
    for (role, name, mail), count in sorted(identities().items()):
        who = f"identity  {role} {name} <{mail}> ({count}x)"
        if not is_no_reply(mail) and mail not in allowed:
            found.append(f"{who}: no no-reply address and not in the allow list")
        checked = name.lower() if mail in allowed else f"{name} {mail}".lower()
        found.extend(f"{who}: '{term}'" for term in terms if term in checked)
    return found


def message_findings(terms: list[str]) -> list[str]:
    """Search commit messages and tag annotations for the terms.

    Args:
        terms: Lower-case deny terms.

    Returns:
        One line per finding.
    """
    text = git("log", "--format=%B", "--all").lower()
    tags = git("for-each-ref", "--format=%(contents)", "refs/tags").lower()
    found = [f"commit    message contains '{t}'" for t in terms if t in text]
    found.extend(f"tag       annotation contains '{t}'" for t in terms if t in tags)
    return found


def main() -> int:
    """Run the gate.

    Returns:
        0 if nothing was found, 1 on findings, 2 without terms outside CI.
    """
    environ = dict(os.environ)
    deny, hint = deny_list_path(environ, Path.home())
    terms = load_entries(deny)
    if not terms:
        if environ.get("CI") == "true":
            print("CI: no private deny list here - privacy gate skipped (runs locally)")
            return 0
        allow = deny.with_name("allowlist.txt")
        print(f"no terms in {deny}: nothing can be checked, gate FAILS.\n"
              "Create the lists from the samples (see CONTRIBUTING.md):\n"
              f"  mkdir -p {deny.parent}\n"
              f"  cp -n examples/privacy/denylist.sample.txt {deny}\n"
              f"  cp -n examples/privacy/allowlist.sample.txt {allow}\n"
              f"  chmod 600 {deny} {allow}")
        return 2
    if hint:
        print(hint)
    allowed = load_entries(allow_list_path(environ, deny))
    result = file_findings(terms)
    if has_commits():
        result += identity_findings(terms, allowed) + message_findings(terms)
    for line in result:
        print(line)
    print(f"{len(terms)} terms, {len(allowed)} allowed addresses checked, "
          f"{len(result)} findings")
    return 1 if result else 0


if __name__ == "__main__":
    sys.exit(main())
