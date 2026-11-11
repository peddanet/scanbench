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

## Modules of release 0.1.0

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

## Target design

The full design for milestones M1 to M4 (scanner adapter, device profiles,
page pipeline, photo detection, encoders, exporters) and the Gang-of-Four
patterns it uses are in the
[concept, chapter 5](../concept/scanbench-concept.md#architecture). The
diagram sources are in [`docs/concept/diagrams`](../concept/diagrams).
