# Release process

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

## Versions and changelog

* Semantic Versioning: `MAJOR.MINOR.PATCH`.
* The version exists once, in `src/scanbench/__init__.py`
  (`__version__ = "X.Y.Z"`); `pyproject.toml` reads it at build time.
* `CHANGELOG.md` follows Keep a Changelog; work in progress collects under
  `## [Unreleased]`.
* A release is an annotated tag `vX.Y.Z` on `main`. The CI job
  `release-check` fails if the tagged commit is not on `main` or the tag does
  not match `__version__`; `install.sh` refuses an installation whose
  reported version differs from the tag.

## Branches (git-flow)

| Branch | Purpose | From | Into |
|---|---|---|---|
| `main` | released states only, each tagged | -- | -- |
| `develop` | integration | `main` | `main` via release branch |
| `feature/<name>` | one feature or fix | `develop` | `develop` (pull request) |
| `release/X.Y.Z` | version, changelog, documentation | `develop` | `main` (pull request) |
| `hotfix/X.Y.Z` | urgent fix of a release | `main` | `main` and `develop` |

Merges keep all commits (merge commits); squash and rebase merging are
disabled on GitHub. The integrator (repository owner) merges and tags.

## Feature cycle

~~~bash
git switch develop && git pull --ff-only && git switch -c feature/NAME
tools/check.sh
git push -u origin feature/NAME
pr=$(gh pr create --base develop --fill)
sleep 30 && gh pr checks "$pr" --watch && gh pr merge "$pr" --merge --delete-branch \
  && git switch develop && git pull --ff-only
~~~

`pr=$(...)` keeps the URL of the new pull request; `sleep 30` gives GitHub
time to register the checks, otherwise `--watch` reports "no checks". All
commands as normal user; `gh` acts with your GitHub login.

## Feature release

~~~bash
git switch develop && git pull --ff-only && git switch -c release/X.Y.Z
# set __version__, move [Unreleased] to "## [X.Y.Z] - YYYY-MM-DD", update docs
tools/check.sh && git commit -am "Release X.Y.Z" && git push -u origin release/X.Y.Z
pr=$(gh pr create --base main --title "Release X.Y.Z" --fill)
sleep 30 && gh pr checks "$pr" --watch && gh pr merge "$pr" --merge --delete-branch
~~~

Tag and back-merge:

~~~bash
git switch main && git pull --ff-only \
  && grep -q '^__version__ = "X.Y.Z"$' src/scanbench/__init__.py \
  && git tag -a vX.Y.Z -m "scanbench X.Y.Z" && git push origin vX.Y.Z
git switch develop && pr=$(gh pr create --base develop --head main \
  --title "Merge release X.Y.Z into develop" --body "Back-merge of release X.Y.Z.") \
  && sleep 30 && gh pr checks "$pr" --watch && gh pr merge "$pr" --merge \
  && git pull --ff-only
~~~

The `grep -q` guard makes the tag impossible if the version line does not
match.

## Patch delivery by the assistant

The assistant works in its own clone, commits with the author's GitHub
noreply identity, runs `tools/check.sh`, and delivers `git format-patch`
output as `scanbench-X.Y.Z-patch.tar.gz`. It never pushes. The owner applies
the series on a feature or hotfix branch with `git am` and opens the pull
request. A generic `scanbench update` command that automates this (as in
mediatools) is planned once releases exist.

## First publication (once)

How release 0.1.0 was brought to GitHub is described in the delivery notes of
that release; afterwards the normal cycle above applies. Branch protection:
[CI](ci.md#branch-protection).
