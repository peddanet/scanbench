# scanbench

Document and photo-album scanning for Linux, built on SANE, Ghostscript and
CUPS. Graphical interface with Qt 6; runs on GNOME, KDE Plasma, COSMIC and
other freedesktop desktops, on Wayland and X11.

> **Status: version 0.2.1, testable draft.** Documents, photo albums and
> printing work. Device profiles, the duplex calibration wizard and album
> export follow; see the [roadmap](docs/concept/README.md#roadmap).

![Photo-album tab: detected photos, the selected frame with its grips](docs/user/img/photo-frame-editor.png)

## Features

| Area | What scanbench does |
|---|---|
| Scanners | every scanner SANE reaches, USB or network (eSCL/WSD through sane-airscan); target device of the first tests: Canon PIXMA MX925 |
| Documents | flatbed or feeder, one or both sides, manual duplex for one-sided feeders; colour, grey, black and white; resolutions as offered by the device; A4, A5, A6, Letter; turn, reorder, delete pages |
| PDF | lossless (img2pdf) or reduced with Ghostscript: screen, e-book, printer, prepress; always from the lossless original |
| Photo albums | scan the full A4 glass once; every photo or postcard is found, also with grey or white borders or turned by 90 degrees; frames snap to 9 x 13, 10 x 15, postcard, 13 x 18 cm |
| Frame editor | click a frame to see size, skew and orientation; drag to move; grips to resize; orange grip to rotate freely (Shift: 0.5° steps); arrow keys and +/-; right-click to turn by 90°, straighten, fit, delete, add |
| Album | after confirmation each photo is straightened and saved as PNG or JPEG with continuing numbers and an `album.json` index |
| Printing | every CUPS printer with all driver options, e.g. photo tray, cassette or CD/DVD tray |
| Updates | each release in its own environment; an open window switches to a new release when no work is pending |

## Installation

~~~bash
sudo apt install sane-utils sane-airscan ghostscript cups-client
curl -fsSLO https://raw.githubusercontent.com/peddanet/scanbench/main/install.sh
less install.sh
bash install.sh
~~~

| Line | What it does | Privilege |
|---|---|---|
| 1 | SANE command line tools, network scanner backend, Ghostscript, CUPS clients | `sudo` from your user context: packages are written below `/usr` |
| 2 | downloads the installer | normal user |
| 3 | lets you read it before running it | normal user |
| 4 | installs the newest release into its own venv below `~/.local/share/scanbench`, links `~/.local/bin/scanbench`, adds the menu entry | normal user: writes only below your home directory |

Other locations: set `SCANBENCH_HOME` and `SCANBENCH_BIN` before step 4
([user guide, section 2.3](docs/user/README.md#23-where-the-installation-goes)).
Package names are those of Debian and Ubuntu (including Pop!_OS).

## Usage

Start **scanbench** from the application menu or with `scanbench` in a
terminal, then:

1. Select the scanner in the bar at the top (**Search scanners** searches again).
2. **Documents:** choose source, colour, resolution, paper; **Scan**; arrange
   the pages; choose the PDF size; **Save PDF ...** or **Print ...**.
3. **Photo album:** put up to four photos on the glass; **Scan page**; check
   and correct the frames; **Confirm**; next page.

Useful commands (normal user):

| Command | Purpose |
|---|---|
| `scanbench doctor` | version, directories, external programs and missing packages |
| `scanbench devices` | scanners with sources, modes and resolutions |
| `scanbench printers` | printers with their driver options |
| `SCANBENCH_TEST_DEVICE=1 scanbench` | try scanbench with SANE's virtual scanner |

## Documentation

This page is the short version. Everything in detail:

| Document | For |
|---|---|
| [User guide](docs/user/README.md) | installation, documents, photo albums, frame editor, printing, updating, troubleshooting |
| [Developer documentation](docs/developer/README.md) | architecture, detection algorithm, frame geometry, printing, threads, coding standard, quality gates, CI, releases |
| [Concept](docs/concept/README.md) | design rationale, requirements, roadmap, open decisions |
| [Documentation home](docs/README.md) | map of all documents |
| [Glossary](docs/glossary.md) | every technical term with a link |
| [Changelog](CHANGELOG.md) | changes per release |

## Updates

`bash install.sh` again installs a newer release; an open window offers the
switch. For the maintainer, `scanbench update` turns delivered patch archives
into releases with all quality gates and CI runs
([user guide, section 8](docs/user/README.md#8-updating)).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). In short: git-flow branches, pull
requests only, all six quality gates green (`tools/check.sh`).

## Licence

Not yet decided (see [decisions](docs/concept/README.md#open-decisions)).
Until a licence file exists, no rights beyond viewing are granted.
