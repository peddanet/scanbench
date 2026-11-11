# Contributing to scanbench

Back to: [README](README.md) · [Developer documentation](docs/developer/README.md)

1. **Branches:** git-flow. Work on `feature/<name>` from `develop`; releases on
   `release/X.Y.Z`, urgent fixes on `hotfix/X.Y.Z` from `main`.
   Details: [release process](docs/developer/release-process.md).
2. **Gates:** activate the pre-push hook once per clone and keep all six gates
   green: [quality gates](docs/developer/quality-gates.md).
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
