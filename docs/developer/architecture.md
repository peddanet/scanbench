# Architecture

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

Overview of the structure. Each functional unit has its own page with the
module tables and diagrams.

## Layers

Dependencies point inwards only.

~~~mermaid
flowchart TB
  ui["ui: Qt widgets, no business rules"] --> application
  ui --> infrastructure
  application["application: use cases (sessions, workflows)"] --> domain
  application --> infrastructure
  infrastructure["infrastructure: adapters to files, programs, libraries"] --> domain
  domain["domain: value objects and rules, no dependencies"]
  cli["cli.py: composition root"] --> ui
  cli --> application
  cli --> infrastructure
~~~

| Layer | Package | Rule |
|---|---|---|
| domain | `scanbench.domain` | pure Python; no Qt, no I/O |
| application | `scanbench.application` | no Qt; receives collaborators through the constructor |
| infrastructure | `scanbench.infrastructure` | the only place that runs external programs and touches OpenCV, Pillow, img2pdf |
| ui | `scanbench.ui` | widgets; Qt is imported nowhere else |

`cli.py` is the composition root for the command line, `ui/workbench.py` for
the scanning GUI. The GUI is imported lazily, so `scanbench doctor` works
without a display.

## Functional units

| Unit | Page | Main classes |
|---|---|---|
| Application core, desktop integration, update and publish workflows, live switching | [update-and-switching.md](update-and-switching.md) | `Cli`, `AppPaths`, `UpdateService`, `HotfixRelease`, `ReleaseWatcher` |
| Scanner access and documents | [scanning-and-documents.md](scanning-and-documents.md) | `ScanimageBackend`, `DeviceOptions`, `DocumentSession`, `PdfWriter` |
| Photo album: detection, cropping, frame editor | [photo-album.md](photo-album.md) | `PhotoDetector`, `ImageCropper`, `PhotoSession`, `RegionView`, `frame_edit` |
| Printing | [printing.md](printing.md) | `CupsClient`, `PrintDialog`, `OptionForm` |
| GUI structure and threads | [gui.md](gui.md) | `Workbench`, `TaskRunner`, `ScanTab`, `MainWindow` |

## Design patterns in use

| Pattern | Where |
|---|---|
| Adapter | `ScanimageBackend`, `CupsClient`, `GitRepo`, `GitHubCli` wrap command line programs |
| Strategy | `PhotoDetector` (exchangeable detection with `DetectorTuning`) |
| Template Method | `ScanTab.run_job`/`refresh`; `PdfWriter.write` (lossless, then optional reduction) |
| Command | menu actions of `RegionMenus`, page commands of `PageList` |
| State | `PhotoSession`: idle or waiting for confirmation |
| Observer | Qt signals: `DeviceBar.options_changed`, `RegionView.regions_changed`, `Progress` |
| Factory Method | `build_workbench`, `release_context` |
| Parameter Object | `TabContext`, `Dialogs`, `ReleaseContext` |

## Target design

The full design for milestones M1 to M4 and its rationale are in the
[concept, chapter 5](../concept/scanbench-concept.md#architecture); diagram
sources are in [`docs/concept/diagrams`](../concept/diagrams).
