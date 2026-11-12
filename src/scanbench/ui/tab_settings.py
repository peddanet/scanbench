"""The settings of one tab: rows, collapsible sections, presets and summary line."""

from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QSpinBox, QToolButton, QVBoxLayout,
                               QWidget)

from scanbench.domain.settings_schema import BASIC, BY_KEY, Scalar, for_tab
from scanbench.domain.settings_stack import Layer, SettingsStack
from scanbench.infrastructure.settings_files import SettingsFiles
from scanbench.ui.dialogs import AskName
from scanbench.ui.setting_rows import SettingRow, create_editor

NO_PRESET = "(no preset)"
"""First entry of the preset list."""


@dataclass
class SettingsHub:
    """Settings shared by the tabs.

    Attributes:
        stack: Effective values over the layers.
        files: Settings files, or None to keep nothing (tests).
        presets: Name of the chosen preset per tab.
    """

    stack: SettingsStack = field(default_factory=SettingsStack)
    files: SettingsFiles | None = None
    presets: dict[str, str] = field(default_factory=dict)

    def load(self) -> list[str]:
        """Read the saved defaults.

        Returns:
            Problems found in the file, one line each.
        """
        if self.files is None:
            return []
        loaded = self.files.load_defaults()
        self.stack.set_layer(Layer.DEFAULT, loaded.values)
        return loaded.problems

    def save_defaults(self) -> str | None:
        """Write the default layer.

        Returns:
            An error text, or None if written (or nothing is kept).
        """
        if self.files is None:
            return None
        try:
            self.files.save_defaults(self.stack.layer(Layer.DEFAULT))
        except OSError as exc:
            return f"Settings not saved: {exc}"
        return None

    def keep_session(self, tab: str, keep: bool) -> None:
        """Keep or drop the changes of the running program in one tab.

        Args:
            tab: The tab.
            keep: False removes the tab's changes.
        """
        if not keep:
            session = self.stack.layer(Layer.SESSION)
            self.stack.set_layer(Layer.SESSION, {k: v for k, v in session.items()
                                                 if BY_KEY[k].tab != tab})


def _signal(editor: QWidget) -> object:
    """Return the change signal of an editor widget.

    Args:
        editor: Combo box, spin box, check box or line edit.

    Returns:
        The bound signal.
    """
    if isinstance(editor, QComboBox):
        return editor.currentIndexChanged
    if isinstance(editor, QSpinBox):
        return editor.valueChanged
    if isinstance(editor, QCheckBox):
        return editor.toggled
    if isinstance(editor, QLineEdit):
        return editor.editingFinished
    raise TypeError(f"no editor: {type(editor).__name__}")


class TabSettings(QObject):
    """Bind the widgets of a tab to the settings stack.

    The tab creates its basic widgets and wraps each with ``row(key, widget)``
    while laying out its form; ``sections()`` creates the other settings in
    collapsible sections. Every change goes into the session layer (or the
    defaults for remembered settings) and updates badges and the summary.
    """

    changed = Signal(str)
    """Key of a setting the user changed."""

    message = Signal(str)
    """A status text."""

    def __init__(self, tab: str, hub: SettingsHub) -> None:
        """Start without rows.

        Args:
            tab: ``documents`` or ``photos``.
            hub: Shared settings.
        """
        super().__init__()
        self.tab = tab
        self.hub = hub
        self.rows: dict[str, SettingRow] = {}
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self._titles: dict[str, QToolButton] = {}

    def row(self, key: str, editor: QWidget | None = None) -> SettingRow:
        """Wrap a widget (or a new one) as the row of a setting.

        Args:
            key: Setting key.
            editor: The tab's widget; None creates one from the schema.

        Returns:
            The row to place in the form.
        """
        definition = BY_KEY[key]
        row = SettingRow(definition, editor or create_editor(definition))
        self.rows[key] = row
        _signal(row.editor).connect(lambda *_args, k=key: self._edited(k))  # type: ignore
        row.reset.clicked.connect(lambda _checked=False, k=key: self.reset(k))
        return row

    def sections(self) -> QWidget:
        """Create the collapsible sections with the settings beyond the basic ones.

        Returns:
            A widget with one section per group.
        """
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        groups: dict[str, list[str]] = {}
        for definition in for_tab(self.tab):
            if definition.group != BASIC:
                groups.setdefault(definition.group, []).append(definition.key)
        for group, keys in groups.items():
            title = QToolButton()
            title.setText(group)
            title.setCheckable(True)
            title.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            title.setArrowType(Qt.ArrowType.RightArrow)
            title.setAutoRaise(True)
            content = QWidget()
            form = QFormLayout(content)
            for key in keys:
                row = self.row(key)
                form.addRow(BY_KEY[key].label + ":", row)
            content.setVisible(False)
            title.toggled.connect(lambda shown, c=content, t=title: self._fold(c, t, shown))
            layout.addWidget(title)
            layout.addWidget(content)
            self._titles[group] = title
        return box

    @staticmethod
    def _fold(content: QWidget, title: QToolButton, shown: bool) -> None:
        """Open or close a section.

        Args:
            content: The section's rows.
            title: Its title button.
            shown: Open.
        """
        content.setVisible(shown)
        title.setArrowType(Qt.ArrowType.DownArrow if shown
                           else Qt.ArrowType.RightArrow)

    def apply(self) -> None:
        """Show the effective values in all widgets."""
        for key, row in self.rows.items():
            row.put(self.hub.stack.value(key))
        self.refresh()

    def refresh(self) -> None:
        """Update badges, section markers and the summary line."""
        stack = self.hub.stack
        for key, row in self.rows.items():
            wanted = stack.value(key)
            row.show_source(stack.source(key), wanted, row.get() in (wanted, None))
        for group, title in self._titles.items():
            moved = [k for k in self.rows if BY_KEY[k].group == group
                     and stack.source(k) is not Layer.BUILT_IN]
            title.setText(f"{group}  ({len(moved)} set)" if moved else group)
        self.summary.setText(self.summary_text())

    def summary_text(self) -> str:
        """Return the one-line summary of the tab's effective settings.

        Returns:
            E.g. ``Color · 600 dpi · PNG (lossless) · preset: Album · 1 changed``.
        """
        parts = []
        for definition in for_tab(self.tab):
            if definition.group != BASIC or definition.remember:
                continue
            row = self.rows.get(definition.key)
            shown = row.get() if row is not None else None
            value = self.hub.stack.value(definition.key) if shown is None else shown
            if isinstance(value, bool):
                if value:
                    parts.append(definition.label.lower())
            else:
                parts.append(definition.text(value))
        preset = self.hub.presets.get(self.tab)
        if preset:
            parts.append(f"preset: {preset}")
        changed = sum(BY_KEY[k].tab == self.tab for k in self.hub.stack.layer(Layer.SESSION))
        if changed:
            parts.append(f"{changed} changed")
        return " · ".join(parts)

    def _edited(self, key: str) -> None:
        """Take over a value the user entered.

        Args:
            key: Setting key.
        """
        value = self.rows[key].get()
        if value is None:
            return
        definition = BY_KEY[key]
        try:
            self.hub.stack.set(key, value, Layer.DEFAULT if definition.remember
                               else Layer.SESSION)
        except ValueError as exc:
            self.message.emit(f"{definition.label}: {exc}")
            self.rows[key].put(self.hub.stack.value(key))
            return
        if definition.remember:
            self._report(self.hub.save_defaults())
        self.refresh()
        self.changed.emit(key)

    def reset(self, key: str) -> None:
        """Drop the change of one setting.

        Args:
            key: Setting key.
        """
        self.hub.stack.reset(key)
        self.rows[key].put(self.hub.stack.value(key))
        self.refresh()
        self.changed.emit(key)

    def _report(self, error: str | None) -> None:
        """Show an error text if there is one.

        Args:
            error: Text or None.
        """
        if error is not None:
            self.message.emit(error)

    def value(self, key: str) -> Scalar:
        """Return the effective value of a setting.

        Args:
            key: Setting key.

        Returns:
            The value.
        """
        return self.hub.stack.value(key)


class PresetBar(QWidget):
    """Choose a preset, save the tab's settings as preset or as default."""

    def __init__(self, settings: TabSettings, ask_name: AskName) -> None:
        """Build the bar.

        Args:
            settings: The tab's settings.
            ask_name: Question for the preset name.
        """
        super().__init__()
        self._settings = settings
        self._ask_name = ask_name
        self.combo = QComboBox()
        self.combo.setToolTip("A preset sets all options of this tab at once; your changes "
                              "afterwards are marked 'changed'.")
        self.save_preset = QPushButton("Save as preset ...")
        self.save_default = QPushButton("Save as default")
        self.save_default.setToolTip("Use the current values of this tab at every start")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.addWidget(QLabel("Preset:"))
        top.addWidget(self.combo, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.save_preset)
        buttons.addWidget(self.save_default)
        layout.addLayout(top)
        layout.addLayout(buttons)
        self.reload()
        self.combo.currentIndexChanged.connect(lambda _index: self.choose())
        self.save_preset.clicked.connect(self.ask_and_save)
        self.save_default.clicked.connect(self.as_default)

    def reload(self, select: str = "") -> None:
        """List the presets of the tab.

        Args:
            select: Name to select.
        """
        hub = self._settings.hub
        names = list(hub.files.presets(self._settings.tab)) if hub.files else []
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItem(NO_PRESET, "")
        for name in names:
            self.combo.addItem(name, name)
        self.combo.setCurrentIndex(max(0, self.combo.findData(select)))
        self.combo.blockSignals(False)
        enabled = hub.files is not None
        self.combo.setEnabled(enabled)
        self.save_preset.setEnabled(enabled)
        self.save_default.setEnabled(enabled)

    def choose(self) -> None:
        """Take over the selected preset; the tab's changes are dropped."""
        settings, hub = self._settings, self._settings.hub
        name = str(self.combo.currentData() or "")
        values: dict[str, Scalar] = {}
        if name and hub.files is not None:
            loaded = hub.files.load_preset(hub.files.presets(settings.tab)[name])
            values = loaded.values
            for problem in loaded.problems:
                settings.message.emit(problem)
        hub.stack.set_layer(Layer.PRESET, {**{k: v for k, v in hub.stack.layer(Layer.PRESET)
                                              .items() if BY_KEY[k].tab != settings.tab},
                                           **values})
        hub.presets[settings.tab] = name
        hub.keep_session(settings.tab, False)
        settings.apply()
        settings.message.emit(f"Preset: {name}" if name else "No preset")
        settings.changed.emit("")

    def _current(self) -> dict[str, Scalar]:
        """Return the tab's effective values without remembered settings.

        Returns:
            Key to value.
        """
        settings = self._settings
        return {k: v for k, v in settings.hub.stack.effective(settings.tab).items()
                if not BY_KEY[k].remember}

    def ask_and_save(self) -> None:
        """Save the tab's current values as a named preset and choose it."""
        settings, hub = self._settings, self._settings.hub
        name = self._ask_name(self, "Name of the preset:")
        if not name or hub.files is None:
            return
        try:
            hub.files.save_preset(name.strip(), settings.tab, self._current())
        except OSError as exc:
            settings.message.emit(f"Preset not saved: {exc}")
            return
        self.reload(name.strip())
        self.choose()

    def as_default(self) -> None:
        """Make the tab's current values the defaults of every start."""
        settings, hub = self._settings, self._settings.hub
        built_in = hub.stack.layer(Layer.BUILT_IN)
        defaults = {k: v for k, v in hub.stack.layer(Layer.DEFAULT).items()
                    if BY_KEY[k].tab != settings.tab or BY_KEY[k].remember}
        defaults.update({k: v for k, v in self._current().items() if v != built_in[k]})
        hub.stack.set_layer(Layer.DEFAULT, defaults)
        hub.keep_session(settings.tab, False)
        # the shown values are now the defaults; a preset above them would hide them
        hub.stack.set_layer(Layer.PRESET, {k: v for k, v in hub.stack.layer(Layer.PRESET).items()
                                           if BY_KEY[k].tab != settings.tab})
        hub.presets[settings.tab] = ""
        self.reload()
        error = hub.save_defaults()
        settings.apply()
        settings.message.emit(error or "Saved as default for every start")
