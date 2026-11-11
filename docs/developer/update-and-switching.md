# Application core, updates and live switching

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

Modules of the application core, the desktop integration and the release
workflows (`scanbench update`, `scanbench publish`), and how an open window
switches to a newly installed release. The git-flow rules behind the
workflows are in the [release process](release-process.md).

## Application core and desktop integration

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

## Release workflows (update, publish)

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

## Update and live switch

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

## When a switch may happen

`MainWindow.is_busy()` is true while a background job runs (counted through
the task runner's `started`/`finished` signals, see [GUI](gui.md)) or while
`Workbench.unsaved()` reports an unconfirmed photo scan or an unsaved
document. An offered switch is then stored and retried after every job end
and every status message, i.e. after each user command.
