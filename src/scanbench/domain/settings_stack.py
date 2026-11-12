"""Effective setting values over the layers built-in, default, preset and session."""

from enum import Enum

from scanbench.domain.settings_schema import BY_KEY, Scalar


class Layer(Enum):
    """Where a value comes from, lowest priority first; the value is the badge text."""

    BUILT_IN = "built-in"
    DEFAULT = "default"
    PRESET = "preset"
    SESSION = "changed"


class SettingsStack:
    """Resolve each setting from the highest layer that sets it (Chain of Responsibility).

    Built-in values come from the schema. ``default`` holds the user's saved
    defaults (``settings.toml``), ``preset`` the chosen preset, ``session`` the
    changes made in the running program.
    """

    def __init__(self) -> None:
        """Start with the built-in values only."""
        self._layers: dict[Layer, dict[str, Scalar]] = {layer: {} for layer in Layer}
        self._layers[Layer.BUILT_IN] = {k: d.default for k, d in BY_KEY.items()}

    def layer(self, layer: Layer) -> dict[str, Scalar]:
        """Return a copy of the values of one layer.

        Args:
            layer: The layer.

        Returns:
            Key to value.
        """
        return dict(self._layers[layer])

    def set_layer(self, layer: Layer, values: dict[str, Scalar]) -> None:
        """Replace the values of a layer (not the built-in one).

        Args:
            layer: Default, preset or session.
            values: Key to value; unknown keys are ignored.

        Raises:
            ValueError: For the built-in layer.
        """
        if layer is Layer.BUILT_IN:
            raise ValueError("the built-in values are fixed")
        self._layers[layer] = {k: v for k, v in values.items() if k in BY_KEY}

    def source(self, key: str) -> Layer:
        """Return the layer the effective value comes from.

        Args:
            key: Setting key.

        Returns:
            The highest layer that sets it.
        """
        return next(layer for layer in reversed(Layer) if key in self._layers[layer])

    def value(self, key: str) -> Scalar:
        """Return the effective value.

        Args:
            key: Setting key.

        Returns:
            The value of the highest layer that sets it.
        """
        return self._layers[self.source(key)][key]

    def below(self, key: str) -> Scalar:
        """Return the value a reset would bring back (ignoring the session).

        Args:
            key: Setting key.

        Returns:
            The effective value without the session layer.
        """
        return next(self._layers[layer][key] for layer in reversed(Layer)
                    if layer is not Layer.SESSION and key in self._layers[layer])

    def set(self, key: str, value: Scalar, layer: Layer = Layer.SESSION) -> None:
        """Change one value; a value equal to the one below removes the change.

        Args:
            key: Setting key.
            value: New value (checked against the schema).
            layer: Session for a change in the form, default for remembered options.
        """
        value = BY_KEY[key].check(value)
        if layer is Layer.SESSION and value == self.below(key):
            self._layers[Layer.SESSION].pop(key, None)
        else:
            self._layers[layer][key] = value
            if layer is not Layer.SESSION:
                self._layers[Layer.SESSION].pop(key, None)

    def reset(self, key: str) -> None:
        """Drop the change of the running program.

        Args:
            key: Setting key.
        """
        self._layers[Layer.SESSION].pop(key, None)

    def effective(self, tab: str) -> dict[str, Scalar]:
        """Return the effective values of one tab.

        Args:
            tab: ``documents`` or ``photos``.

        Returns:
            Key to value for every setting of the tab.
        """
        return {k: self.value(k) for k, d in BY_KEY.items() if d.tab == tab}
