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

## Patch delivery and `scanbench update`

The assistant works in its own clone, commits with the author's GitHub
noreply identity, runs `tools/check.sh`, and delivers `git format-patch`
output as `scanbench-X.Y.Z-patch-N.tar.gz`, always based on the newest
release; N counts the deliveries of one version (1, 2, …), so a corrected
delivery has its own name. (Up to 0.2.4 the name had no N; the update of
0.2.3 and older does not recognise N.) It never pushes.

From 0.3.0 on the archive is built with `tools/make_patch_archive.py`
(normal user, in the repository):

~~~bash
python3 tools/make_patch_archive.py <commit of the previous delivery> <out dir> --build 1
~~~

It writes the patches of `<base>..HEAD` and a file `BASE` with the version of
the base commit. A cumulative delivery (for a user who skipped one) is the
same command with an older base.

The maintainer turns delivered archives into releases with
`scanbench update` (terminal) or the menu **scanbench > Update ...**. The
steps per version are listed in the user documentation,
[user guide, section 8.3](../user/README.md#83-maintainer-release-delivered-patches).
Deliveries go through the hotfix path even for small additions; strictly by
Semantic Versioning some of them are minor increments. This is a deliberate
simplification for a single maintainer.

| Design point | Implementation |
|---|---|
| order | archives are applied strictly in ascending version order; the list is printed first |
| chain | `ArchiveFinder.base` reads `BASE`; `UpdateService._check_chain` requires every archive to follow its named base (the released version or the archive before it) and stops before any change otherwise; archives without `BASE` are not checked |
| choice per version | highest delivery number N, then newest browser copy (`ArchiveFinder.newest_per_version`) |
| corrected delivery | the SHA-256 of the applied archive is stored in the clone's git configuration (`scanbench.hotfix-X-Y-Z`); a local `hotfix/X.Y.Z` built from another archive is deleted and rebuilt, one already on `origin` stops the update |
| tidy download folder | `ArchiveFinder.obsolete`: archives of released versions and older deliveries or copies go to the archive store at the start and the end of each run |
| local gates | run in `<clone>/.venv`, created and refreshed by the update; the push afterwards skips the pre-push hook because the same commit was just checked |
| resumable | each step checks the state first (version on `origin/main`, existing tag, open pull request, merged state) |
| network | reading `git` and `gh` calls are retried 5 times, 10 s apart |
| parallel runs | prevented by an exclusive lock on `<release dir>/update.lock` |
| after the update | newest release installed into its own venv, link switched, archives moved to `<release dir>/releases` |

The equivalent manual commands are the feature-release and tag blocks above.

## First publication: `scanbench publish`

Once, on a fresh clone with the first patch series applied: gates, `gh repo
create`, push `main` and `develop`, merge commits only, first CI run on
`develop` (registers the check `gates`), branch protection, tag on `main`,
installation. Manual equivalent: [CI, branch protection](ci.md#branch-protection)
and the tag block above.
