# Developer documentation

Back to: [Documentation home](../README.md)

Lead document of the developer documentation.

| Page | Content |
|---|---|
| [Architecture](architecture.md) | layers, modules of the current release, patterns, target design |
| [Coding standard](coding-standard.md) | rules and measurable limits enforced by the gates |
| [Quality gates](quality-gates.md) | `tools/check.sh`, the six gates, staged output, pre-push hook |
| [CI](ci.md) | GitHub Actions workflow, what runs when, branch protection |
| [Release process](release-process.md) | git-flow, versions, changelog, tags, patch delivery |
| [Documentation guide](documentation-guide.md) | how this documentation is organised; the lead-document rule |

Related: [Concept](../concept/README.md) (why the design is as it is),
[CONTRIBUTING.md](../../CONTRIBUTING.md), [glossary](../glossary.md).

## Set up a development clone

~~~bash
git clone https://github.com/peddanet/scanbench.git ~/Projects/scanbench
cd ~/Projects/scanbench
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
git config core.hooksPath .githooks
tools/check.sh
~~~

All as normal user: the clone and the venv live in your home directory;
`git config` without `--global` writes only `.git/config` of this clone.
`pip install -e` installs the package in editable mode, so code changes are
active without reinstalling; `.[dev]` adds the gate tools.
