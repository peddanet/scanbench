# Concept

Back to: [Documentation home](../README.md)

Lead document of the design documents.

| Document | Content |
|---|---|
| [scanbench-concept.md](scanbench-concept.md) | concept revision 1 (source): input review, requirements, technology decisions, architecture, document and photo scanning, gates, CI, milestones, risks, glossary, sources |
| [scanbench-concept.pdf](scanbench-concept.pdf) | the same as PDF |
| [diagrams/](diagrams) | Mermaid sources of all concept diagrams |
| [img/](img) | rendered diagrams used by the concept |

## Revisions

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-11 | first version. Repository copy: the real IP address of the author's scanner in chapter 2.3 (W4) is replaced by a description, as the privacy rule requires |

## Roadmap

| Milestone | Content | State |
|---|---|---|
| M0 | repository skeleton, gates, staged runner, CI, desktop entry, empty window; update and publish workflows with live release switching | done in 0.1.0 |
| M1 | scanner adapter, device detection, device profiles, CLI for the seven scan cases | planned |
| M2 | document GUI, duplex pipeline, calibration wizard, PDF shrinking | planned |
| M3 | photo-album mode: detection, review with undo, encoders, album loop | planned |
| M4 | export (archive, rclone, folder), complete documentation, release 1.0.0 | planned |

## Open decisions

| # | Question | State in 0.1.0 |
|---|---|---|
| D1 | project name | working title "scanbench" used; availability on GitHub and PyPI not checked |
| D2 | licence | open; no licence file yet |
| D3 | UI language | English, as proposed |
| D4 | minimum Python | 3.12, as proposed |
| D5 | default paths | XDG, `SCANBENCH_HOME` for a single root, as proposed |
| D6 | keep raw album scans | not yet relevant (M3) |

## Implementation notes on revision 1

Deviations of release 0.1.0 from the concept text; the concept itself stays
unchanged as the record of the design decision.

| Concept | Implementation | Reason |
|---|---|---|
| `tools/summary.py` | `tools/gate_summary.py` | name says what it summarises |
| CI installs `sane-utils ghostscript` | CI installs Qt system libraries only | M0 has no SANE or Ghostscript tests yet; SANE test-backend tests come with M1 |
| pylint defaults "from memory" | defaults confirmed with `pylint --generate-toml-config`, pylint 4.1.3 | open point of the concept closed |
| package name `sane-airscan` to verify | confirmed for Ubuntu 24.04 (noble, main) on Launchpad | open point of the concept closed |
| dependency `PySide6` | `PySide6-Essentials` | contains QtCore, QtGui, QtWidgets; the add-on modules are not needed |
| not in revision 1 | `scanbench update`, `scanbench publish`, versioned venvs and switching of open windows | requested after revision 1; design in [architecture](../developer/architecture.md#update-and-live-switch) |
