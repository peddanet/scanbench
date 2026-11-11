"""Options a scanner offers, parsed from ``scanimage -A``."""

import re
from dataclasses import dataclass

from scanbench.domain.color_mode import ColorMode
from scanbench.domain.scan_source import ScanSource

_CHOICES = r"^\s*--{name}\s+(?P<choices>.+?)\s+\["
_RANGE = re.compile(r"^(?:auto\|)?(\d+)\.\.(\d+)")
_EXTENT = r"^\s*-{axis}\s+(?:auto\|)?[\d.]+\.\.(?P<max>[\d.]+)mm"
PREFERRED_DPI = (75, 150, 300, 600, 1200)
"""Resolutions offered when a device reports a continuous range."""

_SOURCE_WORDS = {
    ScanSource.ADF_DUPLEX: ("duplex",),
    ScanSource.ADF: ("adf", "feeder"),
    ScanSource.FLATBED: ("flatbed", "platen", "normal"),
}
_MODE_WORDS = {
    ColorMode.COLOR: ("color", "colour"),
    ColorMode.GRAY: ("gray", "grey"),
    ColorMode.LINEART: ("lineart", "binary", "black"),
}


def _choices(text: str, name: str) -> tuple[str, ...]:
    """Return the ``|``-separated choices of an option.

    Args:
        text: Output of ``scanimage -A``.
        name: Option name without dashes.

    Returns:
        The choices, or an empty tuple.
    """
    match = re.search(_CHOICES.format(name=name), text, re.MULTILINE)
    return tuple(match["choices"].split("|")) if match else ()


def _extent(text: str, axis: str) -> float | None:
    """Return the maximum scan extent of an axis in millimetres.

    Args:
        text: Output of ``scanimage -A``.
        axis: ``x`` or ``y``.

    Returns:
        The maximum, or None if the option is missing.
    """
    match = re.search(_EXTENT.format(axis=axis), text, re.MULTILINE)
    return float(match["max"]) if match else None


@dataclass(frozen=True)
class DeviceOptions:
    """Sources, modes, resolutions and scan area of one device.

    Attributes:
        sources: Backend names of the sources.
        modes: Backend names of the modes.
        resolutions: Offered resolutions in dpi.
        max_width_mm: Maximum scan width, if reported.
        max_height_mm: Maximum scan height, if reported.
    """

    sources: tuple[str, ...]
    modes: tuple[str, ...]
    resolutions: tuple[int, ...]
    max_width_mm: float | None = None
    max_height_mm: float | None = None

    @classmethod
    def parse(cls, text: str) -> "DeviceOptions":
        """Parse the option list of ``scanimage -d DEVICE -A``.

        Args:
            text: Output of the command.

        Returns:
            The options.
        """
        raw = _choices(text, "resolution")
        resolutions: tuple[int, ...] = ()
        if raw:
            spec = raw[0] if len(raw) == 1 else "|".join(raw)
            spec = spec.removesuffix("dpi")
            match = _RANGE.match(spec)
            if match:
                low, high = int(match[1]), int(match[2])
                resolutions = tuple(d for d in PREFERRED_DPI if low <= d <= high)
            else:
                resolutions = tuple(int(v) for v in re.findall(r"\d+", spec))
        return cls(_choices(text, "source"), _choices(text, "mode"), resolutions,
                   _extent(text, "x"), _extent(text, "y"))

    @staticmethod
    def _pick(choices: tuple[str, ...], words: tuple[str, ...],
              avoid: tuple[str, ...] = ()) -> str | None:
        """Return the first choice containing one of the words.

        Args:
            choices: Backend names.
            words: Lower-case words that identify the wanted choice.
            avoid: Lower-case words the choice must not contain.

        Returns:
            The matching backend name, or None.
        """
        for choice in choices:
            low = choice.lower()
            if any(w in low for w in words) and not any(a in low for a in avoid):
                return choice
        return None

    def source_name(self, source: ScanSource) -> str | None:
        """Return the backend name of a source.

        Args:
            source: Wanted source.

        Returns:
            The backend name, or None if the device lacks the source.
        """
        avoid = ("duplex",) if source is ScanSource.ADF else ()
        return self._pick(self.sources, _SOURCE_WORDS[source], avoid)

    def mode_name(self, mode: ColorMode) -> str | None:
        """Return the backend name of a mode.

        Args:
            mode: Wanted mode.

        Returns:
            The backend name, or None if the device lacks the mode.
        """
        return self._pick(self.modes, _MODE_WORDS[mode])

    def available_sources(self) -> list[ScanSource]:
        """Return the sources the device offers.

        Returns:
            Sources in enum order.
        """
        return [s for s in ScanSource if self.source_name(s) is not None]

    def available_modes(self) -> list[ColorMode]:
        """Return the modes the device offers.

        Returns:
            Modes in enum order.
        """
        return [m for m in ColorMode if self.mode_name(m) is not None]
