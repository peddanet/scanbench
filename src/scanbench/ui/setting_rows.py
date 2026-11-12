"""One editable setting: its widget, the badge of its source and a reset button."""

from enum import Enum

from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
                               QToolButton, QWidget)

from scanbench.domain.paper_format import PaperFormat
from scanbench.domain.settings_schema import Scalar, SettingDefinition
from scanbench.domain.settings_stack import Layer

BADGE_STYLE = {Layer.BUILT_IN: "color: gray;", Layer.DEFAULT: "color: gray;",
               Layer.PRESET: "color: #2a7ab0;", Layer.SESSION: "color: #2a7ab0; "
               "font-weight: bold;"}
"""Look of the source badge per layer."""

UNAVAILABLE_STYLE = "color: #c06000; font-weight: bold;"
"""Look of the badge when the scanner does not offer the wanted value."""


def stored(data: object) -> object:
    """Return the value a combo box entry stands for in the settings.

    Args:
        data: Item data: an enum member, a paper format, a number or text.

    Returns:
        The member or format name, or the data itself.
    """
    if isinstance(data, (Enum, PaperFormat)):
        return data.name
    return data


def create_editor(definition: SettingDefinition) -> QWidget:
    """Create the widget for a setting that has none in the tab yet.

    Args:
        definition: The setting.

    Returns:
        Spin box, check box, combo box or line edit.
    """
    if isinstance(definition.default, bool):
        return QCheckBox(definition.label)
    if isinstance(definition.default, int):
        spin = QSpinBox()
        low, high = definition.bounds or (0, 100000)
        spin.setRange(low, high)
        if definition.unit:
            spin.setSuffix(f" {definition.unit}")
        return spin
    if definition.choices:
        combo = QComboBox()
        for label, value in definition.choices:
            combo.addItem(label, value)
        return combo
    return QLineEdit()


class SettingRow(QWidget):
    """The widget of a setting with source badge and reset button.

    The widget is usually created by the tab (combo boxes that follow the
    scanner) and only wrapped here.
    """

    def __init__(self, definition: SettingDefinition, editor: QWidget) -> None:
        """Wrap the editor.

        Args:
            definition: The setting.
            editor: Its widget.
        """
        super().__init__()
        self.definition = definition
        self.editor = editor
        self.badge = QLabel()
        self.reset = QToolButton()
        self.reset.setText("↺")
        self.reset.setToolTip("Back to the value of the preset, your default or the built-in "
                              "value")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(editor, 1)
        layout.addWidget(self.badge)
        layout.addWidget(self.reset)
        tip = f"{definition.help}\nBuilt-in value: {definition.text(definition.default)}"
        editor.setToolTip(tip)

    def get(self) -> Scalar | None:
        """Return the value shown in the widget.

        Returns:
            The value, or None while a combo box is empty.
        """
        editor = self.editor
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, QSpinBox):
            return editor.value()
        if isinstance(editor, QComboBox):
            value = stored(editor.currentData())
            return value if isinstance(value, (str, int)) else None
        if isinstance(editor, QLineEdit):
            return editor.text()
        return None

    def put(self, value: Scalar) -> bool:
        """Show a value without reporting a change.

        Args:
            value: The value.

        Returns:
            False if a combo box does not offer the value (it keeps its entry).
        """
        editor = self.editor
        editor.blockSignals(True)
        try:
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QSpinBox):
                editor.setValue(int(value))
            elif isinstance(editor, QLineEdit):
                editor.setText(str(value))
            elif isinstance(editor, QComboBox):
                index = next((i for i in range(editor.count())
                              if stored(editor.itemData(i)) == value), -1)
                if index < 0:
                    return editor.count() == 0
                editor.setCurrentIndex(index)
        finally:
            editor.blockSignals(False)
        return True

    def show_source(self, source: Layer, wanted: Scalar, offered: bool) -> None:
        """Show where the value comes from.

        Args:
            source: Layer of the effective value.
            wanted: The effective value.
            offered: False if the scanner does not offer it.
        """
        if offered:
            self.badge.setText(source.value)
            self.badge.setStyleSheet(BADGE_STYLE[source])
            self.badge.setToolTip(f"Value from: {source.value}")
        else:
            self.badge.setText("not offered")
            self.badge.setStyleSheet(UNAVAILABLE_STYLE)
            self.badge.setToolTip(f"The scanner does not offer "
                                  f"{self.definition.text(wanted)}; the nearest value is used.")
        font = self.editor.font()
        font.setBold(source is Layer.SESSION)
        self.editor.setFont(font)
        self.reset.setEnabled(source is Layer.SESSION)
