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

## Modules of release 0.1.0 (milestone M0)

~~~mermaid
classDiagram
  direction LR
  class Cli {
    +parser() ArgumentParser
    +run(argv) int
  }
  class Doctor {
    +run() tuple
  }
  class ToolRequirement {
    +name
    +required
    +label() str
  }
  class ToolProbe {
    +locate(name) str
  }
  class AppPaths {
    +config_dir
    +log_dir
    +release_dir
    +applications_dir
    +icon_dir
  }
  class VersionInfo {
    +checkout_root() Path
    +text() str
  }
  class DesktopInstaller {
    +install() list
    +uninstall() list
  }
  class GuiApplication {
    +configure(app)
    +run(argv) int
  }
  class MainWindow
  Cli --> Doctor
  Cli --> DesktopInstaller
  Cli --> VersionInfo
  Cli ..> GuiApplication : lazy import
  Doctor --> ToolProbe
  Doctor --> ToolRequirement
  Doctor --> AppPaths
  DesktopInstaller --> AppPaths
  GuiApplication --> MainWindow
~~~

| Module | Class | Responsibility |
|---|---|---|
| `app_info.py` | -- | application name and ID (`io.github.peddanet.scanbench`) |
| `cli.py` | `Cli` | parse commands, dispatch, wire objects (`main`) |
| `domain/tool_requirement.py` | `ToolRequirement` | an external program and its importance |
| `application/doctor.py` | `Doctor` | diagnosis report of version, directories, programs |
| `infrastructure/app_paths.py` | `AppPaths` | XDG layout or single root `SCANBENCH_HOME` |
| `infrastructure/version_info.py` | `VersionInfo` | version text with source-checkout marker |
| `infrastructure/tool_probe.py` | `ToolProbe` | find programs on `PATH` (injectable lookup) |
| `infrastructure/desktop_installer.py` | `DesktopInstaller` | write and remove desktop file and icon |
| `ui/gui_application.py` | `GuiApplication` | Qt identity (name, desktop file name, icon), event loop |
| `ui/main_window.py` | `MainWindow` | tabs per use case, status bar |
| `resources/` | -- | desktop file template, SVG icon (package data) |

## Target design

The full design for milestones M1 to M4 (scanner adapter, device profiles,
page pipeline, photo detection, encoders, exporters) and the Gang-of-Four
patterns it uses are in the
[concept, chapter 5](../concept/scanbench-concept.md#architecture). The
diagram sources are in [`docs/concept/diagrams`](../concept/diagrams).
