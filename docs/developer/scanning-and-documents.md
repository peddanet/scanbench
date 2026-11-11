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
| `infrastructure/scanimage_backend.py` | `ScanimageBackend` | devices, options, flatbed and batch scans (Adapter) |
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
| flatbed page | `scanimage -d DEVICE --format=png --source=… --mode=… --resolution=… -l 0 -t 0 -x W -y H --output-file=FILE` |
| feeder | same with `--batch=DIR/STEM-%03d.png --batch-start=1`; an empty feeder at the end is the normal end |

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
