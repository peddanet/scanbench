# GUI structure and threads

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `ui/gui_application.py` | `GuiApplication` | Qt identity, window, update dialog, watcher, restart, cleanup |
| `ui/main_window.py` | `MainWindow` | tabs, header, menu (Update, About, Quit), busy state, release switching |
| `ui/workbench.py` | `Workbench`, `build_workbench` | creates adapters, sessions and tabs (Factory Method); session work directory |
| `ui/task_runner.py` | `TaskRunner` | jobs in a `QThreadPool`, results in the GUI thread |
| `ui/device_bar.py` | `DeviceBar` | scanner selection shared by the tabs |
| `ui/tab_context.py` | `TabContext` | device bar, runner, CUPS client, dialogs (Parameter Object) |
| `ui/scan_tab.py` | `ScanTab` | base of the tabs: `run_job`, `finish`, `refresh` hook (Template Method) |

## Object structure

~~~mermaid
classDiagram
  class ScanTab { +run_job() +finish() +refresh() }
  ScanTab <|-- DocumentTab
  ScanTab <|-- PhotoTab
  ScanTab --> TabContext
  TabContext --> DeviceBar
  TabContext --> TaskRunner
  TabContext --> CupsClient
  TabContext --> Dialogs
  DocumentTab --> DocumentSession
  DocumentTab --> PageList
  PhotoTab --> PhotoSession
  PhotoTab --> FrameEditor
  FrameEditor --> RegionView
  Workbench --> DocumentTab
  Workbench --> PhotoTab
  MainWindow --> Workbench : tabs, header
~~~

## Threads

Scanning, detection, saving and printing can take seconds, so they run in the
thread pool of `TaskRunner`. A small `QObject` relay created in the GUI thread
carries the result back; its signals are delivered queued, so callbacks run in
the GUI thread. While a job runs the tab disables its buttons; `started` and
`finished` mark the main window busy, which postpones release switches
([update and switching](update-and-switching.md#when-a-switch-may-happen)).

Raw scans live in a temporary directory below the cache directory
(`~/.cache/scanbench/session-*`), not in `/tmp`, which is a RAM file system on
many distributions; `Workbench.close()` waits for jobs and removes it.

## Testing the GUI

pytest-qt with the offscreen platform. Tabs are built with
`tests/gui_helpers.py` (fake scanner, scripted CUPS, prepared dialog answers);
`idle()` waits until the runner has no job.
