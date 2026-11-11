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
| M1 | scanner adapter, device detection, device profiles, CLI for the seven scan cases | adapter, detection and `scanbench devices` in 0.2.0; device profiles open |
| M2 | document GUI, duplex pipeline, calibration wizard, PDF shrinking | first draft in 0.2.0 (without calibration wizard) |
| M3 | photo-album mode: detection, review with undo, encoders, album loop | first draft in 0.2.0 (without undo); printing through CUPS added; free frame editing in 0.2.1 |
| M4 | export (archive, rclone, folder), complete documentation, release 1.0.0 | planned |

Requested for later releases (not yet scheduled to a milestone):

| Item | Note |
|---|---|
| orientation proposal from the picture content | suggest the 90-degree turn per photo (faces, horizon, text) |
| align a frame to a drawn line | draw along an edge of the photo; the frame takes that angle (0.2.1 has free rotation with a grip and 0.1° keys) |
| PDF collage assistant | several photos and texts on pages, exported as PDF |
| duplex calibration wizard, device profiles | from M1/M2 |
| undo in the frame editor | from M3 |

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
| not in revision 1 | `scanbench update`, `scanbench publish`, versioned venvs and switching of open windows | requested after revision 1; design in [architecture](../developer/update-and-switching.md#update-and-live-switch) |
