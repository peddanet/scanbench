# Scanner access and documents

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/scan_source.py`, `color_mode.py` | enums | source and colour mode as the user sees them |
| `domain/scan_settings.py` | `ScanSettings` | source, mode, resolution, paper of one scan |
| `domain/paper_format.py` | `PaperFormat` | document sizes, photo presets, A4 frame |
| `domain/device_info.py` | `DeviceInfo` | a device listed by `scanimage -f` |
| `domain/device_options.py` | `DeviceOptions` | options parsed from `scanimage -A`; maps enums to backend names |
| `domain/duplex_order.py` | `DuplexOrder` | feeder order to reading order |
| `domain/pdf_quality.py` | `PdfQuality` | PDF size level and Ghostscript preset |
| `domain/scan_error.py` | `ScanError` | user-facing error |
| `domain/scan_progress.py` | `ScanProgress` | page, pages, percent, elapsed and remaining time, status text |
| `infrastructure/scanimage_backend.py` | `ScanimageBackend` | devices, options, flatbed and batch scans (Adapter) |
| `infrastructure/scan_stream.py` | `ScanStream`, `ProgressParser` | streamed scans with progress, live image and cancel |
| `infrastructure/pnm_assembler.py` | `PnmAssembler` | builds the partial image from a PNM stream (P4, P5, P6) |
| `infrastructure/scan_observer.py` | `ScanObserver` | callbacks for progress and image, cancel event, report interval (Observer) |
| `infrastructure/image_store.py` | `ImageStore` | read, turn and write images with resolution (Pillow) |
| `infrastructure/pdf_writer.py` | `PdfWriter` | img2pdf, then optional Ghostscript reduction (Template Method) |
| `application/document_session.py` | `DocumentSession`, `Page` | pages, edits, manual duplex merge, PDF output |
| `ui/document_tab.py`, `ui/page_list.py`, `ui/settings_panel.py` | `DocumentTab`, `PageList`, `SettingsPanel` | the documents tab |

## Talking to SANE

`ScanimageBackend` calls `scanimage` with argument lists (never through a
shell):

| Purpose | Call |
|---|---|
| list devices | `scanimage -f "%d|%v|%m|%t%n"` |
| read options | `scanimage -d DEVICE -A` |
| flatbed page | `scanimage -d DEVICE --source=… --mode=… --resolution=… -l L -t T -x W -y H --progress --format=pnm` (image on standard output) |
| feeder | same with `--format=png --batch=DIR/STEM-%03d.png --batch-start=1`; an empty feeder at the end is the normal end |

The area is the paper at 0,0 or, for an area scan, the `ScanArea`; both are
clamped to the device maximum.

### Streaming, progress and cancel

~~~mermaid
sequenceDiagram
  participant W as worker thread
  participant S as ScanStream
  participant P as scanimage
  participant G as GUI thread
  W->>S: page(argv, target, dpi, observer)
  S->>P: start (stdout and stderr piped)
  par error output
    P-->>S: "Progress: 12.3%" (CR separated)
  and image
    P-->>S: PNM header, rows
  end
  loop every 0.4 s
    S-->>G: ScanProgress, partial image (via TaskRunner relay)
  end
  G->>S: Cancel sets the event
  S->>P: terminate
  S-->>W: ScanError("scan cancelled")
~~~

The PNM stream is assembled row by row (`PnmAssembler`; missing rows are
white). The finished page is saved as PNG with its resolution. In batch mode
`ProgressParser` follows `Scanning page N` and `Scanned page N.`; cancelling
keeps the finished pages. Remaining time is estimated only for a single page
from 3 % on. Tests use `tests/fake_scanimage.py`, a slow stand-in started
through a `Shell` subclass.

Backends name sources and modes differently (`Automatic Document Feeder`,
`ADF`, `ADF Duplex`, `Lineart` ...). `DeviceOptions` maps the enums to the
backend names by keywords; a continuous resolution range is reduced to
75/150/300/600/1200 dpi. The scan area is clamped to the device maximum.

## PDF output

~~~mermaid
flowchart LR
  pages["pages: raw PNG + quarter turns"] --> render["ImageStore.turned_copy\n(PNG with dpi)"]
  render --> lossless["img2pdf: lossless PDF"]
  lossless -->|Original| out["target file"]
  lossless -->|Screen / E-book / Printer / Prepress| gs["gs -sDEVICE=pdfwrite\n-dPDFSETTINGS=..."]
  gs -->|smaller| out
  gs -->|not smaller| lossless
~~~

The resolution written into each PNG gives the PDF page its physical size.

## Manual duplex

Each scan run is a batch. `merge_last_batches` takes the last two batches
(fronts, then backs in reverse order) and interleaves them with
`DuplexOrder.FRONTS_THEN_BACKS`; both must have the same length.

## Tests

`tests/unit/test_scanimage_backend.py` runs against scripted output and,
when `sane-utils` is installed, against SANE's test device `test` (also in
CI). `tests/scan_fakes.py` provides a scanner that returns prepared images.
