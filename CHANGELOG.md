# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning 2.0.0](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-11

### Added

- Milestone M0: repository skeleton with the layers domain, application,
  infrastructure and ui.
- Main window with placeholder tabs "Documents" and "Photo album"; version in
  the status bar, marked when run from a source checkout.
- Command line: `scanbench`, `scanbench doctor`, `scanbench install-desktop`,
  `scanbench uninstall-desktop`, `scanbench --version`.
- Per-user desktop entry and icon; Wayland app ID `io.github.peddanet.scanbench`.
- XDG directory layout, single-root layout via `SCANBENCH_HOME`.
- Six quality gates in `tools/check.sh` with numbered stages, log directory,
  `--fast`, `--full`, `--json`, `--only`; pre-push hook.
- GitHub Actions workflow: one Python version per pull request, matrix
  3.12/3.13/3.14 and release check on tags.
- `install.sh`: installation from a release tag into a venv.

### Documentation

- Documentation tree with lead documents for user, developer and concept
  documentation; concept revision 1 with diagrams.
