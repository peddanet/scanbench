"""Tests for GitRepo and GitVersions against real local repositories."""

from pathlib import Path

import pytest

from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.git_repo import GitRepo
from scanbench.infrastructure.git_versions import GitVersions
from scanbench.infrastructure.shell import Shell

INIT = "src/scanbench/__init__.py"


def _write_version(root: Path, version: str) -> None:
    """Write the version line.

    Args:
        root: Repository root.
        version: Version text.
    """
    path = root / INIT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'"""Package."""\n\n__version__ = "{version}"\n', encoding="utf-8")


@pytest.fixture(name="clone")
def fixture_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a bare remote and a clone with release v0.1.0 on main and develop.

    Args:
        tmp_path: Temporary directory of the test.
        monkeypatch: Sets a git identity for the test.

    Returns:
        The clone directory.
    """
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "Test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.org")
    remote, clone = tmp_path / "remote.git", tmp_path / "clone"
    Shell(tmp_path).run("git", "init", "-q", "--bare", "-b", "main", str(remote))
    Shell(tmp_path).run("git", "init", "-q", "-b", "main", str(clone))
    git = Shell(clone)
    _write_version(clone, "0.1.0")
    git.run("git", "add", "-A")
    git.run("git", "commit", "-q", "-m", "Release 0.1.0")
    git.run("git", "remote", "add", "origin", str(remote))
    git.run("git", "tag", "-a", "v0.1.0", "-m", "scanbench 0.1.0")
    git.run("git", "push", "-q", "-u", "origin", "main", "v0.1.0")
    git.run("git", "switch", "-q", "-c", "develop")
    git.run("git", "push", "-q", "-u", "origin", "develop")
    return clone


def _repo(clone: Path) -> tuple[GitRepo, GitVersions, Shell]:
    """Create the adapters for a clone.

    Args:
        clone: Clone directory.

    Returns:
        Repository adapter, version reader and shell.
    """
    shell = Shell(clone)
    versions = GitVersions(shell)
    return GitRepo(shell, versions), versions, shell


def test_versions(clone: Path) -> None:
    """Released tag, checked-out line and line on another ref are read.

    Args:
        clone: Prepared clone.
    """
    repo, versions, _ = _repo(clone)
    repo.fetch()
    assert repo.has_remote()
    assert repo.root == clone
    assert versions.released_version() == Version(0, 1, 0)
    assert versions.version_line() == Version(0, 1, 0)
    assert versions.version_on("origin/main") == Version(0, 1, 0)
    assert versions.version_on("origin/missing") is None


def test_missing_version_line(clone: Path) -> None:
    """A file without version line is an error.

    Args:
        clone: Prepared clone.
    """
    (clone / INIT).write_text("x = 1\n", encoding="utf-8")
    with pytest.raises(UpdateError):
        _repo(clone)[1].version_line()


def test_branch_patch_tag_push(clone: Path, tmp_path: Path) -> None:
    """A hotfix branch gets a patch, is tagged, pushed and deleted.

    Args:
        clone: Prepared clone.
        tmp_path: Temporary directory for the patch files.
    """
    repo, versions, shell = _repo(clone)
    repo.switch("main")
    repo.pull()
    repo.switch("work", start="main")
    _write_version(clone, "0.1.1")
    shell.run("git", "commit", "-q", "-am", "Release 0.1.1")
    shell.run("git", "format-patch", "-q", "-1", "-o", str(tmp_path / "p"))
    patches = sorted((tmp_path / "p").glob("*.patch"))
    shell.run("git", "reset", "-q", "--hard", "main")
    repo.apply(patches)
    assert versions.version_line() == Version(0, 1, 1)
    with pytest.raises(UpdateError, match="not 0.2.0"):
        repo.tag(Version(0, 2, 0))
    repo.tag(Version(0, 1, 1))
    repo.tag(Version(0, 1, 1))
    repo.push("v0.1.1")
    repo.push("work")
    assert versions.released_version() == Version(0, 1, 1)
    repo.switch("work", start="main")
    repo.switch("main")
    repo.delete_branch("work")
    assert not shell.run("git", "rev-parse", "--verify", "-q", "refs/heads/work",
                         check=False).ok


def test_failing_patch_is_aborted(clone: Path, tmp_path: Path) -> None:
    """A patch that does not apply leaves no half-applied state.

    Args:
        clone: Prepared clone.
        tmp_path: Temporary directory for the broken patch.
    """
    repo, _, shell = _repo(clone)
    broken = tmp_path / "broken.patch"
    broken.write_text("not a patch\n", encoding="utf-8")
    with pytest.raises(UpdateError, match="do not apply"):
        repo.apply([broken])
    assert not (clone / ".git" / "rebase-apply").exists()
    assert shell.run("git", "status", "--porcelain").stdout == ""
