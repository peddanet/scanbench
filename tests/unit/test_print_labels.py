"""Tests of the readable labels of printer driver choices."""

import pytest

from scanbench.domain.print_labels import (choice_label, is_borderless, is_disc_slot,
                                           is_placeholder, media_label, size_label, size_mm,
                                           spaced)
from scanbench.domain.printer_option import PrinterOption


@pytest.mark.parametrize(("keyword", "label", "photo"), [
    ("A4", "A4 (210 x 297 mm)", False),
    ("Letter", "Letter (216 x 279 mm)", False),
    ("4x6", "Photo 10 x 15 cm (4 x 6 in)", True),
    ("4x6.Borderless", "Photo 10 x 15 cm (4 x 6 in), borderless", True),
    ("Photo4x6.FB", "Photo 10 x 15 cm (4 x 6 in), borderless", True),
    ("na_index-4x6_4x6in", "Photo 10 x 15 cm (4 x 6 in)", True),
    ("oe_photo-l_3.5x5in", "Photo L, 9 x 13 cm (3.5 x 5 in)", True),
    ("PhotoL", "Photo L, 9 x 13 cm (3.5 x 5 in)", True),
    ("5x7", "Photo 13 x 18 cm (5 x 7 in, 2L)", True),
    ("Hagaki", "Postcard (Hagaki) 100 x 148 mm", True),
    ("w288h432", "Photo 10 x 15 cm (4 x 6 in)", True),
    ("iso_a6_105x148mm", "A6 (105 x 148 mm)", False),
    ("na_letter_8.5x11in", "Letter (216 x 279 mm)", False),
    ("custom_min_1x1in", "Custom (25 x 25 mm)", False),
    ("w100h200", "Custom (35 x 71 mm)", False),
    ("Env10", "Env10 (105 x 241 mm)", False),
    ("SomethingElse", "Something else", False),
])
def test_size_labels(keyword: str, label: str, photo: bool) -> None:
    """Paper keywords of PPD files and PWG names get readable labels.

    Args:
        keyword: Driver keyword.
        label: Expected label.
        photo: Expected photo flag.
    """
    assert size_label(keyword) == (label, photo)


def test_choice_labels() -> None:
    """Trays, duplex, colour and other choices."""
    assert choice_label("InputSlot", "Auto") == "Automatic"
    assert choice_label("InputSlot", "ByPassTray") == "Rear tray (manual feed)"
    assert choice_label("InputSlot", "Tray1") == "Tray 1"
    assert choice_label("Duplex", "DuplexTumble") == "Two-sided, flip on short edge (calendar)"
    assert choice_label("ColorModel", "RGB") == "Colour"
    assert choice_label("MediaType", "PhotographicGlossy") == "Photographic glossy"
    assert choice_label("PageSize", "A5") == "A5 (148 x 210 mm)"
    assert spaced("") == ""
    assert is_disc_slot("CDDVDTray") and is_disc_slot("Disc") and not is_disc_slot("Photo")
    assert is_borderless("A4.FB") and not is_borderless("A4")
    assert size_mm("Unknown") is None


MX920_DRIVERLESS = (
    "PageSize/Media Size: 200x148mm 200x148mm.Borderless 3.5x5 3.5x5.Borderless 4x6 "
    "4x6.Borderless 5x7 5x7.Borderless 8x10 8x10.Borderless *A4 A4.Borderless A5 "
    "A5.Borderless B5 B5.Borderless DoublePostcardRotated.Borderless Env10 Env10.Borderless "
    "EnvDL EnvDL.Borderless Legal Legal.Borderless Letter Letter.Borderless Postcard "
    "Postcard.Borderless Custom.WIDTHxHEIGHT\n"
    "InputSlot/Media Source: *Auto Top Bottom\n"
    "MediaType/Media Type: *Stationery Photographic CustomMediaTypePhotoPaperPlusGlossyIi "
    "CustomMediaTypePhotoPaperProPlatinum CustomMediaTypeMattePhotoPaper "
    "CustomMediaTypeGlossyPhotoPaper CustomMediaTypeHighResolutionPaper "
    "CustomMediaTypeInkJetHagaki CustomMediaTypeHagakiK CustomMediaTypeHagaki Envelope "
    "CustomMediaTypeOtherPhotoPaper CustomMediaTypePhotoPaperPlusSemiGloss "
    "CustomMediaTypePhotoPaperProLuster\n"
    "ColorModel/Print Color Mode: *RGB Gray\n"
    "Duplex/2-Sided Printing: None *DuplexNoTumble DuplexTumble\n"
    "OutputBin/Output Tray: *FaceUp\n"
    "cupsPrintQuality/Print Quality: *Normal High\n")
"""``lpoptions -l`` of a driverless (IPP Everywhere) queue of a PIXMA MX925."""


def test_driverless_mx920_queue() -> None:
    """Every choice of the real queue gets a readable label."""
    options = {o.key: o for o in PrinterOption.parse_all(MX920_DRIVERLESS)}
    sizes = {c: size_label(c) for c in options["PageSize"].choices}
    assert sizes["200x148mm"] == ("200 x 148 mm", False)
    assert sizes["DoublePostcardRotated.Borderless"] == \
        ("Double postcard rotated (148 x 200 mm), borderless", False)
    assert size_label("11x17") == ("11 x 17 in (279 x 432 mm)", False)
    assert sizes["B5"] == ("B5 (182 x 257 mm)", False)
    assert sizes["Postcard.Borderless"] == ("Postcard (Hagaki) 100 x 148 mm, borderless", True)
    assert [c for c, (_l, photo) in sizes.items() if photo] == [
        "3.5x5", "3.5x5.Borderless", "4x6", "4x6.Borderless", "5x7", "5x7.Borderless",
        "8x10", "8x10.Borderless", "Postcard", "Postcard.Borderless"]
    assert is_placeholder("Custom.WIDTHxHEIGHT") and not is_placeholder("A4")
    assert [choice_label("InputSlot", c) for c in options["InputSlot"].choices] == \
        ["Automatic", "Upper cassette (top)", "Lower cassette (bottom)"]
    media = [choice_label("MediaType", c) for c in options["MediaType"].choices]
    assert media[:4] == ["Plain paper", "Photo paper (generic)", "Photo Paper Plus Glossy II",
                         "Photo Paper Pro Platinum"]
    assert "Envelope" in media and "Ink Jet Hagaki" in media
    assert choice_label("OutputBin", "FaceUp") == "Face up"
    assert not any(is_disc_slot(c) for c in options["InputSlot"].choices)
    assert media_label("CustomMediaType") == "Custom media type"
