# Settings, presets and the settings form

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

Increment 0.3.0 of the concept [Settings and sessions](../concept/settings-and-sessions.md)
(sections 4 and 7). Sessions (0.3.2), the device profile layer and live
previews (0.3.2, 0.3.3) come later.

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/settings_schema.py` | `SettingDefinition`, `DEFINITIONS`, `BY_KEY`, `for_tab` | every option once as data: key, label, group, built-in value, help text, choices or bounds, unit, `device`, `remember`; `check` validates a value, `text` formats it |
| `domain/settings_stack.py` | `SettingsStack`, `Layer` | effective value and its source over the layers (Chain of Responsibility) |
| `infrastructure/settings_files.py` | `SettingsFiles`, `Loaded` | `settings.toml` and `presets/*.toml`: read with `tomllib`, write with `tomli_w`, atomically; unknown keys kept; invalid values reported; `settings.json` of 0.2.x taken over once (Adapter) |
| `ui/setting_rows.py` | `SettingRow`, `create_editor` | a widget with source badge and reset button; reads and shows values of combo boxes, spin boxes, check boxes and line edits |
| `ui/tab_settings.py` | `SettingsHub`, `TabSettings`, `PresetBar` | shared stack and files; the rows, sections and summary line of one tab; presets and "Save as default" |
| `tools/settings_table.py` | — | writes the options table of the user guide from `DEFINITIONS`; a unit test fails if the guide is outdated |

## Layers

| Priority | Layer | Badge | Filled by | Stored |
|---|---|---|---|---|
| 4 (highest) | `SESSION` | changed | edits in the form | no (sessions: 0.3.2) |
| 3 | `PRESET` | preset | the chosen preset of the tab | `presets/<tab>-<slug>.toml` |
| 2 | `DEFAULT` | default | **Save as default**; settings with `remember` (album folder) at once | `settings.toml` |
| 1 | `BUILT_IN` | built-in | `SettingDefinition.default` | program |

`SettingsStack.set` drops a session value that equals the value below it, so
"changed" always means "differs". **Save as default** writes the tab's
effective values that differ from the built-in ones and unselects the preset,
which would otherwise hide them.

## Flow

~~~mermaid
sequenceDiagram
  participant B as build_workbench
  participant H as SettingsHub
  participant T as Tab (PhotoTab / DocumentTab)
  participant S as TabSettings
  participant D as DeviceBar
  B->>H: load() settings.toml (problems -> status bar)
  B->>T: create with TabContext(settings=H)
  T->>S: row(key, widget) while laying out; sections()
  T->>S: apply(): effective values into the widgets
  D-->>T: options_changed
  T->>T: SettingsPanel.apply(options) refills combo boxes
  T->>S: apply(): wanted value or "not offered" badge
  Note over S: user edits a widget
  S->>H: stack.set(key, value, SESSION or DEFAULT)
  S->>S: refresh(): badges, section titles, summary
  S-->>T: changed(key) -> refresh buttons
~~~

The tabs still read the scan settings from their widgets (they show what the
scanner really offers); options without a widget of their own in the basic
form (JPEG quality, PNG compression, size tolerance) are read with
`TabSettings.value` and passed on: `AlbumOptions.encoding` to
`ImageStore.save`, the tolerance to `PhotoSession.detect(snap=...)`.

## Adding an option

1. Add a `SettingDefinition` to `DEFINITIONS` (group `Basic` only if the tab
   lays out its widget itself and wraps it with `TabSettings.row`).
2. Use the value where it takes effect; an option without effect is not added.
3. Run `python3 tools/settings_table.py` to update the user guide.
4. Old files stay valid: a new key simply has its built-in value. Renaming or
   removing a key needs a schema step (`SCHEMA`) and a migration.
