"""Tests for HotfixRelease, UpdateService and FirstPublication with fake adapters."""

import io
import tarfile
from contextlib import nullcontext
from pathlib import Path

import pytest
from workflow_fakes import (FakeDev, FakeGit, FakeGitHub, FakeInstaller, FakeVersions,
                            GitState, Log)

from scanbench.application.first_publication import FirstPublication
from scanbench.application.progress import Progress
from scanbench.application.release_context import ReleaseContext
from scanbench.application.update_service import UpdateService
from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.update_error import UpdateError
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.archive_finder import ArchiveFinder


def _archive(folder: Path, version: str) -> Path:
    """Write a delivery archive with one patch.

    Args:
        folder: Download folder.
        version: Version in the file name.

    Returns:
        The archive path.
    """
    path = folder / f"scanbench-{version}-patch.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        data = b"From 0000 Mon Sep 17 00:00:00 2001\n"
        info = tarfile.TarInfo(f"scanbench-{version}-patch/0001-x.patch")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return path


def _context(tmp_path: Path, released: Version | None, active: Version | None,
             fail_checks: bool = False,
             state: GitState | None = None) -> tuple[ReleaseContext, Log, list[str]]:
    """Wire a context of fakes.

    Args:
        tmp_path: Temporary directory.
        released: Released version on GitHub.
        active: Active installed release.
        fail_checks: Make pull-request checks fail.
        state: State of the fake clone (branches, origin), or None for a new one.

    Returns:
        Context, call log and output lines.
    """
    log: Log = []
    out: list[str] = []
    clone = tmp_path / "clone"
    (clone / ".git").mkdir(parents=True, exist_ok=True)
    paths = AppPaths({"SCANBENCH_HOME": str(tmp_path / "sb")}, tmp_path)
    versions = FakeVersions(released, released or Version(0, 1, 0))
    state = state or GitState()
    git = FakeGit(log, versions, clone, state.remote, state)
    ctx = ReleaseContext(paths, git, versions, FakeGitHub(log, fail_checks), FakeDev(log),
                         FakeInstaller(log, paths, active), Progress(out.append))
    return ctx, log, out


def test_update_applies_pending_in_order(tmp_path: Path) -> None:
    """Two archives become two releases; the newest is installed and archived.

    Args:
        tmp_path: Temporary directory of the test.
    """
    downloads = tmp_path / "dl"
    downloads.mkdir()
    for version in ("0.1.1", "0.1.2"):
        _archive(downloads, version)
    ctx, log, out = _context(tmp_path, Version(0, 1, 0), Version(0, 1, 0))
    git = ctx.git
    assert isinstance(git, FakeGit)
    lines = iter([Version(0, 1, 1), Version(0, 1, 2)])

    def choose(pending: list[PatchArchive]) -> list[PatchArchive]:
        """Pass everything and prepare the version the next apply produces.

        Args:
            pending: Pending archives.

        Returns:
            All of them.
        """
        return pending

    original_apply = git.apply

    def apply(patches: list[Path]) -> None:
        """Advance the version line per applied archive.

        Args:
            patches: Patch files.
        """
        git.next_line = next(lines)
        original_apply(patches)

    git.apply = apply  # type: ignore[method-assign]
    status = UpdateService(ctx, ArchiveFinder(downloads), choose, nullcontext()).run()
    assert status == 0, out
    assert log.count("gates") == 2
    assert log.index("tag v0.1.1") < log.index("tag v0.1.2")
    assert "pr merge/hotfix-0.1.2->develop" in log
    assert log[-1] == "install v0.1.2"
    assert not list(downloads.iterdir())
    assert out[-1].startswith("==== DONE: scanbench 0.1.2")


def test_update_nothing_pending_installs_released(tmp_path: Path) -> None:
    """Without archives the released version is installed if not active.

    Args:
        tmp_path: Temporary directory of the test.
    """
    ctx, log, _ = _context(tmp_path, Version(0, 2, 0), Version(0, 1, 0))
    assert UpdateService(ctx, ArchiveFinder(tmp_path), lambda p: p, nullcontext()).run() == 0
    assert log[-1] == "install v0.2.0"


def test_update_resumes_after_merge(tmp_path: Path) -> None:
    """If main and develop already carry the version, only the tag step runs.

    Args:
        tmp_path: Temporary directory of the test.
    """
    _archive(tmp_path, "0.1.1")
    ctx, log, _ = _context(tmp_path, Version(0, 1, 0), Version(0, 1, 1))
    versions = ctx.versions
    assert isinstance(versions, FakeVersions)
    versions.refs = {"origin/main": Version(0, 1, 1), "origin/develop": Version(0, 1, 1)}
    assert UpdateService(ctx, ArchiveFinder(tmp_path), lambda p: p, nullcontext()).run() == 0
    assert "gates" not in log and "tag v0.1.1" in log and "install v0.1.1" not in log


@pytest.mark.parametrize("remote,git_dir", [(False, True), (True, False)])
def test_update_preconditions(tmp_path: Path, remote: bool, git_dir: bool) -> None:
    """A missing clone or remote stops the update with a summary.

    Args:
        tmp_path: Temporary directory of the test.
        remote: Whether origin exists.
        git_dir: Whether the clone has a .git directory.
    """
    ctx, _, out = _context(tmp_path, None, None, state=GitState(remote=remote))
    if not git_dir:
        (ctx.git.root / ".git").rmdir()
    assert UpdateService(ctx, ArchiveFinder(tmp_path), lambda p: p, nullcontext()).run() == 1
    assert out[-1].startswith("==== FAILED")


def test_update_stops_on_red_ci_and_wrong_patch(tmp_path: Path) -> None:
    """Red CI and a patch with the wrong version both stop the update.

    Args:
        tmp_path: Temporary directory of the test.
    """
    _archive(tmp_path, "0.1.1")
    ctx, log, out = _context(tmp_path, Version(0, 1, 0), Version(0, 1, 0), fail_checks=True)
    git = ctx.git
    assert isinstance(git, FakeGit)
    git.next_line = Version(0, 1, 1)
    assert UpdateService(ctx, ArchiveFinder(tmp_path), lambda p: p, nullcontext()).run() == 1
    assert "merge" not in log and "CI failed" in out[-1]
    ctx, log, out = _context(tmp_path, Version(0, 1, 0), Version(0, 1, 0))
    assert UpdateService(ctx, ArchiveFinder(tmp_path), lambda p: p, nullcontext()).run() == 1
    assert "not 0.1.1" in out[-1]


def test_publish_runs_all_steps(tmp_path: Path) -> None:
    """The first publication creates, protects, tags and installs.

    Args:
        tmp_path: Temporary directory of the test.
    """
    ctx, log, out = _context(tmp_path, None, None, state=GitState(remote=False))
    assert FirstPublication(ctx, "o/r").run() == 0
    expected = ["gates", "create o/r", "push main", "push develop", "configure",
                "dispatch develop", "protect main", "tag v0.1.0", "install v0.1.0"]
    positions = [log.index(item) for item in expected]
    assert positions == sorted(positions)
    assert out[-1].startswith("==== DONE: scanbench 0.1.0 published")


def test_publish_reports_failure(tmp_path: Path) -> None:
    """A failing step ends with a FAILED summary.

    Args:
        tmp_path: Temporary directory of the test.
    """
    ctx, _, out = _context(tmp_path, None, Version(0, 1, 0))
    github = ctx.github
    assert isinstance(github, FakeGitHub)

    def broken(ref: str, event: str) -> str:
        """Fail like a red CI run.

        Args:
            ref: Ref.
            event: Event.

        Raises:
            UpdateError: Always.
        """
        raise UpdateError(f"CI run failed for {ref} {event}")

    github.wait_run = broken  # type: ignore[method-assign]
    assert FirstPublication(ctx, "o/r").run() == 1
    assert "CI run failed" in out[-1]


def test_publish_needs_clone(tmp_path: Path) -> None:
    """Without a clone the publication stops with a clear message.

    Args:
        tmp_path: Temporary directory of the test.
    """
    ctx, _, out = _context(tmp_path, None, None, state=GitState(remote=False))
    (ctx.git.root / ".git").rmdir()
    assert FirstPublication(ctx, "o/r").run() == 1
    assert "no git clone" in out[-1]


def test_update_discards_branch_of_another_delivery(tmp_path: Path) -> None:
    """A local hotfix branch from an older delivery is rebuilt; a pushed one stops.

    Args:
        tmp_path: Temporary directory of the test.
    """
    downloads = tmp_path / "dl"
    downloads.mkdir()
    _archive(downloads, "0.1.1")
    (downloads / "scanbench-0.1.0-patch.tar.gz").write_bytes(b"released long ago")
    state = GitState()
    state.branches.add("hotfix/0.1.1")             # left by a failed run
    ctx, log, out = _context(tmp_path, Version(0, 1, 0), Version(0, 1, 0), state=state)
    git = ctx.git
    assert isinstance(git, FakeGit)
    versions = ctx.versions
    assert isinstance(versions, FakeVersions)
    versions.line = Version(0, 1, 1)
    git.next_line = Version(0, 1, 1)
    original_delete = git.delete_branch

    def delete(branch: str) -> None:
        """Delete and fall back to the version of main.

        Args:
            branch: Branch.
        """
        original_delete(branch)
        versions.line = Version(0, 1, 0)

    git.delete_branch = delete  # type: ignore[method-assign]
    assert UpdateService(ctx, ArchiveFinder(downloads), lambda p: p, nullcontext()).run() == 0
    assert log.index("delete hotfix/0.1.1") < log.index("apply 1")
    assert any("discarded local hotfix/0.1.1" in line for line in out)
    assert not list(downloads.iterdir())
    assert (ctx.paths.release.archive_store / "scanbench-0.1.0-patch.tar.gz").exists()

    _archive(downloads, "0.1.2")
    pushed = GitState()
    pushed.branches.add("hotfix/0.1.2")
    pushed.pushed.add("hotfix/0.1.2")
    ctx, log, out = _context(tmp_path, Version(0, 1, 1), Version(0, 1, 1), state=pushed)
    assert UpdateService(ctx, ArchiveFinder(downloads), lambda p: p, nullcontext()).run() == 1
    assert "built from another delivery" in out[-1] and "delete hotfix/0.1.2" not in log
