"""Tests of gate 0, tools/privacy_scan.py (rules as in mediatools)."""

import shutil
import subprocess
from pathlib import Path

import privacy_scan
import pytest

NO_REPLY = "1+t@users.noreply.github.com"
"""A per-user no-reply address with the login ``t``."""


def _git(repo: Path, *args: str, name: str = "t", mail: str = NO_REPLY) -> None:
    """Run git in a test repository with a fixed identity.

    Args:
        repo: Repository directory.
        *args: Arguments after ``git``.
        name: Author, committer and tagger name.
        mail: Author, committer and tagger address.
    """
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": mail,
           "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": mail,
           "HOME": str(repo), "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", "-C", str(repo), *args], env=env, check=True,
                   capture_output=True, timeout=30)


def _repo(path: Path, files: dict[str, bytes], message: str = "initial",
          mail: str = NO_REPLY) -> str:
    """Create a repository with one commit of the given files.

    Args:
        path: Repository root.
        files: Relative path to content.
        message: Commit message.
        mail: Address of author and committer.

    Returns:
        The repository root as text.
    """
    for name, data in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_bytes(data)
    _git(path, "init", "-q")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", message, mail=mail)
    return str(path)


def test_finds_terms_in_files_paths_and_messages(tmp_path: Path,
                                                 capsys: pytest.CaptureFixture[str]) -> None:
    """Terms are found in content, file names and commit messages; whole words only.

    Args:
        tmp_path: Temporary directory of the test.
        capsys: Captures standard output.
    """
    repo = _repo(tmp_path, {"docs/a.md": b"An example with Secretname inside.\n",
                            "secretname_notes.txt": b"neutral\n",
                            "words.txt": b"concatenate the files\n",
                            "blob.bin": b"\0secretname\0"},
                 message="add notes about secretname")
    scan = privacy_scan.PrivacyScan(repo, ["secretname", "cat", "ab"])
    assert scan.run() == 1
    locations = [location for location, _term in scan.findings]
    assert "docs/a.md:1" in locations
    assert any(loc.startswith("path secretname_notes.txt") for loc in locations)
    assert any(loc.startswith("commit messages") for loc in locations)
    assert not any("words.txt" in loc for loc in locations)      # no partial words
    assert not any(loc.startswith("blob.bin") for loc in locations)   # binary skipped
    assert "ab" not in scan.terms                                # too short
    assert "finding(s)" in capsys.readouterr().out


def test_clean_and_without_terms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    """A clean repository passes; without terms the scan fails, in CI it is skipped.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output and error.
    """
    repo = _repo(tmp_path, {"a.txt": b"nothing to see\n"})
    assert privacy_scan.PrivacyScan(repo, ["hidden"]).run() == 0
    monkeypatch.delenv("CI", raising=False)
    assert privacy_scan.PrivacyScan(repo, []).run() == 2
    assert "FAILED: no local terms" in capsys.readouterr().err
    monkeypatch.setenv("CI", "true")
    assert privacy_scan.PrivacyScan(repo, []).run() == 0
    assert "skipped in CI" in capsys.readouterr().out


def test_identities_need_no_reply_addresses(tmp_path: Path,
                                            capsys: pytest.CaptureFixture[str]) -> None:
    """Author, committer and tagger: terms are found, private addresses refused (masked).

    Args:
        tmp_path: Temporary directory of the test.
        capsys: Captures standard output.
    """
    repo = _repo(tmp_path, {"a.txt": b"nothing to see\n"},
                 mail="someone@private-mail.example")
    _git(tmp_path, "tag", "-a", "v1", "-m", "v1", name="Hiddenname")
    _git(tmp_path, "tag", "light")
    scan = privacy_scan.PrivacyScan(repo, ["hiddenname"])
    assert scan.run() == 1
    found = dict(scan.findings)
    commit = scan.findings[0][0].split()[1]
    assert found[f"commit {commit} author"] == "not a no-reply address: s***@p***.example"
    assert any(loc.startswith("tag v1 tagger name") for loc, _t in scan.findings)
    assert not any("light" in loc for loc, _t in scan.findings)     # no tagger
    assert "someone@" not in capsys.readouterr().out
    allowed = privacy_scan.PrivacyScan(repo, ["unrelated"], ["someone@private-mail.example"])
    assert allowed.run() == 0
    assert privacy_scan.mask("x@localhost") == "x***@***"


def test_no_reply_login_is_not_a_finding(tmp_path: Path) -> None:
    """The login in a no-reply identity may be a deny-list term; another name is searched.

    Args:
        tmp_path: Temporary directory of the test.
    """
    repo = _repo(tmp_path, {"a.txt": b"nothing to see\n"})   # name t, address 1+t@...
    assert privacy_scan.PrivacyScan(repo, ["ttt", "users"]).run() == 0
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "x", name="Hiddenname")
    scan = privacy_scan.PrivacyScan(repo, ["hiddenname"])
    assert scan.run() == 1
    assert {loc.rsplit(" ", 1)[-1] for loc, _t in scan.findings} == {"name:1"}


def test_allowed_phrases_are_blanked(tmp_path: Path) -> None:
    """A term inside an allowed phrase passes; elsewhere it is still found.

    Args:
        tmp_path: Temporary directory of the test.
    """
    repo = _repo(tmp_path, {"a.md": b"the sea level rises\nraise the level\nlevel=3\n"})
    scan = privacy_scan.PrivacyScan(repo, ["level"], ["Sea Level", "level="])
    assert scan.run() == 1
    assert [location for location, _term in scan.findings] == ["a.md:2"]
    assert scan.allowed_count == 2


def test_tag_annotations_are_searched(tmp_path: Path) -> None:
    """A term in the annotation of a tag is found.

    Args:
        tmp_path: Temporary directory of the test.
    """
    repo = _repo(tmp_path, {"a.txt": b"nothing to see\n"})
    _git(tmp_path, "tag", "-a", "v1", "-m", "built on secrethost")
    scan = privacy_scan.PrivacyScan(repo, ["secrethost"])
    assert scan.run() == 1
    assert scan.findings[0][0].startswith("tag annotations:")


def test_pdf_and_deleted_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                               capsys: pytest.CaptureFixture[str]) -> None:
    """Without pdftotext a PDF is reported as not scanned; a deleted file is skipped.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Replaces the program lookup.
        capsys: Captures standard error.
    """
    repo = _repo(tmp_path, {"doc.pdf": b"%PDF-1.4 secrethost", "gone.txt": b"secrethost\n"})
    (tmp_path / "gone.txt").unlink()
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which",
                        lambda name: None if name == "pdftotext" else real_which(name))
    scan = privacy_scan.PrivacyScan(repo, ["secrethost"])
    assert scan.run() == 0
    assert "pdftotext missing, not scanned: doc.pdf" in capsys.readouterr().err


def test_list_locations(tmp_path: Path) -> None:
    """Explicit path, XDG name, old names with hint, allow list next to deny list.

    Args:
        tmp_path: Temporary directory of the test.
    """
    home = tmp_path / "home"
    current = home / ".config" / "scanbench" / "privacy" / "denylist.txt"
    assert privacy_scan.deny_list_path({}, home) == (current, "")
    assert privacy_scan.deny_list_path({"SCANBENCH_PRIVACY_DENY": "/x/d.txt"}, home) \
        == (Path("/x/d.txt"), "")
    assert privacy_scan.deny_list_path({"XDG_CONFIG_HOME": "rel"}, home) == (current, "")
    old_config = current.with_name("deny.txt")
    old_config.parent.mkdir(parents=True)
    old_config.write_text("term\n", encoding="utf-8")
    path, hint = privacy_scan.deny_list_path({}, home)
    assert path == old_config and "rename" in hint
    current.write_text("term\n", encoding="utf-8")
    assert privacy_scan.deny_list_path({}, home) == (current, "")
    assert privacy_scan.allow_list_path({}, current) == current.with_name("allowlist.txt")
    assert privacy_scan.allow_list_path({"SCANBENCH_PRIVACY_ALLOW": "/a"}, current) \
        == Path("/a")


def test_read_list_ignores_comments(tmp_path: Path) -> None:
    """Comments and empty lines are skipped; a missing file is empty.

    Args:
        tmp_path: Temporary directory of the test.
    """
    path = tmp_path / "allowlist.txt"
    assert not privacy_scan.read_list(path)
    path.write_text("# allowed\nsea level  # why\n\n", encoding="utf-8")
    assert privacy_scan.read_list(path) == ["sea level"]


def test_main_reads_the_lists_and_prints_the_hint(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch,
                                                  capsys: pytest.CaptureFixture[str]) -> None:
    """main() scans this repository with the configured lists.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    old = tmp_path / "home" / ".config" / "scanbench" / "privacy" / "deny.txt"
    old.parent.mkdir(parents=True)
    old.write_text("zzqqxxunlikelyterm\n", encoding="utf-8")
    monkeypatch.delenv("SCANBENCH_PRIVACY_DENY", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "home" / ".config"))
    assert privacy_scan.main() in (0, 1)                # this repository's own history
    out = capsys.readouterr().out
    assert "please rename it" in out and "1 term(s)" in out
