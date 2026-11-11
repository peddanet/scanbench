# Printing

Back to: [User documentation](README.md) · [Documentation home](../README.md)

scanbench prints through CUPS, the printing system of Linux desktops. Every
printer set up in CUPS appears in the print dialog, with the options its
driver offers.

## Requirements

~~~bash
sudo apt install cups-client
scanbench printers
~~~

| Line | What it does | Privilege |
|---|---|---|
| 1 | installs `lp`, `lpstat` and `lpoptions` (usually already present on desktops) | `sudo` from your user context |
| 2 | lists every printer, the default printer and its driver options | normal user |

## The print dialog

| Field | Meaning |
|---|---|
| Printer | all CUPS queues; the default printer is preselected |
| Copies | 1 to 99 |
| Scale to fit the page | `-o fit-to-page`; preselected for photos |
| Driver options | one choice per option of the driver (PPD), important ones first: paper source (`InputSlot`), media type, page size, colour, quality, duplex |

Only options you change are sent with the job; everything else keeps the
printer's defaults.

### Paper source on a multifunction printer

Inkjet multifunction devices usually offer several paper sources through
`InputSlot`, for example an automatic choice, the rear tray, the cassette,
and on some models a CD/DVD tray. The exact names come from the driver and
are shown as `scanbench printers` lists them. Typical choices:

| Job | Paper source | Media type | Page size |
|---|---|---|---|
| document on A4 | cassette or automatic | plain paper | A4 |
| photo 10 x 15 cm | photo tray or rear tray | glossy photo paper | 10x15 / 4x6 |
| printable CD/DVD | CD/DVD tray | printable disc | disc size of the driver |

A CD/DVD tray is only offered if the installed driver supports it; the
driverless IPP Everywhere queue of a printer often has fewer options than the
manufacturer's driver.

## References

- [CUPS: command-line printing and options](https://openprinting.github.io/cups/doc/options.html)
- [lp(1)](https://openprinting.github.io/cups/doc/man-lp.html) · [lpoptions(1)](https://openprinting.github.io/cups/doc/man-lpoptions.html)

Terms: [glossary](../glossary.md).
