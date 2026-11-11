# Architecture

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

## Layers

Dependencies point inwards only. The application layer defines ports
(interfaces); the infrastructure layer implements them.

~~~mermaid
flowchart TB
  ui["ui: Qt views, no logic"] --> application
  application["application: use cases, presenters"] --> domain
  application -. ports .-> infrastructure
  infrastructure["infrastructure: adapters to files, tools, libraries"] --> domain
  domain["domain: value objects and rules, no dependencies"]
  cli["cli.py: composition root"] --> ui
  cli --> application
  cli --> infrastructure
~~~

| Layer | Package | Rule |
|---|---|---|
| domain | `scanbench.domain` | pure Python; no Qt, no I/O |
| application | `scanbench.application` | no Qt widgets; receives collaborators through the constructor |
| infrastructure | `scanbench.infrastructure` | the only place that touches files, external programs and libraries such as OpenCV |
| ui | `scanbench.ui` | widgets only; Qt is imported nowhere else |

`cli.py` is the composition root: it creates the real objects and injects
them. The GUI is imported lazily, so `scanbench doctor` works without a
display.

## Modules of release 0.1.0 (core and release workflows)

### Application core and desktop integration

| Module | Class | Responsibility |
|---|---|---|
| `app_info.py` | -- | application name and ID (`io.github.peddanet.scanbench`) |
| `cli.py` | `Cli` | parse commands, dispatch, wire objects (`main`) |
| `wiring.py` | -- | composition of the release workflows (`release_context`) |
| `domain/tool_requirement.py` | `ToolRequirement` | an external program and its importance |
| `application/doctor.py` | `Doctor` | diagnosis report of version, directories, programs |
| `infrastructure/app_paths.py` | `AppPaths` | XDG layout or single root `SCANBENCH_HOME`; clone and download folder |
| `infrastructure/release_layout.py` | `ReleaseLayout` | `venvs/X.Y.Z`, `venv` link, launcher, archive store, lock file |
| `infrastructure/version_info.py` | `VersionInfo` | version text with source-checkout marker |
| `infrastructure/tool_probe.py` | `ToolProbe` | find programs on `PATH` (injectable lookup) |
| `infrastructure/desktop_installer.py` | `DesktopInstaller` | write and remove desktop file and icon |
| `ui/gui_application.py` | `GuiApplication` | Qt identity, wiring of window, update dialog, watcher, restart |
| `ui/main_window.py` | `MainWindow` | tabs, menu, busy state, safe release switching |
| `ui/update_dialog.py` | `UpdateDialog` | runs `scanbench update --yes`, shows the output live |
| `ui/release_watcher.py` | `ReleaseWatcher` | polls the `venv` link, signals newer releases |
| `resources/` | -- | desktop file template, SVG icon (package data) |

### Release workflows (update, publish)

| Module | Class | Responsibility |
|---|---|---|
| `domain/version.py` | `Version` | `MAJOR.MINOR.PATCH`, ordering, tag |
| `domain/patch_archive.py` | `PatchArchive` | recognise `scanbench-X.Y.Z-patch[(n)].tar.gz` |
| `domain/command_result.py` | `CommandResult` | exit status and output of a command |
| `domain/update_error.py` | `UpdateError` | a workflow step failed |
| `application/progress.py` | `Progress` | numbered stages, CI run table (Observer of the workflow) |
| `application/release_context.py` | `ReleaseContext` | the collaborators of a workflow |
| `application/hotfix_release.py` | `HotfixRelease` | one archive through hotfix branch, PRs, tag, back-merge |
| `application/update_service.py` | `UpdateService` | lock, pending archives in order, install, archive store |
| `application/first_publication.py` | `FirstPublication` | create repository, settings, protection, first tag |
| `infrastructure/shell.py` | `Shell` | argument-list commands, retries for reading calls, live output |
| `infrastructure/git_repo.py` | `GitRepo` | branches, patches, pushes, tags (Adapter) |
| `infrastructure/git_versions.py` | `GitVersions` | release tags on the remote, version lines on refs |
| `infrastructure/github_cli.py` | `GitHubCli` | pull requests, CI runs, repository settings through `gh` (Adapter) |
| `infrastructure/dev_environment.py` | `DevEnvironment` | development venv of the clone, gates |
| `infrastructure/release_installer.py` | `ReleaseInstaller` | run `install.sh`, read the active release |
| `infrastructure/archive_finder.py` | `ArchiveFinder` | newest copy per version, pending versions |
| `infrastructure/update_lock.py` | `UpdateLock` | exclusive `flock` against parallel updates |

### Update and live switch

~~~mermaid
sequenceDiagram
  actor U as Maintainer
  participant W as MainWindow
  participant D as UpdateDialog
  participant C as scanbench update (child process)
  participant G as git and gh
  participant I as install.sh
  participant R as ReleaseWatcher
  U->>W: menu Update ...
  W->>D: open, start child process
  D->>C: scanbench update --yes
  loop each pending archive, ascending
    C->>G: hotfix branch, git am, gates, PR main (CI 1/3), merge
    C->>G: tag vX.Y.Z (CI 2/3), back-merge into develop (CI 3/3)
  end
  C->>I: install newest tag into venvs/X.Y.Z, switch link venv
  C-->>D: exit status 0, summary
  D-->>W: succeeded
  W->>W: idle? then restart into the new release
  R-->>W: newer release seen (updates from elsewhere): ask, switch when idle
~~~

## Modules of release 0.2.0 (scanning, photo album, printing)

### Domain and infrastructure

| Module | Class | Responsibility |
|---|---|---|
| `domain/scan_source.py`, `color_mode.py`, `image_format.py` | enums | source, colour mode, photo file format |
| `domain/pdf_quality.py` | `PdfQuality` | PDF size level and its Ghostscript preset |
| `domain/paper_format.py` | `PaperFormat` | document sizes, photo presets, A4 frame |
| `domain/scan_settings.py` | `ScanSettings` | source, mode, resolution, paper of one scan |
| `domain/device_info.py`, `device_options.py` | `DeviceInfo`, `DeviceOptions` | a SANE device; its options parsed from `scanimage -A`, mapped to the enums |
| `domain/duplex_order.py` | `DuplexOrder` | feeder order to reading order (manual duplex) |
| `domain/crop_region.py` | `CropRegion` | rotated photo frame: turn, straighten, fit, snap, clamp |
| `domain/printer_info.py`, `printer_option.py`, `print_job.py` | value objects | CUPS queue, PPD option parsed from `lpoptions -l`, chosen job |
| `domain/scan_error.py` | `ScanError` | user-facing error of scanning, saving, printing |
| `infrastructure/scanimage_backend.py` | `ScanimageBackend` | devices, options, flatbed and batch scans (Adapter) |
| `infrastructure/image_store.py` | `ImageStore` | read, turn and write images with resolution (Pillow) |
| `infrastructure/photo_detector.py` | `PhotoDetector` | colour distance + edges, minimum-area rectangles (Strategy) |
| `infrastructure/image_cropper.py` | `ImageCropper` | affine cut-out, deskew, quarter turns |
| `infrastructure/pdf_writer.py` | `PdfWriter` | lossless PDF with img2pdf, reduction with Ghostscript (Template Method) |
| `infrastructure/cups_client.py` | `CupsClient` | printers, driver options, print jobs (Adapter) |
| `infrastructure/settings_store.py` | `SettingsStore` | small persistent settings (album folder) |

### Application and user interface

| Module | Class | Responsibility |
|---|---|---|
| `application/document_session.py` | `DocumentSession`, `Page` | pages of a document, edit commands, manual duplex merge, PDF output |
| `application/photo_session.py` | `PhotoSession`, `PhotoScan`, `AlbumOptions` | full-frame scan, proposal, confirmation, numbering, `album.json` (State: idle / waiting) |
| `ui/workbench.py` | `Workbench`, `build_workbench` | creates adapters, sessions and tabs (Factory Method) |
| `ui/task_runner.py` | `TaskRunner` | background jobs in a thread pool, results in the GUI thread |
| `ui/device_bar.py` | `DeviceBar` | scanner selection shared by the tabs (Observer subject) |
| `ui/tab_context.py`, `ui/dialogs.py` | `TabContext`, `Dialogs` | collaborators and modal questions of the tabs (Parameter Object) |
| `ui/scan_tab.py` | `ScanTab` | base of the tabs: job start, error report, unlocking (Template Method) |
| `ui/settings_panel.py` | `SettingsPanel` | source, mode, resolution, paper combos following the device |
| `ui/document_tab.py`, `ui/page_list.py` | `DocumentTab`, `PageList` | document commands; thumbnails, preview, page commands |
| `ui/photo_tab.py`, `ui/photo_form.py` | `PhotoTab`, `PhotoForm` | album workflow; album options |
| `ui/region_view.py` | `RegionView`, `RegionItem`, `RegionMenus` | frame editor with context-menu commands (Command) |
| `ui/print_dialog.py`, `ui/option_form.py` | `PrintDialog`, `OptionForm` | printer, copies, driver options |

~~~mermaid
classDiagram
  class ScanTab { +run_job() +finish() +refresh() }
  ScanTab <|-- DocumentTab
  ScanTab <|-- PhotoTab
  DocumentTab --> DocumentSession
  DocumentTab --> PageList
  PhotoTab --> PhotoSession
  PhotoTab --> RegionView
  RegionView ..> RegionMenus : context menu
  DocumentSession --> ScanimageBackend
  DocumentSession --> PdfWriter
  PhotoSession --> ScanimageBackend
  PhotoSession --> PhotoDetector
  PhotoSession --> ImageCropper
  DocumentTab ..> CupsClient : print
  PhotoTab ..> CupsClient : print
  ScanTab --> TaskRunner
~~~

### Photo album sequence

~~~mermaid
sequenceDiagram
  actor U as User
  participant T as PhotoTab
  participant R as TaskRunner
  participant S as PhotoSession
  participant B as ScanimageBackend
  participant D as PhotoDetector
  U->>T: Scan page
  T->>R: run(scan)
  R->>S: scan(device, A4 frame)
  S->>B: scanimage --format=png
  S->>D: detect(pixels, dpi)
  D-->>S: regions (minimum-area rectangles)
  S-->>T: PhotoScan (waiting)
  U->>T: right-click: rotate, straighten, fit, delete
  U->>T: Confirm
  T->>R: run(accept)
  R->>S: crop, deskew, save photo-NNNN, append album.json
  S-->>T: written files (idle)
~~~

### Threads and release switching

Scans, saves and print jobs run in `TaskRunner`; the runner's `started` and
`finished` signals mark the main window busy. In addition the window asks
`Workbench.unsaved()`: an unconfirmed photo scan or an unsaved document also
postpones a release switch. Every status message re-checks a waiting switch.

## Target design

The full design for milestones M1 to M4 (scanner adapter, device profiles,
page pipeline, photo detection, encoders, exporters) and the Gang-of-Four
patterns it uses are in the
[concept, chapter 5](../concept/scanbench-concept.md#architecture). The
diagram sources are in [`docs/concept/diagrams`](../concept/diagrams).
