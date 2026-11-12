# Detailed settings, transparency and sessions

Back to: [Concept](README.md) · [Documentation home](../README.md)

| | |
|---|---|
| Status | revision 2, 2026-11-12: decisions D7–D15 taken; parts implemented in 0.2.3 (see 1.3); increment 0.3.0 implemented in a first scope (see 8) |
| Builds on | [concept revision 1](scanbench-concept.md), scanner reference rev. 4 ("format matrix"), release 0.2.1 |
| Decides | which options exist, how their effect is shown, where they are stored, how sessions are saved and resumed |

**Abstract.** scanbench 0.2.1 offers the coarse options: source, colour,
resolution, paper, PDF size and photo format. The scanner reference describes
many more: device name and backend, duplex order and back-side rotation, batch
size, file naming, and the full set of Ghostscript parameters behind the PDF
sizes. This concept makes all of them settable without losing the overview.
It rests on three ideas:

1. **One settings model with layers** (built-in → device profile → preset →
   session). The application always shows the effective value of an option
   and where it comes from.
2. **Three levels of transparency**: a tooltip with the effect, live figures
   computed without scanning, and a live preview where one is possible.
3. **Persistent sessions**: every command is saved at once, so a large job can
   be closed in the evening and continued the next day. As a side effect,
   release switches no longer have to wait for unsaved work.

## Contents

1. [Goals and constraints](#1-goals-and-constraints)
2. [Inventory of options](#2-inventory-of-options)
3. [Transparency: how the user sees the effect](#3-transparency-how-the-user-sees-the-effect)
4. [Configuration model](#4-configuration-model)
5. [Sessions](#5-sessions)
6. [Keeping the overview: screen layout](#6-keeping-the-overview-screen-layout)
7. [Architecture](#7-architecture)
8. [Increments](#8-increments)
9. [Open decisions and risks](#9-open-decisions-and-risks)
10. [Glossary additions](#10-glossary-additions)
11. [Sources](#11-sources)

## 1. Goals and constraints

### 1.1 Requirements from the request of 2026-11-12

| ID | Requirement |
|---|---|
| S1 | Besides the coarse options, every detail option of the scanner reference can be set. |
| S2 | The user knows what an option does: through a live preview where possible, otherwise through explanations and tooltips, and in the documentation. |
| S3 | All settings are kept in the configuration. |
| S4 | Sessions can be saved and loaded; work can stop in the evening and continue the next day. |
| S5 | Very large sessions (many pages or album scans over several days) are possible. |
| S6 | The interface stays clear; the user always sees what is being done. |
| S7 | Every session belongs to a **project with a name** (request of 2026-11-12, see [5.8](#58-projects)). |

### 1.2 Constraints found in the scanner reference

| Finding | Source | Consequence for this concept |
|---|---|---|
| Option names differ per backend (`ADF` with airscan, `Automatic Document Feeder` with pixma). | reference 1, 9.4 | Options are read from the device at runtime; settings store the *meaning* (feeder), not the backend word. |
| airscan offers only Color and Gray, at 150/300/600 dpi; pixma also offers Lineart and 75 to 2400 dpi. | reference 1 | Choices are always limited to what the selected device reports; settings that a device cannot honour are marked, not hidden. |
| Duplex only for A4/Letter (manufacturer). | reference 2.3 | Duplex settings are tied to the format; an invalid combination is explained, not just disabled. |
| Duplex page order (interleaved or two runs) and back-side rotation are **not verified** on Ubuntu 26.04. | reference 2.2, 13 | These values carry a state "assumed" until the calibration wizard has measured them. |
| Ghostscript reduction must always start from the original; cascades have no or bad effect (DownsampleThreshold 1.5, effective DPI). | reference 12 | Every preview and every output is produced from the lossless original. |
| Fixed device name instead of an automatically detected one, because detection failed with two active network interfaces. | reference 14 | The device profile stores a fixed device name; detection is only an offer. |

### 1.3 Editor requests of 2026-11-12, planned before 0.3.0

| Request | Release |
|---|---|
| zoom in and out of the preview | 0.2.3 (done) |
| horizontal and vertical guide lines, pulled out of a ruler and removed again | 0.2.3 (done) |
| undo and redo buttons for all frame edits | 0.2.3 (done) |
| exact values per photo (angle, width, height) | 0.2.3 (done) |
| preview scan at 75 to 150 dpi, then a high-resolution scan of only the area around the photos | 0.2.3 (done) |
| live scan progress: image building up, progress bar, page counter, times; cancel | 0.2.3 (done) |
| separate photos lying edge to edge; draw frames by hand; merge frames | 0.2.3 (done) |
| frame sides exactly on the photo edges, no light strip | 0.2.3 (done) |
| frame numbers visible, previous/next photo | 0.2.3 (done) |
| version in the status bar; open work kept across a release switch | 0.2.3 (done, minimal handover; full sessions 0.3.1) |

The first four rows of the table were planned for 0.2.3, the preview scan and
progress for 0.2.4; on request they were delivered together in 0.2.3.

### 1.4 What this concept does not add

No functions beyond the reference and the existing requests. The following
are listed as candidates only, without design: blank-page removal, OCR, PDF/A
output, brightness and contrast correction. Each would need its own decision.

## 2. Inventory of options

Legend for the column *Now*: **0.2.1** = settable today, **fixed** = a fixed
value in 0.2.1, **new** = not present in 0.2.1. *Preview* names the
transparency level from chapter 3 (T = tooltip, F = live figures, P = live
preview).

### 2.1 Device

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| Device | fixed name or detected | first detected | 14 | 0.2.1 (detected only) | which scanner is used | T |
| Fixed device name | text, e.g. `airscan:wsd:…` | none | 14.3 | new | bypasses network detection; robust against the multi-interface problem | T |
| Backend preference | airscan, pixma | airscan | 1, 9.1 | new | airscan is more stable for feeder batches; pixma offers Lineart and more resolutions | T, F (option list per backend) |

### 2.2 Scan

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| Source | Flatbed, Feeder, Feeder duplex | Flatbed | 4, 5 | 0.2.1 | where the paper is taken from | T |
| Colour mode | as reported: Color, Gray, (Lineart) | Color | 1 | 0.2.1 | file size and look; Lineart only with pixma | T, F (size), P (prescan) |
| Resolution | as reported, e.g. 150/300/600 | 300 documents, 600 photos | 1, 3 | 0.2.1 | detail, file size, scan time | F (pixels, memory, size), P |
| Paper / scan area | A4, A5, A6, Letter, custom width × height | A4 | 3 | 0.2.1 without custom | scanned area; width limited to 215.9 mm | F (mm and pixels), P (frame on prescan) |
| Area offset | left, top in mm | 0, 0 | 3 | fixed 0 | moves the area on the flatbed | P (prescan) |
| Batch limit | 1 to 70 sheets | unlimited (until empty) | 4.1.2 | fixed | protects against endless runs; with BJNP problems shorter batches are safer | T |

### 2.3 Duplex

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| Page order | interleaved (A), two runs (B) | A, state "assumed" | 13 | fixed A | order of fronts and backs before rotation | P (thumbnails reorder) |
| Back-side rotation | 180°, none | 180° (long edge), state "assumed" | 2.2 | fixed none (manual turn per page) | backs upright after scan | P (thumbnails turn) |
| Binding edge of the document | long edge, short edge | long edge | 2.2 | new | selects the rotation; short edge = calendar binding | T |

### 2.4 Document output

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| PDF size preset | Original, Screen, E-book, Printer, Prepress, Custom | E-book | 12.5 | 0.2.1 without Custom | file size against quality | F (estimated and measured size), P (page comparison) |
| Custom: target resolution | 72 to 600 dpi | 200 | 11.1 | new | image resolution in the PDF | F, P |
| Custom: JPEG quality factor (QFactor) | 0.05 to 1.0, lower = better | 0.15 | 11.1 | new | compression artefacts against size | P |
| Custom: chroma subsampling | off (4:4:4), on (4:2:0) | off | 11.1 | new | colour fringes on logos and stamps when on | P |
| Custom: downsampling method | Bicubic, Average, Subsample | Bicubic | 11.1 | new | sharpness of reduced images | P |
| Custom: downsample threshold | 1.0 to 2.0 | 1.5 (Ghostscript default) | 12.1, 12.4 | new | from which effective resolution images are reduced; explains "no effect" cases | T, F |
| PDF compatibility level | 1.4, 1.7 | 1.7 | 11.1 | fixed 1.7 | 1.4 for very old viewers | T |
| File name pattern | text with `{date}`, `{time}`, `{n}` | `scan_{date}_{time}` | 4 | new (dialog only) | name of the PDF | F (example name) |
| Output folder | path | `~/Documents/scanbench` | config chapter of concept rev. 1 | new | where PDFs go | T |
| Keep raw pages | yes, no, ask | ask | 4 | new (deleted on exit) | disk space against reprocessing later | F (disk use) |

### 2.5 Photo album

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| Format | PNG, JPEG | PNG | concept rev. 1 | 0.2.1 | lossless or small | F (size) |
| PNG compression level | 0 to 9 | 6 | concept rev. 1 | fixed (Pillow default) | time and size only, always lossless | F |
| JPEG quality | 70 to 95 | 92 | concept rev. 1 | fixed 92 | artefacts against size | P (100 % crop comparison) |
| JPEG chroma subsampling | 4:4:4, 4:2:0 | 4:4:4 | 11.1 | fixed 4:4:4 | colour fringes | P |
| Downscale photos to | off, 300, 200 dpi | off | concept rev. 1 | new | size of the saved photos | F |
| Snap to photo sizes | on/off, tolerance 2 to 10 % | on, 6 % | 0.2.1 | 0.2.1 (tolerance fixed) | frames get exact sizes | P (frames) |
| Detection: colour distance | 5 to 40 | 14 | 0.2.1 | fixed | sensitivity to light borders | P (mask overlay) |
| Detection: minimum photo side | 10 to 80 mm | 25 mm | 0.2.1 | fixed | ignores specks and small items | P |
| Detection: gap closing / separation | 1 to 10 mm | 3 / 2 mm | 0.2.1 | fixed | merges broken photos / separates touching ones | P (mask overlay) |
| Numbering pattern | text with `{n:04}` | `photo-{n:04}` | 0.2.1 | fixed | file names | F (example name) |
| Keep full-page scans | yes, no | no | concept rev. 1 | 0.2.1 | re-cut later; disk use | F (disk use) |

### 2.6 Printing

| Option | Values | Default | Ref. | Now | Effect | Preview |
|---|---|---|---|---|---|---|
| Printer per job type | CUPS queue for documents, for photos | CUPS default | 15 | per dialog only | no re-selection each time | T |
| Driver options per job type | as reported by the driver | driver default | 15 | per dialog only | e.g. photo tray and glossy paper remembered for photos | T |

## 3. Transparency: how the user sees the effect

Every option gets the levels that are honestly possible for it. Scanner-side
options (resolution, colour mode, area) can only be previewed by scanning.
Processing options (PDF reduction, JPEG quality, detection) can be previewed
from a page that is already scanned.

| Level | What the user sees | Applies to |
|---|---|---|
| T: explanation | tooltip with one line each for *what*, *effect* and *default*; a "?" link to the matching section of the user guide; options in state "assumed" carry a marker with the reason | every option |
| F: live figures | values computed without scanning: pixel size, raw memory, expected file size, example file name, disk use of the session; after the first scans, measured values replace estimates (marked "measured") | resolution, area, formats, naming, retention |
| P: live preview | an image that shows the effect | see below |

### 3.1 Live previews

| Preview | How it works | Cost |
|---|---|---|
| Prescan | quick scan of the flatbed at the lowest offered resolution (e.g. 150 dpi with airscan); shows the area frame, the offset and the colour mode | one short scan; only on request (button) |
| PDF page comparison | one page of the current document is reduced with the chosen settings; the original and the result are shown side by side at 100 % in a synchronised crop, with the size of both | Ghostscript on one page, about a second; always from the lossless original |
| Photo encoder comparison | the same with one cut photo as PNG and JPEG at the chosen quality | Pillow, milliseconds |
| Detection overlay | the detection mask and the found frames are drawn over the current scan; sliders for colour distance, minimum side and gap sizes update the overlay | detection at 75 dpi, below a second |
| Duplex result | thumbnails show order and rotation of the last duplex run under the current settings | no new scan; reordering of existing pages |

### 3.2 Changed and effective values

- A value that differs from its default or profile is shown in bold, with a
  reset button and a marker of its source (see 4.2).
- A one-line summary at the top of each tab shows the effective settings, for
  example `ADF Duplex · Color · 300 dpi · A4 · backs 180° (assumed) · order A
  (assumed) · PDF E-book`.
- Values that the selected device cannot honour are shown with the reason
  (e.g. "Lineart: not offered by airscan; choose pixma").

### 3.3 What is done: activity log with commands

Each session keeps a log of the actions. Every scan and every output entry
contains the exact external command, e.g. the `scanimage` arguments and the
`gs` parameters. **Show commands** displays them; **Copy as shell script**
exports a runnable script in the style of the scanner reference. This makes
the application's work traceable and reproducible without the GUI.

### 3.4 Progress while scanning and processing

Requested on 2026-11-12: the scan must be visible while it runs, in the
preview scan and in the normal scan, with a progress bar and figures in the
status bar.

| Element | Content |
|---|---|
| live image | the page builds up line by line in the preview while the scanner delivers it |
| progress bar | progress of the current page in percent |
| status bar | `Page 3 of 10` (flatbed, known count) or `Page 3 of ?` (feeder, count unknown); elapsed time, estimated remaining time of the page, resolution, size of the page so far |
| processing | separate progress for detection, cropping and PDF output, e.g. `Saving photo 2 of 4` |
| cancel | a **Cancel** button stops the scan; already finished pages stay |

Technical basis, checked with `scanimage` and the SANE test device
(2026-11-12):

| Fact | Use |
|---|---|
| `scanimage --progress` writes `Progress: 12.4%` lines to the error output | progress bar of the current page |
| in batch mode it writes `Scanning page N` and `Scanned page N.` | page counter |
| with `--format=pnm` the image is written as an uncompressed stream (`P6` header, then the rows) | rows can be shown as they arrive; scanbench converts to PNG afterwards |

Open point, to be measured on the real device: network backends may receive
a page only as a whole (eSCL and WSD transfer finished image files). Then
the live image appears at once at the end of the page and the percentage
jumps; the page counter and the elapsed time still work.

## 4. Configuration model

### 4.1 Layers

An option's effective value is taken from the first layer that sets it:

| Priority | Layer | Content | Stored in |
|---|---|---|---|
| 1 (highest) | page or photo | e.g. rotation of one page, frame of one photo | session |
| 2 | session | settings of this job | session |
| 3 | preset | named set chosen by the user, e.g. "Letter A4 duplex", "Album 600 dpi PNG" | `presets/<name>.toml` |
| 4 | device profile | fixed device name, measured duplex order and rotation, backend option words | `devices/<id>.toml` |
| 5 | user defaults | the user's general choices (output folders, file name pattern) | `settings.toml` |
| 6 (lowest) | built-in | defaults of the application | program |

The settings panel shows the source of each value as a small badge
(`built-in`, `default`, `profile`, `preset`, `session`). "Save as preset" and
"Save as default" move session values down into a lower layer.

### 4.2 Files

~~~text
$SCANBENCH_HOME/config/          (without SCANBENCH_HOME: ~/.config/scanbench/)
  settings.toml                  user defaults
  devices/mx925.toml             device profile, written by the calibration wizard
  presets/letter-a4-duplex.toml  presets
~~~

Format TOML: readable and editable by hand. Python reads it with `tomllib`
from the standard library. Writing needs a small extra library or an own
writer (decision D7).

Rules:

1. Every file has `schema = N`. A newer program migrates older files and keeps
   a copy `*.toml.bak-N`.
2. Unknown keys are kept, not deleted (forward compatibility).
3. Invalid values are reported in the GUI with file, key and reason; the
   built-in value is used meanwhile.
4. Device addresses and host names stay in these local files only; the
   repository contains placeholders. The privacy gate remains unchanged.

### 4.3 Option definitions as data

Each option is described once, in one table of `SettingDefinition` objects:
key, type, unit, range or choices, default, group, the tooltip text, the
user-guide anchor, the preview kind and, for device options, the device
capability it depends on. The settings panel, the TOML validation, the
tooltips and a generated options table in the user guide are all made from
this one table. Then documentation and program cannot drift apart.

## 5. Sessions

### 5.1 What a session is

A session is one job with everything needed to continue it.

| Kind | Contains |
|---|---|
| Document session | settings snapshot, raw pages with rotation and order, batches (for manual duplex), saved outputs, activity log |
| Album session | settings snapshot, album folder, every full-frame scan with its frames and state (waiting, confirmed, discarded), numbering, activity log |

### 5.2 Storage

~~~text
$SCANBENCH_HOME/sessions/        (without SCANBENCH_HOME: ~/.local/share/scanbench/sessions/)
  2026-11-12_album-family-1970s/
    session.json                 state, settings snapshot, page or scan list, log
    session.lock                 present while a window has the session open
    raw/scan-0001.png ...        raw scans, never changed
    thumbs/                      thumbnails, can be rebuilt
~~~

Sessions are kept below the installation root, not in the cache, because they
are work data. With `SCANBENCH_HOME=~/scripts/scanbench.d` everything lies
below `~/scripts`.

### 5.3 Saving

| Rule | Reason |
|---|---|
| Autosave after every command (scan, rotate, confirm, frame edit) | nothing is lost when the window is closed, the computer sleeps or the release switches |
| Atomic writing: `session.json.tmp`, then rename | a crash during saving never leaves a broken file |
| Raw scans are written once and never changed; edits are stored as data | the original is always available for reprocessing (never cascade) |
| Lock file with process ID | two windows cannot change the same session; a stale lock of a dead process is detected and offered for removal |
| `schema` number in `session.json` | sessions survive updates; a newer release migrates them |

### 5.4 Opening and resuming

- Sessions live in the sessions directory (D8), changeable in the settings.
- On start: a list **Continue session** with every unfinished session: name,
  kind, pages or photos (confirmed / waiting), last change, size on disk.
- **File > Open session**, **Recent sessions**, **Save session as ...**
  (rename), **Close session** (finished).
- When a session is opened, the device of its settings is looked up. If it is
  missing or offers different options, the differences are shown before the
  next scan; nothing is changed silently.
- An album session continues numbering after the last confirmed photo, also
  when photos were added to the folder by other means.

### 5.5 Large sessions

| Topic | Measure |
|---|---|
| memory | only thumbnails and the current page are in memory; an A4 colour page at 600 dpi needs 4961 × 7016 × 3 bytes ≈ 104 MB as raw RGB |
| disk | the session panel shows the disk use; before each scan the free space is checked against the expected size, with a warning below a threshold |
| speed | thumbnails are cached in `thumbs/`; the list is loaded lazily |
| end of a session | **Finish** saves the outputs and then asks whether to delete the raw scans; the default is to keep them (decision D9) |

### 5.6 Browsing and finishing an album session

Requested on 2026-11-12:

| Function | Design |
|---|---|
| Browse confirmed pages | **Back / Forward** buttons and a page strip show every confirmed scan with its frames and the photos cut from it. A confirmed page can be reopened: frames corrected, photos cut again from the kept raw scan (needs "keep raw scans") |
| Browse photos | a grid of all saved photos of the session; double-click opens the photo large, with zoom |
| Finish | **Finish album** ends the session: the user names the album (folder name and title), chooses the outputs and confirms |
| Outputs on finishing | the photo folder (always); optionally a **PDF album** with one or more photos per page, title page and captions; later an archive or rclone upload (M4) |
| What goes into the PDF album | every confirmed photo of the session; nothing has to be ticked beforehand (request of 2026-11-12); a selection can be made in the finishing dialog |
| Scaling in the PDF album | two choices: **original size** (the photo in its real size, e.g. 10 x 15 cm on A4) or **maximised** (each photo as large as fits the page, margins kept); with "maximised", normalisation either **over all pages** (one common scale, sizes stay comparable) or **per page** (each page filled) |
| "Keep full-page scans" | becomes unnecessary: with D9 the raw scans of a session are always kept; the checkbox is removed with the sessions |

### 5.7 Effect on release switching

Because every command is saved immediately, a switch to a new release no longer
has to wait for "unsaved work". The new release reopens the sessions that were
open, in the state they had. Only a running scan still postpones the switch.

0.2.3 has a minimal form of this: before the switch the window writes a
handover (`sessions/handover/`: scanner, tab, the waiting photo scan with its
frames, the document pages) and the new window takes it over once.

### 5.8 Projects

Requested on 2026-11-12: every session belongs to a project, and projects have
names.

| Rule | Design |
|---|---|
| name at the start | a new photo album or document job first asks for the project name |
| folder | the album folder (and the session directory) is named after the project, e.g. `~/Pictures/Family 1970s/` |
| rename at any time | renaming the project renames the folder, the session directory and the title in `album.json` and `session.json` in one step; open windows follow |
| over days | the start list shows the projects; choosing one continues its session |

Decisions of 2026-11-12 (see [chapter 9](#9-open-decisions-and-risks)):

| # | Question | Decision |
|---|---|---|
| D12 | characters in folder names | letters (also umlauts and ß), digits, space, `-`, `_`; `/` and control characters become `-`; the display name keeps everything |
| D13 | renaming onto an existing folder | a dialog offers all three ways: cancel and choose another name, merge both projects (photo numbers renumbered without clashes), or append a number (`Family 1970 (2)`); nothing happens without the choice |
| D14 | documents and photos in one project | a project holds both kinds, in the sub-folders `photos/` and `documents/` |
| D15 | where project folders go | below one base folder chosen once in the settings, default `~/Pictures/scanbench/`; the project name is the sub-folder: `~/Pictures/scanbench/<project>/photos/` |

## 6. Keeping the overview: screen layout

~~~text
+----------------------------------------------------------------------------------+
| scanbench                                   Session: Album family 1970s  saved ✓ |
| Scanner: [airscan Canon MX920 (profile mx925) v]   Preset: [Album 600 dpi PNG v] |
| ADF Duplex · Color · 300 dpi · A4 · backs 180° (assumed) · PDF E-book            |
+--------------------+-------------------------------------------+-----------------+
| SESSION            |                                           | SETTINGS        |
| 3 scans            |                                           | Basic           |
|  1 confirmed (4)   |            preview / frame editor          |  Colour  ...    |
|  2 confirmed (3)   |                                           |  Resolution ... |
|  3 waiting   (4)   |                                           | > Scan area     |
| 11 photos, 1.2 GB  |                                           | > Duplex  (!)   |
| [Continue] [Finish]|                                           | > PDF output    |
|                    |                                           | > Detection     |
| ACTIVITY           |                                           | > Naming        |
| 21:04 scan 3 ...   |                                           | [Save preset]   |
| [Show commands]    | Frame 2: 100 x 70 mm, skew -0.8°          | [Reset section] |
+--------------------+-------------------------------------------+-----------------+
~~~

| Principle | Implementation |
|---|---|
| The basic options stay as they are | the section **Basic** is always open and holds today's options |
| Details only on demand | the other sections are collapsed; a changed value inside a collapsed section shows a marker on the section title |
| One place for the state | the summary line under the device bar and the session panel on the left |
| Explain, do not hide | unavailable choices remain visible with the reason |
| Undo | every edit command is recorded in the session; **Undo/Redo** also covers the frame editor (open request from M3) |

## 7. Architecture

### 7.1 New classes

| Layer | Class | Responsibility | Pattern |
|---|---|---|---|
| domain | `SettingDefinition` | one option: type, range, default, unit, help, preview kind, device capability | — |
| domain | `SettingsSchema` | all definitions, groups, validation | Composite (groups) |
| domain | `SettingsStack` | resolves the effective value and its source over the layers | Chain of Responsibility |
| domain | `Preset`, `DeviceProfile` | named value sets | — |
| domain | `SessionState` (document, album) | serialisable state of a job | Memento |
| domain | `EditCommand` | one reversible edit (rotate page, move frame, confirm) | Command |
| application | `SessionManager` | create, open, autosave, lock, finish, list sessions | Facade |
| application | `PreviewService` | prescan, PDF page comparison, encoder comparison, detection overlay | Strategy per preview |
| infrastructure | `TomlStore` | read, validate, migrate and write TOML files | Adapter |
| infrastructure | `SessionRepository` | session folders, atomic writes, lock files | Repository |
| infrastructure | `CommandLog` | records external commands; exports a shell script | — |
| ui | `SettingsForm` | builds the sections and widgets from the schema | Factory Method |
| ui | `SessionPanel`, `ActivityPanel`, `ComparisonView` | panels of chapter 6 | — |

### 7.2 Class overview

~~~mermaid
classDiagram
  class SettingDefinition { key; type; default; unit; help; preview }
  class SettingsSchema { groups; validate() }
  class SettingsStack { effective(key); source(key) }
  class SessionState { schema; settings; items; log }
  class SessionManager { create(); open(); autosave(); finish() }
  class SessionRepository { load(); save_atomic(); lock() }
  class EditCommand { apply(); revert() }
  SettingsSchema o-- SettingDefinition
  SettingsStack --> SettingsSchema
  SettingsStack --> Preset
  SettingsStack --> DeviceProfile
  SessionManager --> SessionRepository
  SessionManager --> SessionState
  SessionState o-- EditCommand : history
  SettingsForm --> SettingsSchema
  SettingsForm --> SettingsStack
  PreviewService --> SettingsStack
~~~

### 7.3 Resuming a session

~~~mermaid
sequenceDiagram
  actor U as User
  participant W as MainWindow
  participant M as SessionManager
  participant R as SessionRepository
  participant D as DeviceBar
  U->>W: start scanbench
  W->>M: unfinished sessions?
  M->>R: list session.json files
  R-->>M: sessions with state and size
  M-->>W: list
  U->>W: Continue "Album family 1970s"
  W->>M: open(id)
  M->>R: lock, load, migrate schema if needed
  M-->>W: SessionState (scans, frames, numbering)
  W->>D: select device of the session
  D-->>W: options differ? show differences
  W-->>U: state as left; next scan continues numbering
~~~

## 8. Increments

Each increment is a release with all quality gates, as before.

| Release | Content | Requirements |
|---|---|---|
| 0.3.0 | settings schema and stack; TOML files; generated settings form with sections, tooltips, badges, reset; summary line; presets; user-guide options table generated from the schema | S1, S2 (T), S3, S6 |
| 0.3.1 | projects with names and renameable folders; persistent sessions: autosave, lock, open, recent list, continue on start; browse confirmed pages and photos; finish with PDF album and raw-scan question; release switch with session reopen | S4, S5, S7 |
| 0.3.2 | live figures and previews: size estimates and measured values, PDF page comparison, encoder comparison, detection overlay, duplex result preview | S2 (F, P) |
| 0.3.3 | activity log with commands and shell-script export; calibration wizard writing the device profile (turns "assumed" into "measured") (undo/redo and the preview scan came with 0.2.3) | S2, S6 |

The "Entwurf" (first draft) requested on 2026-11-12 is increment 0.3.0.

Implemented in 0.3.0 (2026-11-12): schema with the options that take effect
today plus JPEG quality, PNG compression and size tolerance; layers built-in,
default, preset, session; `settings.toml` and presets per tab; badges, reset,
collapsible sections, summary line; generated options table in the user
guide. Moved on: the device profile layer and the "assumed" markers (0.3.3,
with the calibration wizard), the remaining options of chapter 2 (each when
it takes effect), the "?" link to the guide.

## 9. Open decisions and risks

Decided by the user on 2026-11-12:

| # | Question | Decision |
|---|---|---|
| D7 | writing TOML | the library `tomli-w` as dependency |
| D8 | session location | default `$SCANBENCH_HOME/sessions` (without `SCANBENCH_HOME`: `~/.local/share/scanbench/sessions`), changeable in the settings |
| D9 | raw scans after finishing | keep; delete only on request |
| D10 | preview scan | every photo page starts with a preview scan; then **Scan photos** scans only the area of the frames (changed from the proposal "button only") |
| D11 | German interface | concept rev. 1 decided English with Qt translation files; tooltips and help texts are written so that they can be translated |
| D12–D15 | projects | see [5.8](#58-projects) |

| Risk | Mitigation |
|---|---|
| too many options overwhelm | sections collapsed, basic section unchanged, presets for typical jobs, markers only where values differ |
| tooltips and documentation drift apart | both generated from the same option table (4.3) |
| session format changes between releases | schema number and migration with backup copy |
| very large sessions fill the disk | disk-use display, free-space check before each scan |
| preview differs from final output | previews use the same code path and parameters as the output, from the same original |

## 10. Glossary additions

| Term | Meaning | Further reading |
|---|---|---|
| Atomic write | write to a temporary file, then rename it over the target; readers see the old or the new file, never a half-written one | [rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html) |
| Chroma subsampling | storing colour at lower resolution than brightness (4:2:0); saves space, causes colour fringes at sharp coloured edges | [Wikipedia](https://en.wikipedia.org/wiki/Chroma_subsampling) |
| DownsampleThreshold | Ghostscript reduces an image only if its effective resolution exceeds target × threshold (default 1.5) | [Ghostscript: PDF output](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html) |
| Effective resolution | pixels of an image divided by the size it is drawn at on the page; this, not the file metadata, decides Ghostscript's downsampling | scanner reference 12.1 |
| Memento | design pattern: the state of an object is captured so it can be restored later | [Refactoring Guru](https://refactoring.guru/design-patterns/memento) |
| Prescan | quick low-resolution scan used only to preview area and colour | [scanimage(1)](https://manpages.debian.org/scanimage) |
| Preset | named set of settings the user can choose with one click | — |
| QFactor | JPEG quantisation factor in Ghostscript's image dictionaries; lower values mean higher quality | scanner reference 11.1 |
| Schema migration | converting a saved file from an older format version to the current one | — |
| Session | one job (document or album) saved with everything needed to continue it | — |
| TOML | configuration file format with sections and typed values | [toml.io](https://toml.io/en/) |

## 11. Sources

| Source | Used for |
|---|---|
| Scanner reference "Canon PIXMA MX920/MX925 – Vollständige Format-Matrix", rev. 4, 2026-10-08 (local document of the user) | options, backend differences, duplex findings, Ghostscript parameters, device naming |
| [Concept revision 1](scanbench-concept.md) | photo output options, configuration paths, milestones |
| [Python `tomllib`](https://docs.python.org/3/library/tomllib.html) | reading TOML from the standard library (Python 3.11 and later) |
| [tomli-w](https://pypi.org/project/tomli-w/) | proposed TOML writer (D7) |
| [Ghostscript: PDF output](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html) | PDFSETTINGS and image parameters |
| [scanimage(1)](https://manpages.debian.org/scanimage) | scan options, batch mode |
