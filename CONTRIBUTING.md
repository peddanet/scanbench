# Contributing to scanbench

Back to: [README](README.md) · [Developer documentation](docs/developer/README.md)

1. **Branches:** git-flow. Work on `feature/<name>` from `develop`; releases on
   `release/X.Y.Z`, urgent fixes on `hotfix/X.Y.Z` from `main`.
   Details: [release process](docs/developer/release-process.md).
2. **Gates:** activate the pre-push hook once per clone and keep all seven
   gates green: [quality gates](docs/developer/quality-gates.md).
3. **Code:** follow the [coding standard](docs/developer/coding-standard.md):
   one class per module, Google-style docstrings, type hints, limits enforced
   by pylint.
4. **Documentation:** every change that users or developers notice updates the
   documentation in the same pull request, following the
   [documentation guide](docs/developer/documentation-guide.md).
5. **Changelog:** add a line under `## [Unreleased]` in `CHANGELOG.md`.
6. **Privacy:** no real device addresses, host names, user names or album
   names in code, documentation or commit messages; such values live in local
   configuration files.

## Local files of a developer

A fresh clone is enough to develop, test, release and install scanbench.
Files that hold private or machine-specific data live outside the clone and
never in the repository; each has a sample with invented content in
[`examples/`](examples/). Where the folders `.config`, `.local/state`,
`.local/share` and `.cache` come from and what `SCANBENCH_HOME` changes:
[user guide, section 3](docs/user/README.md#3-starting-commands-and-files).

| Path on the machine | Written by | Sample in the repository | Needed for |
|---|---|---|---|
| `~/.config/scanbench/privacy/denylist.txt` | you (mode 600) | `examples/privacy/denylist.sample.txt` | gate `[0] privacy`: terms that must never appear |
| `~/.config/scanbench/privacy/allowlist.txt` | you (mode 600) | `examples/privacy/allowlist.sample.txt` | gate `[0] privacy`: accepted non-no-reply identities |
| `~/.config/scanbench/settings.toml` | scanbench (Settings, "Save as default") | `examples/settings.toml.sample` | saved defaults of all options |
| `~/.config/scanbench/presets/<tab>-<name>.toml` | scanbench ("Save as preset") | `examples/presets/photos-album-600-dpi-png.toml.sample` | named presets per tab |
| `~/.cache/scanbench/devices.json` | scanbench | none (rebuilt on the next start) | scanners and their options |
| `~/.local/state/scanbench/logs/` | scanbench | none (log files) | troubleshooting |
| `~/.local/share/scanbench/` | `install.sh`, `scanbench update` | none (installed releases, sessions) | running the installed release |
| `.venv/`, `.gates/`, `.git/checked-trees` in the clone | you, `tools/check.sh` | none (ignored by git) | development venv, gate logs, check cache |

With `SCANBENCH_HOME` set, configuration, logs, cache and sessions move below
that folder (user guide, section 3); the privacy lists are also still read
from the older name `$SCANBENCH_HOME/privacy/deny.txt`, with a hint to rename.

Create the privacy lists once per machine (normal user; `cp -n` never
overwrites an existing list, `chmod 600` makes them readable for you only),
then replace the invented entries by your own:

~~~bash
mkdir -p ~/.config/scanbench/privacy && \
cp -n examples/privacy/denylist.sample.txt ~/.config/scanbench/privacy/denylist.txt && \
cp -n examples/privacy/allowlist.sample.txt ~/.config/scanbench/privacy/allowlist.txt && \
chmod 600 ~/.config/scanbench/privacy/denylist.txt ~/.config/scanbench/privacy/allowlist.txt
~~~

Images: the program icon is `src/scanbench/data/scanbench.svg` (package
data, installed by `scanbench install-desktop`); the GitHub social preview is
`docs/images/social-preview.png`, rendered from `social-preview.svg` with
`python3 tools/social_preview.py` and uploaded under the repository's
Settings > Social preview.
