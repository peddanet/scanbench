# Developer documentation

Back to: [Documentation home](../README.md)

Lead document of the developer documentation.

| Page | Content |
|---|---|
| [Architecture](architecture.md) | layers, functional units, design patterns, target design |
| [Application core, updates and live switching](update-and-switching.md) | core modules, desktop integration, `scanbench update`/`publish`, safe release switching |
| [Scanner access and documents](scanning-and-documents.md) | SANE adapter, device options, document session, PDF output, manual duplex |
| [Photo album](photo-album.md) | detection algorithm, frame coordinates and editing, cropping, frame editor |
| [Printing](printing.md) | CUPS adapter, print dialog, driver options |
| [GUI structure and threads](gui.md) | workbench, tabs, task runner, work directory, GUI tests |
| [Coding standard](coding-standard.md) | rules and measurable limits enforced by the gates |
| [Quality gates](quality-gates.md) | `tools/check.sh`, the six gates, staged output, pre-push hook |
| [CI](ci.md) | GitHub Actions workflow, what runs when, branch protection |
| [Release process](release-process.md) | git-flow, versions, changelog, tags, patch delivery |
| [Documentation guide](documentation-guide.md) | how this documentation is organised; the lead-document rule |

Related: [Concept](../concept/README.md) (why the design is as it is),
[CONTRIBUTING.md](../../CONTRIBUTING.md), [glossary](../glossary.md).

## Set up a development clone

~~~bash
sudo apt install sane-utils ghostscript
git clone https://github.com/peddanet/scanbench.git ~/Projects/scanbench
cd ~/Projects/scanbench
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
git config core.hooksPath .githooks
tools/check.sh
~~~

| Line | Purpose | Privilege |
|---|---|---|
| 1 | SANE test device and Ghostscript for the integration tests (tests skip without them) | `sudo` from your user context: packages go below `/usr` |
| 2-6 | clone, venv, editable install with the gate tools, pre-push hook, all gates | normal user: everything lives in your home directory; `git config` without `--global` writes only `.git/config` |
