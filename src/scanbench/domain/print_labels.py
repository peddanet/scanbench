"""Readable names for printer driver choices, with photo sizes marked as such.

Drivers name their choices with short keywords: ``4x6.Borderless``,
``iso_a6_105x148mm``, ``DuplexNoTumble``, ``ByPassTray``. The dialog shows
a readable label and keeps the keyword for the print job.
"""

import re

PHOTO_SIZES = (
    ((89.0, 127.0), "Photo L, 9 x 13 cm (3.5 x 5 in)"),
    ((90.0, 130.0), "Photo 9 x 13 cm"),
    ((101.6, 152.4), "Photo 10 x 15 cm (4 x 6 in)"),
    ((100.0, 150.0), "Photo 10 x 15 cm"),
    ((100.0, 148.0), "Postcard (Hagaki) 100 x 148 mm"),
    ((127.0, 177.8), "Photo 13 x 18 cm (5 x 7 in, 2L)"),
    ((130.0, 180.0), "Photo 13 x 18 cm"),
    ((203.2, 254.0), "Photo 20 x 25 cm (8 x 10 in)"),
)
"""Photo print sizes in mm (short side first) and their labels."""

KNOWN_SIZES = {
    "a3": (297.0, 420.0), "a4": (210.0, 297.0), "a5": (148.0, 210.0), "a6": (105.0, 148.0),
    "b5": (182.0, 257.0), "isob5": (176.0, 250.0), "letter": (215.9, 279.4),
    "legal": (215.9, 355.6), "doublepostcardrotated": (148.0, 200.0),
    "hagaki": (100.0, 148.0), "postcard": (100.0, 148.0), "l": (89.0, 127.0),
    "photol": (89.0, 127.0), "2l": (127.0, 177.8), "photo2l": (127.0, 177.8),
    "kg": (101.6, 152.4), "envdl": (110.0, 220.0), "env10": (104.8, 241.3),
    "envc5": (162.0, 229.0),
}
"""Size keywords of PPD files (compared in lower case without "Photo"/"Card");
``B5`` is JIS B5 and ``ISOB5`` is ISO B5, as in the CUPS media table."""

SLOTS = {
    "auto": "Automatic", "main": "Main tray", "cassette": "Cassette (front)",
    "rear": "Rear tray", "manual": "Rear tray (manual feed)",
    "bypasstray": "Rear tray (manual feed)", "manualfeed": "Rear tray (manual feed)",
    "photo": "Photo tray", "phototray": "Photo tray", "disc": "CD/DVD tray",
    "cd": "CD/DVD tray", "cdtray": "CD/DVD tray", "cddvd": "CD/DVD tray",
    "cddvdtray": "CD/DVD tray",
    "disctray": "CD/DVD tray", "alternate": "Alternate tray",
    "top": "Upper cassette (top)", "bottom": "Lower cassette (bottom)",
    "middle": "Middle tray",
}
"""Paper source keywords (lower case, without separators)."""

MEDIA = {"stationery": "Plain paper", "photographic": "Photo paper (generic)",
         "envelope": "Envelope"}
"""Media type keywords of driverless queues (lower case)."""

WORDS = {
    ("Duplex", "None"): "Off (one-sided)",
    ("Duplex", "DuplexNoTumble"): "Two-sided, flip on long edge (book)",
    ("Duplex", "DuplexTumble"): "Two-sided, flip on short edge (calendar)",
    ("ColorModel", "RGB"): "Colour", ("ColorModel", "Gray"): "Grey",
    ("ColorModel", "Grayscale"): "Grey", ("ColorModel", "KGray"): "Black ink only",
    ("ColorModel", "CMYK"): "Colour (CMYK)",
}
"""Fixed labels for single choices."""

_SELF_DESCRIBING = re.compile(r"^[a-z]+_[^_]+_(?P<w>[\d.]+)x(?P<h>[\d.]+)(?P<unit>in|mm)$")
_POINTS = re.compile(r"^w(?P<w>[\d.]+)h(?P<h>[\d.]+)$")
_INCHES = re.compile(r"^(?:photo|card|index)?(?P<w>[\d.]+)x(?P<h>[\d.]+)(?P<mm>mm)?$")
_BORDERLESS = ("borderless", "fb", "bl")


def _key(text: str) -> str:
    """Return text in lower case without separators.

    Args:
        text: A keyword.

    Returns:
        The comparable form.
    """
    return re.sub(r"[^a-z0-9.]", "", text.lower())


def spaced(keyword: str) -> str:
    """Split a CamelCase or dashed keyword into words.

    Args:
        keyword: E.g. ``PhotographicGlossy`` or ``high-gloss``.

    Returns:
        E.g. ``Photographic glossy``.
    """
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[a-zA-Z])(?=[0-9])", " ",
                   keyword.replace("-", " ").replace("_", " "))
    return words[:1].upper() + words[1:].lower() if words else keyword


def size_mm(keyword: str) -> tuple[float, float] | None:
    """Return the size of a paper keyword, short side first.

    Args:
        keyword: E.g. ``A4``, ``4x6``, ``Photo5x7``, ``na_index-4x6_4x6in``,
            ``w288h432`` (points); a suffix like ``.Borderless`` is ignored.

    Returns:
        Width and height in mm, or None if unknown.
    """
    base = re.sub(r"\.(borderless|fb|bl|duplex)$", "", keyword, flags=re.IGNORECASE)
    size: tuple[float, float] | None = None
    if match := _SELF_DESCRIBING.match(base):
        factor = 25.4 if match["unit"] == "in" else 1.0
        size = (float(match["w"]) * factor, float(match["h"]) * factor)
    elif match := _POINTS.match(base):
        size = (float(match["w"]) * 25.4 / 72, float(match["h"]) * 25.4 / 72)
    elif match := _INCHES.match(_key(base)):
        factor = 1.0 if match["mm"] else 25.4
        size = (float(match["w"]) * factor, float(match["h"]) * factor)
    else:
        size = KNOWN_SIZES.get(_key(base)) or KNOWN_SIZES.get(
            re.sub(r"^(photo|card)", "", _key(base)))
    return None if size is None else (min(size), max(size))


def photo_label(size: tuple[float, float]) -> str | None:
    """Return the photo label of a size, if it is a photo print size.

    Args:
        size: Short and long side in mm.

    Returns:
        The label, or None for other sizes.
    """
    for (short, long), label in PHOTO_SIZES:
        if abs(size[0] - short) <= 1.0 and abs(size[1] - long) <= 1.0:
            return label
    return None


def is_borderless(keyword: str) -> bool:
    """Whether a paper keyword stands for borderless printing.

    Args:
        keyword: E.g. ``4x6.Borderless``, ``Photo4x6.FB`` or ``4X6.bl``.

    Returns:
        True for a borderless variant.
    """
    lowered = keyword.lower()
    return any(lowered.endswith("." + suffix) for suffix in _BORDERLESS) or \
        "borderless" in lowered


def size_label(keyword: str) -> tuple[str, bool]:
    """Return the label of a paper size and whether it is a photo size.

    Args:
        keyword: Paper keyword of the driver.

    Returns:
        E.g. ``("Photo 10 x 15 cm (4 x 6 in), borderless", True)`` or
        ``("A4 (210 x 297 mm)", False)``.
    """
    size = size_mm(keyword)
    suffix = ", borderless" if is_borderless(keyword) else ""
    if size is None:
        return spaced(keyword), False
    photo = photo_label(size)
    if photo is not None:
        return photo + suffix, True
    name = re.sub(r"\.(borderless|fb|bl)$", "", keyword, flags=re.IGNORECASE)
    if _SELF_DESCRIBING.match(name):
        kind, middle = name.split("_")[:2]
        name = middle.upper() if kind in ("iso", "jis") else spaced(middle)
        name = "Custom" if kind == "custom" else name
    elif _POINTS.match(name):
        name = "Custom"
    elif match := _INCHES.match(name.lower()):
        unit = "mm" if match["mm"] else "in"
        plain = f"{match['w']} x {match['h']} {unit}"
        return (plain if unit == "mm" else
                f"{plain} ({size[0]:.0f} x {size[1]:.0f} mm)") + suffix, False
    elif re.search(r"[a-z][A-Z]", name):
        name = spaced(name)
    return f"{name} ({size[0]:.0f} x {size[1]:.0f} mm){suffix}", False


def choice_label(option: str, keyword: str) -> str:
    """Return the readable label of one driver choice.

    Args:
        option: Option key, e.g. ``InputSlot``.
        keyword: Choice keyword, e.g. ``ByPassTray``.

    Returns:
        The label.
    """
    if (option, keyword) in WORDS:
        return WORDS[(option, keyword)]
    if option in ("PageSize", "PageRegion", "media"):
        return size_label(keyword)[0]
    if option == "InputSlot":
        return SLOTS.get(_key(keyword).replace(".", ""), spaced(keyword))
    if option == "MediaType":
        return media_label(keyword)
    return spaced(keyword)


def media_label(keyword: str) -> str:
    """Return the label of a media type.

    Driverless queues name vendor media ``CustomMediaTypePhotoPaperPlusGlossyIi``;
    the prefix is removed and the product name keeps its capitals.

    Args:
        keyword: Media type keyword.

    Returns:
        E.g. ``Photo Paper Plus Glossy II``.
    """
    if keyword.lower() in MEDIA:
        return MEDIA[keyword.lower()]
    if keyword.startswith("CustomMediaType") and len(keyword) > len("CustomMediaType"):
        words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", keyword[len("CustomMediaType"):])
        return re.sub(r"\bIi\b", "II", words)
    return spaced(keyword)


def is_placeholder(keyword: str) -> bool:
    """Whether a choice is a template such as ``Custom.WIDTHxHEIGHT``.

    Such a choice cannot be sent as it is; the dialog does not offer it.

    Args:
        keyword: Choice keyword.

    Returns:
        True for a template.
    """
    return keyword.startswith("Custom.")


def is_disc_slot(keyword: str) -> bool:
    """Whether a paper source keyword is the CD/DVD tray.

    Args:
        keyword: Choice of ``InputSlot``.

    Returns:
        True for the disc tray.
    """
    return SLOTS.get(_key(keyword).replace(".", "")) == "CD/DVD tray"
