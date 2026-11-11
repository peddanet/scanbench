"""Create the screenshots of the README and the user guide with the real program.

Only the scanner input is simulated: copyright-free sample photos (see
``docs/user/img/samples/SOURCES.md``) are placed on an image of a scanner lid,
and two sample document pages are drawn. Everything else - detection, frame
editor, cropping, page list, print dialog - is the real code.

Run as normal user, from the repository root, with the development venv::

    QT_QPA_PLATFORM=offscreen python tools/screenshots.py
"""

import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PySide6.QtWidgets import QApplication, QWidget

import scanbench

from scanbench.application.document_session import Page
from scanbench.application.photo_session import AlbumOptions, PhotoScan
from scanbench.domain.command_result import CommandResult
from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.scan_source import ScanSource
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.cups_client import CupsClient
from scanbench.infrastructure.scanimage_backend import ScanimageBackend
from scanbench.infrastructure.shell import Shell
from scanbench.ui import workbench as workbench_module
from scanbench.ui.main_window import MainWindow
from scanbench.ui.print_dialog import PrintDialog

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "user" / "img"
SAMPLES = IMG / "samples"
DPI = 150
"""Resolution of the simulated scans."""

DEVICE = DeviceInfo("airscan:w0:Canon MX920 series", "Canon", "MX920 series",
                    "multi-function device")
OPTIONS = DeviceOptions(("Flatbed", "ADF", "ADF Duplex"), ("Color", "Gray"), (150, 300, 600),
                        215.9, 297.0)
"""Device and options as the airscan backend reports them for the reference scanner."""


@dataclass(frozen=True)
class Print:
    """A photo print lying on the glass.

    Attributes:
        file: Sample file name.
        width_mm: Width of the picture area.
        height_mm: Height of the picture area.
        cx_mm: Centre x on the glass.
        cy_mm: Centre y on the glass.
        angle: Skew in degrees, clockwise.
        border: Border colour, or None for a borderless print.
    """

    file: str
    width_mm: float
    height_mm: float
    cx_mm: float
    cy_mm: float
    angle: float
    border: tuple[int, int, int] | None


PRINTS = (
    Print("coffee.jpg", 105, 70, 64, 52, 1.6, (246, 242, 230)),
    Print("cat.jpg", 105, 70, 66, 140, -2.1, None),
    Print("hubble.jpg", 105, 70, 63, 228, 0.7, (205, 205, 200)),
    Print("rocket.jpg", 105, 70, 165, 140, 90.8, (246, 242, 230)),
)
"""Three landscape prints and one print turned by about 90 degrees."""


class ScriptedShell(Shell):
    """Answers the CUPS commands with an example configuration."""

    ANSWERS = {
        ("lpstat", "-e"): "Canon_MX920_series\nOffice_Laser\n",
        ("lpstat", "-d"): "system default destination: Canon_MX920_series\n",
        ("lpoptions",): ("InputSlot/Paper Source: *Auto RearTray Cassette CDTray\n"
                         "MediaType/Media Type: *Plain Glossy PhotoPlusGlossy Printable\n"
                         "PageSize/Page Size: *A4 A5 Letter 4x6 5x7\n"
                         "ColorModel/Color Model: *RGB Gray\n"
                         "CNIJPrintQuality/Quality: Draft *Standard High\n"),
    }

    def run(self, *argv: str, check: bool = True, stdin: str | None = None) -> CommandResult:
        """Return the example answer.

        Args:
            *argv: Command.
            check: Ignored.
            stdin: Ignored.

        Returns:
            The scripted output.
        """
        del check, stdin
        for prefix, text in self.ANSWERS.items():
            if argv[:len(prefix)] == prefix:
                return CommandResult(0, text, "")
        return CommandResult(0, "", "")


class SampleScanner(ScanimageBackend):
    """Reports the reference scanner; scans are never requested."""

    def devices(self, include_test: bool = False) -> list[DeviceInfo]:
        """Return the reference device.

        Args:
            include_test: Ignored.

        Returns:
            The device list.
        """
        del include_test
        return [DEVICE]

    def options(self, device: str) -> DeviceOptions:
        """Return the airscan options of the reference scanner.

        Args:
            device: Ignored.

        Returns:
            The options.
        """
        del device
        return OPTIONS


def _lid(width: int, height: int) -> NDArray[np.uint8]:
    """Draw the slightly uneven white of a scanner lid.

    Args:
        width: Width in pixels.
        height: Height in pixels.

    Returns:
        RGB pixels.
    """
    rng = np.random.default_rng(7)
    shade = np.linspace(0, 4, height)[:, None, None]
    lid = np.full((height, width, 3), (244, 244, 240), dtype=np.float64) - shade
    lid += rng.normal(0, 1.2, lid.shape)
    return np.clip(lid, 0, 255).astype(np.uint8)


def _print_image(item: Print) -> Image.Image:
    """Make the print: picture, optional border, slight paper texture.

    Args:
        item: The print.

    Returns:
        The print as image, in its own orientation.
    """
    mm = DPI / 25.4
    size = (round(item.width_mm * mm), round(item.height_mm * mm))
    with Image.open(SAMPLES / item.file) as source:
        picture = source.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    if item.border is None:
        return picture
    edge = round(4 * mm)
    framed = Image.new("RGB", (size[0] + 2 * edge, size[1] + 2 * edge), item.border)
    framed.paste(picture, (edge, edge))
    return framed


def album_page() -> Image.Image:
    """Simulate a flatbed scan of four prints.

    Returns:
        The scan of the A4 frame.
    """
    mm = DPI / 25.4
    page = Image.fromarray(_lid(round(210 * mm), round(297 * mm)))
    for item in PRINTS:
        photo = _print_image(item).convert("RGBA")
        turned = photo.rotate(-item.angle, resample=Image.Resampling.BICUBIC, expand=True)
        shadow = Image.new("RGBA", turned.size, (0, 0, 0, 0))
        shadow.putalpha(turned.getchannel("A").filter(ImageFilter.GaussianBlur(2)).point(
            lambda a: min(a, 70)))
        corner = (round(item.cx_mm * mm - turned.width / 2),
                  round(item.cy_mm * mm - turned.height / 2))
        page.paste(shadow, (corner[0] + 2, corner[1] + 2), shadow)
        page.paste(turned, corner, turned)
    return page


def _letter(heading: str, paragraphs: tuple[str, ...]) -> Image.Image:
    """Draw one sample letter page with header, address block, text and table.

    Args:
        heading: Subject line.
        paragraphs: Body text.

    Returns:
        The page at DPI.
    """
    mm = DPI / 25.4
    page = Image.new("RGB", (round(210 * mm), round(297 * mm)), (252, 252, 249))
    draw = ImageDraw.Draw(page)
    big, body = (ImageFont.load_default(size=round(s * mm)) for s in (6.0, 3.6))
    draw.rectangle((0, 0, page.width, 22 * mm), fill=(30, 70, 120))
    draw.text((20 * mm, 7 * mm), "Example Energy Supplier", fill=(255, 255, 255), font=big)
    for row, text in enumerate(("Jane Sample", "1 Example Street", "12345 Sampletown")):
        draw.text((20 * mm, (40 + row * 5) * mm), text, fill=(30, 30, 30), font=body)
    draw.text((20 * mm, 70 * mm), heading, fill=(10, 10, 10), font=big)
    y = 85 * mm
    for paragraph in paragraphs:
        line = ""
        for word in paragraph.split():
            if draw.textlength(f"{line} {word}", font=body) > 170 * mm:
                draw.text((20 * mm, y), line, fill=(40, 40, 40), font=body)
                line, y = word, y + 5.5 * mm
            else:
                line = f"{line} {word}".strip()
        draw.text((20 * mm, y), line, fill=(40, 40, 40), font=body)
        y += 10 * mm
    for row in range(5):
        top = y + row * 8 * mm
        draw.rectangle((20 * mm, top, 190 * mm, top + 8 * mm), outline=(120, 120, 120))
        draw.text((23 * mm, top + 2 * mm), f"Item {row + 1}", fill=(40, 40, 40), font=body)
        draw.text((160 * mm, top + 2 * mm), f"{(row + 3) * 17}.00", fill=(40, 40, 40),
                  font=body)
    return page


def document_pages() -> list[Image.Image]:
    """Draw the front and back of a sample letter (fictitious sender).

    Returns:
        Two pages at DPI.
    """
    text = ("This sample page was drawn by tools/screenshots.py. It stands for a "
            "scanned letter: scanbench shows every page as thumbnail and large "
            "preview, and saves all pages as one PDF in the chosen size.")
    return [_letter("Annual statement 2026", (text, text)),
            _letter("Statement, page 2", (text,))]


def _grab(widget: QWidget, name: str) -> None:
    """Save a screenshot of a widget.

    Args:
        widget: The widget.
        name: File name below the image folder.
    """
    QApplication.processEvents()
    widget.grab().save(str(IMG / name))
    print(f"written: docs/user/img/{name}")


def _show_detection(bench: workbench_module.Workbench, scan: Path) -> PhotoScan:
    """Detect the prints and turn the sideways print upright, as a user would.

    Args:
        bench: The workbench.
        scan: The simulated scan.

    Returns:
        The scan with its regions, waiting for confirmation.
    """
    found = bench.photos._session.detect(scan, DPI, snap=False)  # pylint: disable=W0212
    bench.photos._detected(found)  # pylint: disable=protected-access
    view = bench.photos.editor.view
    turned = max(range(len(view.regions)), key=lambda i: view.regions[i].cx)
    view.change(turned, lambda r: replace(r, quarter_turns=3))
    return found


def result_strip(scan: Path, photos: list[Path]) -> None:
    """Draw "flatbed scan -> single photos" from the real output files.

    Args:
        scan: The simulated scan.
        photos: The saved photos.
    """
    height = 520
    with Image.open(scan) as source:
        page = source.convert("RGB")
    page.thumbnail((height, height))
    canvas = Image.new("RGB", (page.width + 120 + 2 * 310, height), (255, 255, 255))
    canvas.paste(page, (0, 0))
    left = page.width + 20
    ImageDraw.Draw(canvas).polygon([(left, height / 2 - 30), (left + 70, height / 2),
                                    (left, height / 2 + 30)], fill=(0, 120, 215))
    for index, path in enumerate(photos):
        with Image.open(path) as source:
            tile = source.convert("RGB")
        tile.thumbnail((300, 240))
        canvas.paste(tile, (page.width + 120 + (index % 2) * 310, 10 + (index // 2) * 255))
    canvas.save(IMG / "photo-album-result.png")
    print("written: docs/user/img/photo-album-result.png")


def _documents(bench: workbench_module.Workbench, work: Path) -> None:
    """Fill the documents tab with the two sample pages.

    Args:
        bench: The workbench.
        work: Temporary directory.
    """
    session = bench.documents._session  # pylint: disable=protected-access
    for number, image in enumerate(document_pages(), start=1):
        path = work / f"doc-{number}.png"
        image.save(path, dpi=(DPI, DPI))
        session.pages.append(Page(path, DPI, 0, 1))
    bench.documents.pages.redraw(0)
    source = bench.documents.panel.source
    if source is not None:
        source.setCurrentIndex(source.findData(ScanSource.ADF_DUPLEX))


def _photos(bench: workbench_module.Workbench, work: Path, window: MainWindow) -> None:
    """Make the frame-editor screenshot and the result strip.

    Args:
        bench: The workbench.
        work: Temporary directory.
        window: The main window.
    """
    scan = work / "album.png"
    album_page().save(scan, dpi=(DPI, DPI))
    _show_detection(bench, scan)
    photos = bench.photos._session.accept(  # pylint: disable=protected-access
        AlbumOptions(work / "album"))
    found = _show_detection(bench, scan)
    view = bench.photos.editor.view      # select the turned print: grips and values
    view.set_regions(view.regions, max(range(len(view.regions)),
                                       key=lambda i: view.regions[i].cx))
    window.show_message(f"{len(found.regions)} photo(s) detected; please confirm")
    _grab(window, "photo-frame-editor.png")
    result_strip(scan, photos)


def _print_dialog(window: MainWindow, work: Path) -> None:
    """Make the print-dialog screenshot with example driver options.

    Args:
        window: Parent window.
        work: Temporary directory.
    """
    dialog = PrintDialog(CupsClient(ScriptedShell(work)), "Print 4 photo(s)", window, True)
    for key, value in (("InputSlot", "RearTray"), ("MediaType", "PhotoPlusGlossy"),
                       ("PageSize", "4x6")):
        dialog.options.choices[key].setCurrentText(value)
    dialog.show()
    _grab(dialog, "print-dialog.png")


def main() -> int:
    """Create all screenshots.

    Returns:
        Exit status.
    """
    app = QApplication(sys.argv)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        setattr(workbench_module, "ScanimageBackend", SampleScanner)  # reference device
        bench = workbench_module.build_workbench(AppPaths({"SCANBENCH_HOME": tmp}, work))
        window = MainWindow(scanbench.__version__, tabs=(bench.documents, bench.photos),
                            header=bench.devices)
        window.resize(1280, 820)
        window.show()
        bench.devices.refresh()
        for _ in range(3):
            bench.runner.wait()
            app.processEvents()
        _documents(bench, work)
        window.show_message("2 page(s) scanned; 2 in total")
        _grab(window, "documents-tab.png")
        window.tabs.setCurrentIndex(1)
        _photos(bench, work, window)
        _print_dialog(window, work)
        bench.close()
    del app
    return 0


if __name__ == "__main__":
    sys.exit(main())
