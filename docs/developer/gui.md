# GUI structure and threads

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `ui/gui_application.py` | `GuiApplication` | Qt identity, window, update dialog, watcher, restart with handover, cleanup |
| `ui/main_window.py` | `MainWindow` | tabs, header, menu (Update, About, Quit), version label, busy state, release switching |
| `ui/progress_panel.py` | `ProgressPanel` | progress text, bar, **Cancel** and the Esc shortcut in the status bar; owns the cancel event of the running job |
| `ui/switch_banner.py` | `SwitchBanner` | bar above the tabs while a new release waits; reason and **Switch now** |
| `ui/flow_bar.py` | `FlowBar`, `FlowLayout` | tool buttons of the frame editor; wrap into more rows instead of an overflow arrow |
| `infrastructure/app_log.py` | `AppLog` | `scanbench.log` (rotating), `crash.log` (`faulthandler`), hook for uncaught exceptions |
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

`run_job(..., cancellable=True)` offers the same for other jobs; such a job
reads `progress.cancel_event` itself and stops at a safe point
(`PhotoSession.accept` before the next photo; detection results are
discarded). The tab shows its **Cancel (Esc)** button below the scan buttons
while a cancellable job runs; Esc is a window shortcut of the progress panel,
enabled only then. The frame editor's own Esc (end draw mode) is enabled only
in draw mode, so the two never compete. `ScanTab.finish` prefixes the status
text with `Cancelled - ` after a cancel.

Raw scans live in a temporary directory below the cache directory
(`~/.cache/scanbench/session-*`), not in `/tmp`, which is a RAM file system on
many distributions; `Workbench.close()` waits for jobs and removes it.

## Scanner selection without waiting

`DeviceBar.restore()` (called by `GuiApplication.show` before `refresh()`)
fills the combo box from `DeviceCache` and emits `options_changed` with the
remembered options, so the tabs are usable before the search ends. The
search result (`_fill`) replaces the list and keeps the selection; it reads
options only for a device without remembered ones. A device the user selects
before the search of this run has finished is checked by reading its options
(`scanimage -d … -A`); a failure is reported as "Scanner not reachable".
**Search scanners** forgets the options of the selected device first. Every
change is written back (`_remember`), atomically via a temporary file.

## Large scans

Qt 6 refuses to decode an image whose pixels need more than the allocation
limit (`QImageReader.allocationLimit()`, 256 MB by default; environment
variable `QT_IMAGEIO_MAXALLOC`). A 1200 dpi area scan exceeds it. The frame
editor therefore never loads a scan file with `QPixmap(path)`:
`qt_images.read_preview` reads the size from the header, sets a scaled size
(longest side `MAX_PREVIEW` = 1600 px) and raises the limit for this one read
to what the file needs, then restores it. Frames stay in scan pixels
(`RegionView.frame_size` is the full size). If reading fails, `FrameEditor`
shows the reason in the details line; cropping and saving do not use Qt
(Pillow/OpenCV), so confirming still works.

## Graphics items and Python references

The frame editor (`RegionView`) never calls `QGraphicsScene.clear()`. A
graphics item that Python still references but that Qt deletes (by clearing
the scene, deleting the parent item or the view) leaves a dangling wrapper
if it is a plain Qt class: Qt cannot report the deletion, and releasing the
reference crashes the process (segmentation fault; 0.2.5 crashed this way
in `show_scan` while the live image was replaced during a scan). Rules:

- An item Python keeps a reference to is a **Python subclass**
  (`PictureItem`, `RegionItem`, `HandleItem`, `NumberBadge`, `SketchBand`,
  `GuideItem`); Qt then reports its deletion to the wrapper.
- Plain Qt items (text of a badge, top mark) are created as children and
  never stored.
- Items leave the scene with `removeItem`, which hands them back to Python;
  Python deletes them when the last reference is gone. `RegionView._clear`
  does this with blocked scene signals and keeps the one `PictureItem` of
  the view, whose pixmap is replaced (an empty pixmap means "no scan";
  `PictureItem.shown()`).

## Logging

`GuiApplication.run` starts `AppLog` before the window and stops it after
the event loop. Logged are: start with version, Python and platform; every
status text (`MainWindow.show_message`); every failed background job with
traceback (`TaskRunner`); uncaught exceptions, e.g. in Qt slots
(`sys.excepthook`); the start of a release switch; the end. A hard crash
(segmentation fault, abort) leaves the stacks of all threads in `crash.log`.
Files rotate at 1 MB (`scanbench.log` plus 4 older ones).

## Testing the GUI

pytest-qt with the offscreen platform. Tabs are built with
`tests/gui_helpers.py` (fake scanner, scripted CUPS, prepared dialog answers);
`idle()` waits until the runner has no job.
