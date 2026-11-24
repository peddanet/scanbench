"""Tests of gate 0, tools/privacy_scan.py: lists, terms and identities."""

import subprocess
from pathlib import Path

import privacy_scan
import pytest

NO_REPLY = "2825623+someone@users.noreply.github.com"
"""A per-user no-reply address."""


def _git(repo: Path, *args: str, mail: str = NO_REPLY) -> None:
    """Run git in a test repository with a fixed identity.

    Args:
        repo: Repository directory.
        *args: Arguments after ``git``.
        mail: Author, committer and tagger address.
    """
    env = {"GIT_AUTHOR_NAME": "someone", "GIT_AUTHOR_EMAIL": mail,
           "GIT_COMMITTER_NAME": "someone", "GIT_COMMITTER_EMAIL": mail,
           "HOME": str(repo), "PATH": "/usr/bin:/bin"}
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True,
                   timeout=30)


@pytest.fixture(name="repo")
def fixture_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository with one clean commit, the current directory of the test.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Changes directory and environment for the test.

    Returns:
        The repository directory.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "develop")
    (repo / "README.md").write_text("Lorem ipsum\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    monkeypatch.chdir(repo)
    for variable in ("CI", "SCANBENCH_HOME"):
        monkeypatch.delenv(variable, raising=False)
    return repo


def _lists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, deny: str,
           allow: str = "") -> None:
    """Write deny and allow list and point the gate at them.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        deny: Content of the deny list.
        allow: Content of the allow list.
    """
    (tmp_path / "denylist.txt").write_text(deny, encoding="utf-8")
    (tmp_path / "allowlist.txt").write_text(allow, encoding="utf-8")
    monkeypatch.setenv("SCANBENCH_PRIVACY_DENY", str(tmp_path / "denylist.txt"))
    monkeypatch.delenv("SCANBENCH_PRIVACY_ALLOW", raising=False)


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
    relative = privacy_scan.deny_list_path({"XDG_CONFIG_HOME": "rel"}, home)
    assert relative == (current, "")
    old_config = current.with_name("deny.txt")
    old_config.parent.mkdir(parents=True)
    old_config.write_text("term\n", encoding="utf-8")
    path, hint = privacy_scan.deny_list_path({}, home)
    assert path == old_config and "rename" in hint
    root = tmp_path / "root"
    (root / "privacy").mkdir(parents=True)
    (root / "privacy" / "deny.txt").write_text("term\n", encoding="utf-8")
    assert privacy_scan.deny_list_path({"SCANBENCH_HOME": str(root)}, home)[0] \
        == root / "privacy" / "deny.txt"
    current.write_text("term\n", encoding="utf-8")
    assert privacy_scan.deny_list_path({"SCANBENCH_HOME": str(root)}, home) == (current, "")
    assert privacy_scan.allow_list_path({}, current) == current.with_name("allowlist.txt")
    assert privacy_scan.allow_list_path({"SCANBENCH_PRIVACY_ALLOW": "/a"}, current) \
        == Path("/a")


def test_load_entries(tmp_path: Path) -> None:
    """Comments, blank lines and case are ignored; a missing file is empty.

    Args:
        tmp_path: Temporary directory of the test.
    """
    path = tmp_path / "list.txt"
    assert not privacy_scan.load_entries(path)
    path.write_text("# comment\n\n  Term One  # note\nTWO\n", encoding="utf-8")
    assert privacy_scan.load_entries(path) == ["term one", "two"]


def test_no_terms_fails_outside_ci(repo: Path, tmp_path: Path,
                                   monkeypatch: pytest.MonkeyPatch,
                                   capsys: pytest.CaptureFixture[str]) -> None:
    """Without terms the gate fails (exit 2); CI skips it with a notice.

    Args:
        repo: Test repository.
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    assert repo.is_dir()
    _lists(tmp_path, monkeypatch, "# only a comment\n")
    assert privacy_scan.main() == 2
    assert "gate FAILS" in capsys.readouterr().out
    monkeypatch.setenv("CI", "true")
    assert privacy_scan.main() == 0
    assert "skipped" in capsys.readouterr().out


def test_clean_repository_passes(repo: Path, tmp_path: Path,
                                 monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
    """No term anywhere and only no-reply identities: PASS.

    Args:
        repo: Test repository.
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    _git(repo, "tag", "-a", "v0.1.0", "-m", "first")
    _git(repo, "tag", "light")
    _lists(tmp_path, monkeypatch, "secret-host\n")
    assert privacy_scan.main() == 0
    assert "0 findings" in capsys.readouterr().out


def test_terms_in_files_paths_messages_and_tags(repo: Path, tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch,
                                                capsys: pytest.CaptureFixture[str]) -> None:
    """A term is found in a path, a content, a commit message and a tag.

    Args:
        repo: Test repository.
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    (repo / "secret-host.txt").write_text("at secret-host\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "copy from secret-host")
    _git(repo, "tag", "-a", "v0.1.0", "-m", "built on secret-host")
    _lists(tmp_path, monkeypatch, "Secret-Host\n")
    assert privacy_scan.main() == 1
    out = capsys.readouterr().out
    for kind in ("path ", "content ", "commit ", "tag "):
        assert kind in out, kind


def test_identities(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                    capsys: pytest.CaptureFixture[str]) -> None:
    """Private addresses fail unless allowed; an allowed address skips the term check.

    Args:
        repo: Test repository.
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "b", mail="me@laptop.home.example")
    _git(repo, "tag", "-a", "v0.2.0", "-m", "two", mail="me@laptop.home.example")
    _lists(tmp_path, monkeypatch, "laptop\n")
    assert privacy_scan.main() == 1
    out = capsys.readouterr().out
    for role in ("author", "committer", "tagger"):
        assert f"identity  {role} someone <me@laptop.home.example>" in out
    assert "not in the allow list" in out and "'laptop'" in out
    _lists(tmp_path, monkeypatch, "laptop\n", "Me@Laptop.home.example  # old\n")
    assert privacy_scan.main() == 0
    assert "1 allowed addresses" in capsys.readouterr().out


def test_old_name_is_reported(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                              capsys: pytest.CaptureFixture[str]) -> None:
    """A deny list with the old name still works and the hint is printed.

    Args:
        repo: Test repository.
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets the environment for the test.
        capsys: Captures standard output.
    """
    assert repo.is_dir()
    root = tmp_path / "root"
    (root / "privacy").mkdir(parents=True)
    (root / "privacy" / "deny.txt").write_text("secret-host\n", encoding="utf-8")
    monkeypatch.delenv("SCANBENCH_PRIVACY_DENY", raising=False)
    monkeypatch.setenv("SCANBENCH_HOME", str(root))
    assert privacy_scan.main() == 0
    assert "please rename it" in capsys.readouterr().out


def test_fresh_repository_has_no_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                         capsys: pytest.CaptureFixture[str]) -> None:
    """Before the first commit only files are checked.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Changes directory and environment for the test.
        capsys: Captures standard output.
    """
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    _git(fresh, "init", "-q")
    monkeypatch.chdir(fresh)
    monkeypatch.delenv("CI", raising=False)
    _lists(tmp_path, monkeypatch, "secret-host\n")
    assert privacy_scan.main() == 0
    assert "0 findings" in capsys.readouterr().out
