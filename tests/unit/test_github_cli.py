"""Tests for GitHubCli with a scripted shell."""

import json

import pytest
from fakes import FakeShell, failed, ok

from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.github_cli import PROTECTION, GitHubCli

PR = "https://github.com/o/r/pull/7"


def _gh(script: dict[tuple[str, ...], list[object]]) -> tuple[GitHubCli, FakeShell]:
    """Create the adapter on a scripted shell.

    Args:
        script: Results per command prefix.

    Returns:
        Adapter and shell.
    """
    shell = FakeShell(script=script)  # type: ignore[arg-type]
    return GitHubCli(shell, lambda _s: None), shell


def test_open_pr_reuses_or_creates() -> None:
    """An open pull request is reused; otherwise a new one is created."""
    gh, _ = _gh({("gh", "pr", "list"): [ok(json.dumps([{"url": PR}]))]})
    assert gh.open_pr("main", "hotfix/1.0.0", "Release 1.0.0") == PR
    gh, shell = _gh({("gh", "pr", "list"): [ok("[]")],
                     ("gh", "pr", "create"): [ok(f"Creating...\n{PR}\n")]})
    assert gh.open_pr("main", "hotfix/1.0.0", "Release 1.0.0") == PR
    assert shell.calls[-1][:3] == ("gh", "pr", "create")


def test_wait_checks_retries_until_checks_exist() -> None:
    """'no checks reported' is retried; a green watch returns."""
    gh, shell = _gh({("gh", "pr", "checks"): [failed("no checks reported"), ok()]})
    gh.wait_checks(PR)
    assert len(shell.calls) == 2


def test_wait_checks_failures() -> None:
    """A red check fails at once; checks that never appear fail at the end."""
    gh, _ = _gh({("gh", "pr", "checks"): [failed("1 failing")]})
    with pytest.raises(UpdateError, match="CI failed"):
        gh.wait_checks(PR)
    gh, _ = _gh({("gh", "pr", "checks"): [failed("no checks reported")]})
    with pytest.raises(UpdateError, match="no CI checks"):
        gh.wait_checks(PR)


def test_merge_only_when_open() -> None:
    """A merged pull request is not merged again."""
    gh, shell = _gh({("gh", "pr", "view"): [ok("MERGED\n")]})
    gh.merge(PR)
    assert not any(call[:3] == ("gh", "pr", "merge") for call in shell.calls)
    gh, shell = _gh({("gh", "pr", "view"): [ok("OPEN\n")]})
    gh.merge(PR)
    assert shell.calls[-1] == ("gh", "pr", "merge", PR, "--merge", "--delete-branch")


def test_wait_run() -> None:
    """The newest run is watched; red runs and missing runs fail."""
    run = ok(json.dumps([{"databaseId": 42, "url": "https://run/42"}]))
    gh, shell = _gh({("gh", "run", "list"): [ok("[]"), run]})
    assert gh.wait_run("v1.0.0", "push") == "https://run/42"
    assert shell.calls[-1] == ("gh", "run", "watch", "42", "--exit-status")
    gh, _ = _gh({("gh", "run", "list"): [run], ("gh", "run", "watch"): [failed()]})
    with pytest.raises(UpdateError, match="CI run failed"):
        gh.wait_run("v1.0.0", "push")
    gh, _ = _gh({("gh", "run", "list"): [ok("[]")]})
    with pytest.raises(UpdateError, match="no CI run"):
        gh.wait_run("develop", "workflow_dispatch")


def test_repository_commands() -> None:
    """Create, configure, protect, dispatch and update-branch send the right calls."""
    gh, shell = _gh({})
    gh.create_repo("o/r", "desc")
    gh.configure_repo("o/r")
    gh.protect("o/r", "main")
    gh.dispatch("develop")
    gh.update_branch(PR)
    assert shell.calls[0][:4] == ("gh", "repo", "create", "o/r")
    assert "--enable-squash-merge=false" in shell.calls[1]
    assert shell.calls[2][-3:] == ("repos/o/r/branches/main/protection", "--input", "-")
    assert json.loads(shell.stdin[2] or "{}") == PROTECTION
    assert shell.calls[3] == ("gh", "workflow", "run", "quality-gates", "--ref", "develop")
    assert shell.calls[4] == ("gh", "pr", "update-branch", PR)
