# Printing

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/printer_info.py` | `PrinterInfo` | queue name, default flag |
| `domain/printer_option.py` | `PrinterOption` | one PPD option parsed from `lpoptions -l` |
| `domain/print_job.py` | `PrintJob` | printer, copies, options |
| `domain/print_labels.py` | functions | readable labels for choices; paper sizes from PPD names, PWG self-describing names (`na_index-4x6_4x6in`) and points (`w288h432`); photo sizes marked |
| `infrastructure/cups_client.py` | `CupsClient` | the CUPS command line clients (Adapter) |
| `ui/print_dialog.py` | `PrintDialog` | printer, copies, fit to page |
| `ui/option_form.py` | `OptionForm`, `fill_choices` | one combo box per driver option (label as text, keyword as item data); photo sizes after a separator; reports changed options |
| `ui/dialogs.py` | `Dialogs`, `print_asker` | modal questions, replaceable in tests |

## Calls

| Purpose | Call |
|---|---|
| queues | `lpstat -e` |
| default queue | `lpstat -d` (`system default destination: NAME`) |
| driver options | `lpoptions -p NAME -l`; lines `Key/Label: *Default Other ...` |
| print | `lp -d NAME -n COPIES -o key=value ... -- FILE ...`; job ID from `request id is NAME-N` |

Documents are printed from a lossless temporary PDF; `lp` hands the data to
the scheduler before it returns, so the temporary file may be removed
afterwards. Photos are printed as image files.

## Why the command line clients

They exist on every desktop installation (`cups-client`), need no compiled
Python binding and show the same options as the system dialog. Options of the
PPD are shown in driver order, with paper source, media type, page size,
colour, quality and duplex first.

### Labels for driver keywords

| Keyword form | Example | Size from |
|---|---|---|
| PWG self-describing name | `na_index-4x6_4x6in`, `iso_a6_105x148mm`, `oe_photo-l_3.5x5in` | the last field (`WxH` with unit `in` or `mm`) |
| PPD name in inches | `4x6`, `Photo5x7`, `3.5x5` | width x height in inches |
| points | `w288h432` | 1/72 inch |
| known name | `A4`, `Letter`, `Hagaki`, `PhotoL`, `2L` | table `KNOWN_SIZES` |

A suffix `.Borderless`, `.FB` or `.bl` marks borderless variants. A size
within 1 mm of a photo print size is labelled as photo. Unknown keywords
are split into words (`PhotographicGlossy` → "Photographic glossy").

References: [CUPS command-line printing and options](https://openprinting.github.io/cups/doc/options.html) ·
[PWG 5101.1 Media Standardized Names 2.0](https://ftp.pwg.org/pub/pwg/candidates/cs-pwgmsn20-20130328-5101.1.pdf) ·
[CUPS media table `pwg-media.c`](https://android.googlesource.com/platform/external/libcups/+/android-9.0.0_r21/cups/pwg-media.c)
