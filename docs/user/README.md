# scanbench user guide

Back to: [Documentation home](../README.md)

The complete user documentation in one page. Terms are explained in the
[glossary](../glossary.md).

## Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Starting, commands and files](#3-starting-commands-and-files)
4. [Choosing the scanner](#4-choosing-the-scanner)
5. [Scanning documents](#5-scanning-documents)
6. [Scanning photo albums](#6-scanning-photo-albums)
7. [Printing](#7-printing)
8. [Updating](#8-updating)
9. [Troubleshooting](#9-troubleshooting)
10. [References](#10-references)

## 1. Overview

| Tab or function | What it does |
|---|---|
| Documents | scan from flatbed or feeder, one or both sides; arrange pages; save as PDF in five sizes; print |
| Photo album | scan the full A4 glass; find every photo; check and correct the frames; save each photo straightened as PNG or JPEG; print |
| Printing | every CUPS printer with all options of its driver, e.g. photo tray or CD/DVD tray |
| Updates | every release in its own environment; an open window switches when it is idle |

![Photo-album tab with a selected frame and its grips](img/photo-frame-editor.png)

The screenshots show the real program with simulated scanner input from
copyright-free sample photos ([sources](img/samples/SOURCES.md)).

## 2. Installation

scanbench installs per user into its own virtual environment. Only the system
packages need administrator rights.

### 2.1 System packages

~~~bash
sudo apt install sane-utils sane-airscan ghostscript cups-client
~~~

| Package | Provides | Needed for |
|---|---|---|
| `sane-utils` | `scanimage`, the SANE command line program scanbench calls | scanning (required) |
| `sane-airscan` | SANE backend for network scanners (eSCL, WSD) | network scanners |
| `ghostscript` | `gs` | reduced PDF sizes (optional; without it only lossless PDFs) |
| `cups-client` | `lp`, `lpstat`, `lpoptions` | printing (optional; usually installed) |

Privilege: `sudo` from your user context, because packages are written below
`/usr`; a root shell is not needed. Package names are those of Debian and
Ubuntu (including Pop!_OS). The Python libraries (Qt, OpenCV, NumPy, Pillow,
img2pdf) come with `install.sh` into the release environment.

### 2.2 Install a release

~~~bash
curl -fsSLO https://raw.githubusercontent.com/peddanet/scanbench/main/install.sh
less install.sh
bash install.sh
~~~

| Line | What it does | Privilege |
|---|---|---|
| 1 | downloads the installer; `-f` fail on HTTP errors, `-sS` quiet but show errors, `-L` follow redirects, `-O` keep the file name | normal user |
| 2 | lets you read the script before running it | normal user |
| 3 | finds the newest release tag, creates `venvs/X.Y.Z`, installs, checks the version, switches the link `venv`, links the launcher, adds the desktop entry | normal user; writes only below your home directory |

A specific release: `bash install.sh v0.2.1`.

### 2.3 Where the installation goes

| Variable | Default | Meaning |
|---|---|---|
| `SCANBENCH_HOME` | `~/.local/share/scanbench` | root of the installation; if set, configuration, logs and cache move below it too |
| `SCANBENCH_BIN` | `~/.local/bin` | directory of the `scanbench` launcher link |

Everything in one folder below `~/scripts`:

~~~bash
export SCANBENCH_HOME=~/scripts/scanbench.d SCANBENCH_BIN=~/scripts
bash install.sh
~~~

Put the `export` line into `~/.profile` as well. The launcher entry in the
application menu carries both values itself, because programs started from
the menu do not necessarily see `~/.profile`.

### 2.4 Launcher entry

`install.sh` runs `scanbench install-desktop`, which writes
`~/.local/share/applications/io.github.peddanet.scanbench.desktop` and the
icon `~/.local/share/icons/hicolor/scalable/apps/io.github.peddanet.scanbench.svg`.
The entry starts `<installation>/venv/bin/scanbench`, a link that stays valid
across releases. `scanbench uninstall-desktop` removes both files.

### 2.5 Uninstall

~~~bash
scanbench uninstall-desktop
rm -r ~/.local/share/scanbench
rm ~/.local/bin/scanbench
~~~

Normal user, everything is in your home directory. Adjust the paths if you
set `SCANBENCH_HOME` or `SCANBENCH_BIN`. Settings in `~/.config/scanbench`
stay unless you delete them too.

## 3. Starting, commands and files

Start from the application menu, or with `scanbench` in a terminal. The status
bar shows the version; **scanbench > About scanbench** shows it as well.

| Command | Purpose |
|---|---|
| `scanbench` or `scanbench gui` | start the graphical interface |
| `scanbench doctor` | version, directories, external programs; exit status 1 if a required program is missing |
| `scanbench devices [--test]` | scanners with sources, modes, resolutions; `--test` adds SANE's virtual scanner |
| `scanbench printers` | CUPS printers, the default printer, driver options |
| `scanbench install-desktop` / `uninstall-desktop` | add or remove the launcher entry |
| `scanbench update` | maintainer: turn delivered patch archives into releases ([section 8.3](#83-maintainer-release-delivered-patches)) |
| `scanbench publish` | maintainer: first publication on GitHub |
| `scanbench --version` | print the version |

All commands run as normal user.

| Content | Default | With `SCANBENCH_HOME` |
|---|---|---|
| Settings (album folder) | `~/.config/scanbench` | `$SCANBENCH_HOME/config` |
| Logs | `~/.local/state/scanbench/logs` | `$SCANBENCH_HOME/logs` |
| Raw scans of the running session, deleted on exit | `~/.cache/scanbench/session-*` | `$SCANBENCH_HOME/cache/session-*` |
| Installed releases | `~/.local/share/scanbench/venvs/X.Y.Z`, active one linked as `venv` | `$SCANBENCH_HOME/venvs/X.Y.Z` |
| Applied patch archives | `~/.local/share/scanbench/releases` | `$SCANBENCH_HOME/releases` |

## 4. Choosing the scanner

The bar above the tabs lists every scanner SANE can reach. scanbench searches
once at start; **Search scanners** searches again (network scanners can take a
few seconds). Sources, colour modes and resolutions in both tabs follow the
selected scanner.

Without hardware, try SANE's virtual scanner (normal user, this start only):

~~~bash
SCANBENCH_TEST_DEVICE=1 scanbench
~~~

## 5. Scanning documents

![Documents tab](img/documents-tab.png)

### 5.1 Settings

| Setting | Choices | Notes |
|---|---|---|
| Source | Flatbed · Feeder, one side · Feeder, both sides | only what the scanner offers |
| Colour | Color · Gray · Black and white | black and white (line art) gives the smallest files for text |
| Resolution | as offered, e.g. 75 to 1200 dpi | 300 dpi for documents, 150 dpi for screen reading |
| Paper | A4 · A5 · A6 · Letter | limited to the scanner's maximum area |

### 5.2 Scan and arrange

| Action | How |
|---|---|
| scan | **Scan**: one page from the flatbed, or every sheet in the feeder |
| more pages | **Scan** again; new pages are appended |
| turn a page | select it, **Rotate left/right**, or right-click: 90°, 180° |
| reorder | **Move up / Move down** |
| remove | **Delete page** or right-click > Delete page |
| start over | **Start new document** |

Rotations are applied when saving, so editing never degrades the scan.

**Two-sided without a duplex feeder (manual duplex):** scan the stack, turn it
over without re-sorting, scan again, then **Merge fronts + backs**. The runs
are interleaved into reading order; both must have the same number of sheets.

### 5.3 Save as PDF

| PDF size | Ghostscript preset | Typical use |
|---|---|---|
| Original (lossless) | none | archive; pages embedded unchanged with img2pdf |
| Screen (72 dpi) | `/screen` | smallest file, screen only |
| E-book (150 dpi) | `/ebook` | e-mail, reading on screen (default) |
| Printer (300 dpi) | `/printer` | printing |
| Prepress (300 dpi, best) | `/prepress` | printing with the highest quality |

Every reduced size is made from the lossless original. If a reduction would
not be smaller (possible with black-and-white pages), the lossless file is
kept. **Print ...** prints the lossless pages ([section 7](#7-printing)).

## 6. Scanning photo albums

### 6.1 Placing the photos

- Up to four photos fit on the A4 glass, e.g. three 10 x 15 cm landscape
  photos and one portrait photo, or three postcards.
- Leave a few millimetres between the photos.
- Skewed or 90-degree turned photos are detected. Close the lid.

### 6.2 Settings

| Setting | Default | Notes |
|---|---|---|
| Colour | Color | Gray for black-and-white photos |
| Resolution | 600 dpi | 300 dpi for small prints, 600 dpi for archiving |
| Format | PNG (lossless) | JPEG (quality 92) is about a tenth of the size |
| Album | `~/Pictures/scanbench-album` | remembered across restarts |
| Fit frames to photo sizes | on | frames within 6 % of 9 x 13, 10 x 15, postcard A6 or 13 x 18 cm get exactly that size |
| Keep full-page scans | off | also stores the whole page in `scans/` |

The scan always covers the whole A4 frame, the largest possible photo frame.

### 6.3 Check and correct the frames

After **Scan page** every found photo has a blue frame with its number and an
arrow pointing to the side that becomes the top.

| You want to | Do this |
|---|---|
| see the values of a frame | click it; the line below the preview shows size, skew and orientation, e.g. `Frame 2: 100 x 70 mm, skew -0.8°, saved as framed` |
| move a frame | drag it, or arrow keys (1 mm; with Shift 10 mm) |
| resize a frame | drag a white grip on a side or corner; the opposite side stays |
| rotate a frame freely | drag the orange grip above the top edge; hold Shift for 0.5° steps; `+` / `-` turn by 0.1° |
| turn the saved photo by 90° or 180° | right-click > Rotate 90° clockwise / counter-clockwise / 180° |
| remove the skew | right-click > Align horizontally (remove skew) |
| give it an exact photo size | right-click > Fit to size > 9 x 13 cm ... |
| delete a frame | right-click > Delete frame, or the Delete key |
| add a frame | right-click on free space > Add frame here > size, or Add frame: whole page |

The orange grip marks the top of the frame: if you rotate a frame so that the
grip points to the right, the photo is saved turned accordingly. The result is
always a straight rectangle: photos are only rotated, never distorted into a
trapezoid.

### 6.4 Confirm and continue

**Confirm N photo(s)** cuts, straightens and saves the photos as
`photo-0001.png`, `photo-0002.png` ...; numbering continues after the highest
number already in the album. Then put the next page on the glass. **Discard
scan** throws a scan away; **Detect again** repeats the detection, e.g. after
switching the size fitting off.

~~~text
album/
  photo-0001.png ...   the photos, numbered in scan order
  album.json           per photo: file, source scan, resolution, frame
  scans/               full-page scans (only with "Keep full-page scans")
~~~

![A flatbed scan and the photos saved from it](img/photo-album-result.png)

**Print saved photos ...** prints the photos of the last confirmed page with
"Scale to fit the page" preselected.

## 7. Printing

scanbench prints through CUPS, the printing system of Linux desktops. Check
what scanbench sees (normal user):

~~~bash
scanbench printers
~~~

| Field of the print dialog | Meaning |
|---|---|
| Printer | all CUPS queues; the default printer is preselected |
| Copies | 1 to 99 |
| Scale to fit the page | `-o fit-to-page`; preselected for photos |
| Driver options | one choice per option of the driver (PPD), important ones first: paper source (`InputSlot`), media type, page size, colour, quality, duplex |

![Print dialog with example driver options](img/print-dialog.png)

Only options you change are sent; everything else keeps the printer defaults.

| Job | Paper source | Media type | Page size |
|---|---|---|---|
| document on A4 | cassette or automatic | plain paper | A4 |
| photo 10 x 15 cm | photo tray or rear tray | glossy photo paper | 10x15 / 4x6 |
| printable CD/DVD | CD/DVD tray | printable disc | disc size of the driver |

The names come from the printer driver. A CD/DVD tray is only offered if the
installed driver supports it; the driverless IPP Everywhere queue often has
fewer options than the manufacturer's driver.

## 8. Updating

### 8.1 Install a newer release

~~~bash
bash ~/Projects/scanbench/install.sh
~~~

Normal user. Each release goes into its own `venvs/X.Y.Z`; the link `venv` is
switched in one atomic step. The active and the previous release are kept.

### 8.2 A running window switches by itself

| Situation | Behaviour |
|---|---|
| update started from this window (**scanbench > Update ...**) | switches automatically when done |
| update installed from a terminal or another window | asks "Switch to it now?" |
| a scan, save or print job runs, a photo scan waits for confirmation, or a document is unsaved | waits and switches when the work is done, saved or discarded |

A window started from a git clone (source checkout) never switches.

### 8.3 Maintainer: release delivered patches

Archives `scanbench-X.Y.Z-patch.tar.gz` in `~/Downloads` become releases with
`scanbench update` (or **scanbench > Update ...**, which runs
`scanbench update --yes`). Per version, ascending: branch `hotfix/X.Y.Z`
from `main`, `git am`, all six gates locally, pull request into `main`
(CI 1/3), tag `vX.Y.Z` (CI 2/3: Python matrix and release check), pull request
back into `develop` (CI 3/3); finally the newest version is installed and the
archives are moved to `<installation>/releases`. A failed run can be started
again; it continues where it stopped.

| Option | Meaning |
|---|---|
| `--yes` | apply all pending archives without asking |
| `--upto X.Y.Z` | apply only up to this version |
| `--clone DIR` | git clone (default `$SCANBENCH_CLONE` or `~/Projects/scanbench`) |
| `--downloads DIR` | folder with the archives (default `~/Downloads`) |

`scanbench publish` does the first publication once. Normal user for both:
`git` and `gh` act with your GitHub login. Details:
[release process](../developer/release-process.md), [CI](../developer/ci.md).

## 9. Troubleshooting

**First step**, normal user:

~~~bash
scanbench doctor
~~~

It shows version, directories and every external program with its location
or the package to install.

| Problem | Check |
|---|---|
| scanner not found | `scanimage -L` lists what SANE sees; install `sane-airscan` for network scanners; scanner and computer in the same network; close other scanning programs that hold the device. `scanbench devices --test` must at least show the virtual scanner `test` |
| photos not found or merged | leave space between photos; close the lid; very light photos on a white lid: add the frame by hand and adjust it with the grips |
| no reduced PDF sizes | `sudo apt install ghostscript` |
| printing fails | `lpstat -t` shows scheduler, queues and waiting jobs; "No printer is set up in CUPS" means no queue exists: add the printer in the printer settings of your desktop |
| an option such as the CD/DVD tray is missing | the queue uses a driver without it (often IPP Everywhere) |
| no icon in dock or menu | run `scanbench install-desktop` again; on Wayland the window is matched by the app ID `io.github.peddanet.scanbench`, so the desktop file name must stay unchanged |

## 10. References

- [scanimage(1)](https://manpages.debian.org/scanimage) and [sane-test(5)](https://manpages.debian.org/sane-test)
- [img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf)
- [Ghostscript: PDF output and PDFSETTINGS](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html)
- [CUPS: command-line printing and options](https://openprinting.github.io/cups/doc/options.html)
- [OpenCV: minAreaRect and contour functions](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)
