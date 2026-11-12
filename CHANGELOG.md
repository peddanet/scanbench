# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning 2.0.0](https://semver.org/).

## [Unreleased]

### Changed

- Print dialog: readable names instead of driver keywords (paper sizes with
  dimensions, trays, duplex, colour); photo sizes marked "Photo ..." and
  listed after a separator; the keyword is the tooltip. A hint says when
  the driver offers no CD/DVD tray.

## [0.2.3] - 2026-11-12

### Added

- Preview scan: the whole glass at the lowest resolution of at least 75 dpi;
  then **Scan photos** scans only the area around the frames (plus 3 mm) at
  the chosen resolution and takes the frames over. **Scan whole page** keeps
  the old one-step way.
- Live progress for every scan: the image builds up in the preview; the
  status bar shows a progress bar and page, percent, elapsed and remaining
  time; **Cancel** stops the scan (feeder pages already scanned are kept).
  `scanimage` output is streamed as PNM and read with `--progress`.
- Frame editor toolbar: undo/redo, zoom (also Ctrl + wheel, up to 16 x),
  fit and 100 %, draw frame (D), horizontal and vertical guide lines,
  exact values per frame (width, height, skew in 0.1 degree steps, turn),
  previous/next photo (PgUp/PgDown).
- Context menu: merge selected frames (when one photo was split).
- Frame numbers in a blue box at the top-left corner of every frame.
- Version in the window title and permanently at the right of the status bar.
- Release switch hands over the open work: scanner, tab, the photo scan
  waiting for confirmation with its frames and the document pages
  (`sessions/handover/`).

### Changed

- Photos lying edge to edge are separated (`FrameSplitter`): along a light
  seam, or along an edge line if both parts have a standard photo size; up to
  three cuts per blob, slanted seams up to 3 degrees.
- Frame sides are placed on the photo edges at full scan resolution
  (`EdgeRefiner`): lid colour, a light strip up to 1.5 mm and the grey
  shadow line along an edge stay outside; a wider white print border stays
  inside. Detection tests now require 1.5 mm instead of 3 mm accuracy.
- Fitting to photo sizes never grows a frame by more than 1 mm per side.
- Arrow keys move a frame by one screen pixel (Shift: ten), so zooming in
  gives finer steps down to one scan pixel; previously fixed 1 mm / 10 mm.
- An unconfirmed photo scan or an unsaved document no longer delays a
  release switch, because the work is handed over.
- `ScanimageBackend.scan` takes a path prefix instead of directory and stem.

### Fixed

- Guide lines: `shape()` of a line with a cosmetic pen no longer recurses.

## [0.2.2] - 2026-11-12

### Documentation

- README with a "See it in action" section: screenshots of the real program
  (photo detection with a turned print, the saved photos, documents tab,
  print dialog), made with simulated scanner input from copyright-free sample
  photos; sources and licences in `docs/user/img/samples/SOURCES.md`.
- `tools/screenshots.py` regenerates all screenshots.
- Concept "Detailed settings, transparency and sessions"
  (`docs/concept/settings-and-sessions.md`).

## [0.2.1] - 2026-11-11

### Added

- Frame editor of the photo-album tab: a line below the preview shows size,
  skew and output orientation of the selected frame; grips on the selected
  frame resize it (the opposite side stays) and an orange grip above the top
  edge rotates it freely (Shift: 0.5 degree steps); arrow keys move by 1 mm
  (Shift: 10 mm), `+`/`-` turn by 0.1 degrees, Delete removes the frame.

### Documentation

- User documentation merged into one user guide (`docs/user/README.md`) with
  a clickable table of contents.
- Developer documentation split into one page per functional unit:
  architecture overview, core and updates, scanning and documents, photo
  album, printing, GUI and threads.
- Project README rewritten: features, installation, usage, documentation map.

## [0.2.0] - 2026-11-11

### Added

- Documents tab: scanner selection shared by all tabs; flatbed, feeder one
  side, feeder both sides (as offered by the device); colour, grey, black and
  white; resolution and paper (A4, A5, A6, Letter); page thumbnails with large
  preview; rotate, reorder, delete; manual duplex (merge fronts and reversed
  backs); PDF in five sizes: lossless (img2pdf) or reduced with Ghostscript
  `/screen`, `/ebook`, `/printer`, `/prepress`, always from the lossless
  original.
- Photo-album tab: full A4 frame scan; detection of several photos and
  postcards, including grey or white borders and photos turned by 90 degrees;
  frames fitted to 9 x 13, 10 x 15, postcard A6, 13 x 18 cm; frame editor
  with context menu (rotate 90/180 degrees, remove skew, fit to size, delete,
  add frame) and drag to move; confirmation per page; deskewed photos saved as
  PNG or JPEG with continuing numbers and `album.json`; optional full-page
  scans; album folder remembered.
- Printing through CUPS: all printers, default preselected, copies, fit to
  page, every driver option (paper source such as photo tray or CD/DVD tray,
  media type, page size, quality); for documents and photos.
- Commands `scanbench devices [--test]` and `scanbench printers`;
  `scanbench doctor` also checks `lp` and `lpoptions`.
- About box in the menu.
- `SCANBENCH_TEST_DEVICE=1` offers SANE's virtual test scanner.

### Changed

- The desktop entry passes `SCANBENCH_HOME` and `SCANBENCH_BIN`, so an update
  started from the window installs into the same places as one started in a
  terminal.
- A release switch also waits for an unconfirmed photo scan or an unsaved
  document, not only for running jobs.
- Raw scans of a session are kept in `~/.cache/scanbench` and deleted on exit.
- New runtime dependencies: OpenCV (headless), NumPy, Pillow, img2pdf. CI
  installs `sane-utils` and `ghostscript` for the integration tests.

### Documentation

- User pages: scanning documents, scanning photo albums, printing;
  troubleshooting for photos and printing; glossary terms.
- Developer architecture: modules, class and sequence diagrams of 0.2.0.

## [0.1.0] - 2026-11-11

### Added

- Milestone M0: repository skeleton with the layers domain, application,
  infrastructure and ui.
- Main window with placeholder tabs "Documents" and "Photo album"; version in
  the status bar, marked when run from a source checkout.
- Command line: `scanbench`, `scanbench doctor`, `scanbench install-desktop`,
  `scanbench uninstall-desktop`, `scanbench update`, `scanbench publish`,
  `scanbench --version`.
- Per-user desktop entry and icon; Wayland app ID `io.github.peddanet.scanbench`.
- XDG directory layout, single-root layout via `SCANBENCH_HOME`.
- Six quality gates in `tools/check.sh` with numbered stages, log directory,
  `--fast`, `--full`, `--json`, `--only`; pre-push hook.
- GitHub Actions workflow: one Python version per pull request, matrix
  3.12/3.13/3.14 and release check on tags.
- `install.sh`: installation from a release tag into its own venv
  `venvs/X.Y.Z`; the link `venv` is switched atomically, the previous release
  is kept.
- `scanbench update` and menu "Update ...": delivered patch archives become
  releases through hotfix branch, pull requests, tag and back-merge with all
  CI runs, then the newest release is installed; resumable, locked, numbered
  output with a CI summary.
- `scanbench publish`: first publication on GitHub including repository
  settings, branch protection and first tag.
- Open windows switch to a newly installed release when idle: automatically
  after an update from the window, after a question otherwise.
- The desktop entry passes `SCANBENCH_HOME` to programs started from the menu.

### Documentation

- Documentation tree with lead documents for user, developer and concept
  documentation; concept revision 1 with diagrams.
