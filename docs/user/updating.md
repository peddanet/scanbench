# Updating

Back to: [User documentation](README.md) · [Documentation home](../README.md)

## Users: install a newer release

~~~bash
bash ~/Projects/scanbench/install.sh
~~~

Or download `install.sh` again as in the [installation guide](installation.md).
Normal user. Each release is installed into its own venv
(`venvs/X.Y.Z`); the link `venv` is switched to it at the end, in one atomic
step. The active and the previous release are kept, older ones removed.

## A running scanbench switches by itself

An open scanbench window checks every 30 seconds which release the `venv`
link points at. When a newer release appears, it offers to switch:

| Situation | Behaviour |
|---|---|
| update started from this window (menu **scanbench > Update ...**) | switches automatically when the update is done |
| update installed from a terminal or another window | asks "Switch to it now?" |
| a job is running (scan, save, export; from milestone M2) | waits; switches as soon as the job has finished |

Switching starts the new release and closes the old window. Nothing of the
running release is changed during the installation, because the new release
lives in its own venv. A window started from a git clone (source checkout)
never switches.

## Maintainer: release delivered patches with one command

For the maintainer of the GitHub repository. Delivered archives
`scanbench-X.Y.Z-patch.tar.gz` in `~/Downloads` become releases with:

~~~bash
scanbench update
~~~

or from the window: menu **scanbench > Update ...** (runs
`scanbench update --yes` and shows its output live). What happens, per
version, in ascending order:

| Step | Action | Check |
|---|---|---|
| 1 | read the released version from GitHub, list pending archives, ask up to which version | -- |
| 2 | branch `hotfix/X.Y.Z` from `main`, apply the patches (`git am`) | version line must be X.Y.Z |
| 3 | quality gates in the clone's development venv | local, all six gates |
| 4 | push, pull request into `main`, wait, merge | CI 1/3 |
| 5 | tag `vX.Y.Z` on `main`, push the tag | CI 2/3: Python matrix and release check |
| 6 | branch `merge/hotfix-X.Y.Z`, pull request into `develop`, wait, merge | CI 3/3 |
| 7 | after the last version: install it, move the used archives to `<release dir>/releases` | `install.sh` checks the version |

The output uses numbered stages like the quality gates and ends with a table
of all CI runs, also when a step fails. A failed update can simply be started
again: every step checks the current state first and continues where the
previous run stopped. Two updates cannot run at the same time (lock file).

Options:

| Option | Meaning |
|---|---|
| `--yes` | apply all pending archives without asking |
| `--upto X.Y.Z` | apply only up to this version |
| `--clone DIR` | git clone to use (default `$SCANBENCH_CLONE` or `~/Projects/scanbench`) |
| `--downloads DIR` | folder with the archives (default `~/Downloads`) |

Privilege level: normal user. `git` and `gh` act on your clone with your
GitHub login; the installation writes only below your home directory.

## Maintainer: first publication

Once, after the first patch series was applied by hand to a new clone:

~~~bash
scanbench publish
~~~

It runs the gates, creates the public repository `peddanet/scanbench`
(`--repo OWNER/NAME` for another), pushes `main` and `develop`, allows merge
commits only, starts the first CI run, sets the branch protection, tags the
version on `main` and installs it. The individual commands are explained in
[CI](../developer/ci.md) and [release process](../developer/release-process.md).
