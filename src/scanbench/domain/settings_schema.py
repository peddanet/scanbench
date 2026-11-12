"""The settings of scanbench, described once as data.

The settings form, the validation of the TOML files, the tooltips and the
options table of the user guide are all made from ``DEFINITIONS``, so the
program and its documentation cannot drift apart (concept "Settings and
sessions", section 4.3).
"""

from dataclasses import dataclass

from scanbench.domain.color_mode import ColorMode
from scanbench.domain.image_format import ImageFormat
from scanbench.domain.paper_format import DOCUMENT_FORMATS
from scanbench.domain.pdf_quality import PdfQuality
from scanbench.domain.scan_source import ScanSource

SCHEMA = 1
"""Version of the file layout of ``settings.toml`` and the presets."""

Scalar = str | int | bool
"""A setting value as stored in TOML."""

TABS = ("documents", "photos")
"""Tables of the settings files, one per tab."""

BASIC = "Basic"
"""Group shown in the tab itself; the other groups are collapsible sections."""


@dataclass(frozen=True)
class SettingDefinition:  # pylint: disable=too-many-instance-attributes  # one table record
    """One option: type, range or choices, default and help text.

    The type is the type of the default (text, whole number or yes/no).

    Attributes:
        key: ``<tab>.<name>``, also the TOML table and key.
        label: Short name in the form.
        group: Section of the form.
        default: Built-in value.
        help: Tooltip: what the option does and what it costs.
        choices: Allowed values and their labels; empty for free values.
        bounds: Smallest and largest number, for whole numbers.
        unit: Unit shown after numbers.
        device: The scanner offers the choices; values it lacks are kept but
            not selectable.
        remember: A change is saved as default at once (e.g. the album folder).
    """

    key: str
    label: str
    group: str
    default: Scalar
    help: str
    choices: tuple[tuple[str, Scalar], ...] = ()
    bounds: tuple[int, int] | None = None
    unit: str = ""
    device: bool = False
    remember: bool = False

    @property
    def tab(self) -> str:
        """Return the tab (TOML table) of the option.

        Returns:
            ``documents`` or ``photos``.
        """
        return self.key.split(".", 1)[0]

    @property
    def name(self) -> str:
        """Return the key within its table.

        Returns:
            The name, e.g. ``jpeg_quality``.
        """
        return self.key.split(".", 1)[1]

    def check(self, value: object) -> Scalar:
        """Return the value if it is valid for this option.

        Args:
            value: Value read from a file or a widget.

        Returns:
            The value.

        Raises:
            ValueError: With the reason if the value is not allowed.
        """
        if type(value) is not type(self.default) \
                or not isinstance(value, (str, int, bool)):     # bool is no int here
            kind = {bool: "true or false", int: "a whole number", str: "text"}
            raise ValueError(f"must be {kind[type(self.default)]}")
        if self.bounds is not None and not self.bounds[0] <= int(value) <= self.bounds[1]:
            raise ValueError(f"must be {self.bounds[0]} to {self.bounds[1]}")
        if self.choices and not self.device and value not in [v for _, v in self.choices]:
            raise ValueError("must be one of " + ", ".join(str(v) for _, v in self.choices))
        return value

    def text(self, value: Scalar) -> str:
        """Return a value as the user reads it.

        Args:
            value: The value.

        Returns:
            E.g. ``E-book (150 dpi)``, ``600 dpi``, ``on``.
        """
        for label, choice in self.choices:
            if choice == value:
                return label
        if isinstance(value, bool):
            return "on" if value else "off"
        return f"{value} {self.unit}".strip()


def _named(members: list[ColorMode] | list[ScanSource] | list[ImageFormat]
           ) -> tuple[tuple[str, Scalar], ...]:
    """Return choices for enum members: their text and their name.

    Args:
        members: Enum members whose value is the display text.

    Returns:
        Label and stored value per member.
    """
    return tuple((str(m.value), m.name) for m in members)


_FORMATS = (("PNG (lossless)", ImageFormat.PNG.name), ("JPEG (smaller)", ImageFormat.JPEG.name))

DEFINITIONS = (
    SettingDefinition("documents.source", "Source", BASIC, ScanSource.FLATBED.name,
                      "Where the paper is taken from: flatbed or document feeder (one or "
                      "both sides).", _named(list(ScanSource)), device=True),
    SettingDefinition("documents.colour", "Colour", BASIC, ColorMode.COLOR.name,
                      "Colour, grey or black and white. Grey and black and white give "
                      "smaller files.", _named(list(ColorMode)), device=True),
    SettingDefinition("documents.resolution", "Resolution", BASIC, 300,
                      "Dots per inch. 300 dpi is enough for text; doubling it quadruples "
                      "pixels, memory and scan time.", unit="dpi", device=True),
    SettingDefinition("documents.paper", "Paper", BASIC, "A4",
                      "Scanned area. The flatbed is at most 215.9 mm wide.",
                      tuple((p.name, p.name) for p in DOCUMENT_FORMATS)),
    SettingDefinition("documents.pdf_size", "PDF size", BASIC, PdfQuality.EBOOK.name,
                      "Reduction of the saved PDF with Ghostscript, always from the "
                      "lossless pages. E-book is small and readable; Original keeps every "
                      "pixel.", tuple((q.label, q.name) for q in PdfQuality)),
    SettingDefinition("photos.colour", "Colour", BASIC, ColorMode.COLOR.name,
                      "Colour or grey for the photos.", _named(list(ColorMode)), device=True),
    SettingDefinition("photos.resolution", "Resolution", BASIC, 600,
                      "Dots per inch of the photo scan. 600 dpi keeps the detail of paper "
                      "prints; 1200 dpi quadruples size and time, mostly without gain.",
                      unit="dpi", device=True),
    SettingDefinition("photos.format", "Format", BASIC, ImageFormat.PNG.name,
                      "PNG keeps every pixel; JPEG files are about five times smaller.",
                      _FORMATS),
    SettingDefinition("photos.album", "Album", BASIC, "~/Pictures/scanbench-album",
                      "Folder of the saved photos; numbering continues after the last "
                      "photo there.", remember=True),
    SettingDefinition("photos.snap", "Fit frames to photo sizes", BASIC, True,
                      "Frames that nearly match a photo size (10 x 15 cm, 9 x 13 cm ...) "
                      "get its exact size; they never grow more than 1 mm per side."),
    SettingDefinition("photos.keep_scans", "Keep full-page scans", BASIC, False,
                      "Also save each full flatbed scan in the album folder "
                      "(subfolder scans)."),
    SettingDefinition("photos.snap_tolerance", "Size tolerance", "Frames", 6,
                      "How far a frame may differ from a photo size, per side, to be "
                      "fitted to it.", bounds=(2, 10), unit="%"),
    SettingDefinition("photos.jpeg_quality", "JPEG quality", "Output", 92,
                      "Higher means fewer artefacts and larger files; 92 is visually "
                      "lossless. Only for the format JPEG.", bounds=(70, 95)),
    SettingDefinition("photos.png_compression", "PNG compression", "Output", 6,
                      "0 = fastest, 9 = smallest. Always lossless; only time and size "
                      "change. Only for the format PNG.", bounds=(0, 9)),
)
"""Every setting, in form order."""

BY_KEY = {d.key: d for d in DEFINITIONS}
"""Definitions by key."""


def for_tab(tab: str) -> list[SettingDefinition]:
    """Return the definitions of one tab, in form order.

    Args:
        tab: ``documents`` or ``photos``.

    Returns:
        The definitions.
    """
    return [d for d in DEFINITIONS if d.tab == tab]
