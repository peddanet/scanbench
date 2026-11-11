# Printing

Back to: [Developer documentation](README.md) · [Architecture](architecture.md) · [Documentation home](../README.md)

## Modules

| Module | Class | Responsibility |
|---|---|---|
| `domain/printer_info.py` | `PrinterInfo` | queue name, default flag |
| `domain/printer_option.py` | `PrinterOption` | one PPD option parsed from `lpoptions -l` |
| `domain/print_job.py` | `PrintJob` | printer, copies, options |
| `infrastructure/cups_client.py` | `CupsClient` | the CUPS command line clients (Adapter) |
| `ui/print_dialog.py` | `PrintDialog` | printer, copies, fit to page |
| `ui/option_form.py` | `OptionForm` | one combo box per driver option; reports changed options |
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

Reference: [CUPS command-line printing and options](https://openprinting.github.io/cups/doc/options.html).
