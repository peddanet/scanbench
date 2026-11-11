"""GitHub operations through the GitHub CLI ``gh``."""

import json
from collections.abc import Callable

from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell

WORKFLOW = "quality-gates"
"""Name of the CI workflow in ``.github/workflows/quality-gates.yml``."""

PROTECTION = {
    "required_status_checks": {"strict": True, "contexts": ["gates"]},
    "enforce_admins": True,
    "required_pull_request_reviews": {"required_approving_review_count": 0},
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
}
"""Branch protection of ``main`` and ``develop`` (see docs/developer/ci.md)."""


class GitHubCli:
    """Adapter for pull requests, CI runs and repository settings.

    ``gh`` acts with the GitHub login of the user; no local privilege is
    involved. Reading calls are retried, writing calls are made idempotent by
    checking the current state first.
    """

    def __init__(self, shell: Shell, sleep: Callable[[float], None]) -> None:
        """Store the shell and the pause function.

        Args:
            shell: Shell whose working directory is the clone.
            sleep: Pause function used while waiting for GitHub.
        """
        self._shell = shell
        self._sleep = sleep

    def open_pr(self, base: str, head: str, title: str) -> str:
        """Return the open pull request of ``head``, creating it if needed.

        Args:
            base: Target branch.
            head: Source branch.
            title: Title of a new pull request.

        Returns:
            URL of the pull request.
        """
        found = self._shell.read("gh", "pr", "list", "--head", head, "--base", base,
                                 "--state", "open", "--json", "url").stdout
        existing = json.loads(found or "[]")
        if existing:
            return str(existing[0]["url"])
        created = self._shell.run("gh", "pr", "create", "--base", base, "--head", head,
                                  "--title", title, "--body", f"{title} (scanbench update)")
        return created.stdout.strip().splitlines()[-1]

    def wait_checks(self, url: str) -> None:
        """Wait until all checks of a pull request are finished and green.

        GitHub needs some seconds to register the checks of a new pull
        request; until then ``gh pr checks`` reports none, so this is retried.

        Args:
            url: Pull request URL.

        Raises:
            UpdateError: If a check fails or no check appears.
        """
        for _ in range(10):
            self._sleep(15)
            result = self._shell.run("gh", "pr", "checks", url, "--watch", "--interval",
                                     "10", check=False)
            if result.ok:
                return
            if "no checks" not in (result.stdout + result.stderr).lower():
                raise UpdateError(f"CI failed for {url}")
        raise UpdateError(f"no CI checks appeared for {url}")

    def merge(self, url: str) -> None:
        """Merge a pull request with a merge commit, unless already merged.

        Args:
            url: Pull request URL.
        """
        state = self._shell.read("gh", "pr", "view", url, "--json", "state",
                                 "--jq", ".state").stdout.strip()
        if state != "MERGED":
            self._shell.run("gh", "pr", "merge", url, "--merge", "--delete-branch")

    def update_branch(self, url: str) -> None:
        """Bring the pull request branch up to date with its base (``strict``).

        Args:
            url: Pull request URL.
        """
        self._shell.run("gh", "pr", "update-branch", url, check=False)

    def wait_run(self, ref: str, event: str) -> str:
        """Wait for the newest workflow run of a ref and event to succeed.

        Args:
            ref: Branch or tag name, e.g. ``v0.2.0``.
            event: Trigger, ``push`` or ``workflow_dispatch``.

        Returns:
            URL of the run.

        Raises:
            UpdateError: If no run appears or the run fails.
        """
        for _ in range(12):
            self._sleep(10)
            listed = self._shell.read("gh", "run", "list", "--workflow", WORKFLOW,
                                      "--branch", ref, "--event", event, "--limit", "1",
                                      "--json", "databaseId,url").stdout
            runs = json.loads(listed or "[]")
            if runs:
                run_id, url = str(runs[0]["databaseId"]), str(runs[0]["url"])
                if not self._shell.run("gh", "run", "watch", run_id, "--exit-status",
                                       check=False).ok:
                    raise UpdateError(f"CI run failed: {url}")
                return url
        raise UpdateError(f"no CI run appeared for {ref} ({event})")

    def dispatch(self, branch: str) -> None:
        """Start the workflow manually on a branch.

        Args:
            branch: Branch to check.
        """
        self._shell.run("gh", "workflow", "run", WORKFLOW, "--ref", branch)

    def create_repo(self, repo: str, description: str) -> None:
        """Create the public repository and register it as ``origin``.

        Args:
            repo: ``OWNER/NAME``.
            description: Short description shown on GitHub.
        """
        self._shell.run("gh", "repo", "create", repo, "--public", "--source=.",
                        "--remote=origin", "--description", description)

    def configure_repo(self, repo: str) -> None:
        """Allow merge commits only and make ``main`` the default branch.

        Args:
            repo: ``OWNER/NAME``.
        """
        self._shell.run("gh", "repo", "edit", repo, "--enable-merge-commit",
                        "--enable-squash-merge=false", "--enable-rebase-merge=false",
                        "--default-branch", "main")

    def protect(self, repo: str, branch: str) -> None:
        """Set the branch protection (idempotent PUT).

        Args:
            repo: ``OWNER/NAME``.
            branch: Branch to protect.
        """
        self._shell.run("gh", "api", "-X", "PUT",
                        f"repos/{repo}/branches/{branch}/protection", "--input", "-",
                        stdin=json.dumps(PROTECTION))
