# CI on GitHub Actions

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

Workflow file: [`.github/workflows/quality-gates.yml`](../../.github/workflows/quality-gates.yml),
workflow name `quality-gates`.

## What runs when

~~~mermaid
flowchart LR
  F[push feature/x] -->|pre-push hook| L[tools/check.sh, local]
  L --> PR[pull request into develop or main]
  PR --> G["job gates: Python 3.12, one step per gate"]
  G -->|green and up to date| M[merge]
  M --> T[tag vX.Y.Z on main]
  T --> GM["job gates-matrix: 3.12, 3.13, 3.14"]
  GM --> RC["job release-check: tag on main, tag = version"]
~~~

| Event | Jobs | Purpose |
|---|---|---|
| pull request into `main` or `develop` | `gates` | required check; merge only when green |
| push of a tag `v*` | `gates-matrix`, `release-check` | release gate |
| push of a branch | none | covered by its pull request |
| manual start | `gates` | branch without a pull request: `gh workflow run quality-gates --ref BRANCH` |

Why one Python version per pull request: the lowest supported version (3.12)
catches code that uses newer language features; the full matrix runs once per
release. Matrix jobs run in parallel on GitHub-hosted runners (up to 20
concurrent jobs on the Free plan), so the tag run takes about as long as its
slowest job.

## Stages on the run page

The job `gates` has one step per gate, named `[0] privacy` to `[5] tests`,
so the run page shows which gate failed without opening a log. The step
`job summary` writes the stage table to the run's summary page.

## Branch protection

Set once after the first pull request has run, by the repository owner (normal
user; `gh` acts with the owner's GitHub token, no local privilege involved):

~~~bash
for branch in develop main; do
gh api -X PUT "repos/peddanet/scanbench/branches/$branch/protection" --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["gates"] },
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
done
~~~

| Field | Effect |
|---|---|
| `contexts: ["gates"]` | the pull-request job must be green; the tag matrix is not a merge condition, so changing the matrix never locks merges |
| `strict` | the branch must contain the newest commit of its base ("Update branch") |
| `enforce_admins` | the rules apply to the owner too; never merge with `--admin` |
| review count 0 | a pull request is required, a second approval is not (single maintainer) |

In the repository settings also disable squash and rebase merging, so merges
keep all commits.
