# GUI structure and threads

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `ui/gui_application.py` | `GuiApplication` | Qt identity, window, update dialog, watcher, restart with handover, cleanup |
| `ui/main_window.py` | `MainWindow` | tabs, header, menu (Update, About, Quit), version label, busy state, release switching |
| `ui/progress_panel.py` | `ProgressPanel` | progress text, bar and **Cancel** in the status bar |
| `application/session_handover.py` | `SessionHandover`, `Handover` | open work handed to the next release (Memento) |
| `ui/workbench.py` | `Workbench`, `build_workbench` | creates adapters, sessions and tabs (Factory Method); session work directory |
| `ui/task_runner.py` | `TaskRunner` | jobs in a `QThreadPool`, results in the GUI thread |
| `ui/device_bar.py` | `DeviceBar` | scanner selection shared by the tabs |
| `ui/tab_context.py` | `TabContext` | device bar, runner, CUPS client, dialogs, progress panel (Parameter Object) |
| `ui/scan_tab.py` | `ScanTab` | base of the tabs: `run_job`, `run_scan`, `finish`, `refresh` and `show_partial` hooks (Template Method) |

## Object structure

~~~mermaid
classDiagram
  class ScanTab { +run_job() +run_scan() +finish() +refresh() +show_partial() }
  ScanTab <|-- DocumentTab
  ScanTab <|-- PhotoTab
  ScanTab --> TabContext
  TabContext --> DeviceBar
  TabContext --> TaskRunner
  TabContext --> CupsClient
  TabContext --> Dialogs
  TabContext --> ProgressPanel
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

`run_scan` gives the job a `ScanObserver`. Its callbacks call a reporter
created by `TaskRunner.run(..., on_progress=...)`, which emits a `progress`
signal of the relay; in the GUI thread `ScanProgress` items update the
`ProgressPanel` and image arrays go to the tab's `show_partial` (live image
in the frame editor or the page preview). **Cancel** sets the observer's
`threading.Event`; the stream terminates `scanimage`. A reporter whose relay
was deleted (window closed) drops the item.

Raw scans live in a temporary directory below the cache directory
(`~/.cache/scanbench/session-*`), not in `/tmp`, which is a RAM file system on
many distributions; `Workbench.close()` waits for jobs and removes it.

## Testing the GUI

pytest-qt with the offscreen platform. Tabs are built with
`tests/gui_helpers.py` (fake scanner, scripted CUPS, prepared dialog answers);
`idle()` waits until the runner has no job.
