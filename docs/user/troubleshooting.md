# Troubleshooting

Back to: [User documentation](README.md) · [Documentation home](../README.md)

## First step: scanbench doctor

~~~bash
scanbench doctor
~~~

Runs as normal user and changes nothing. It lists the version, the
directories and each external program:

| Program | Importance | Package (Debian/Ubuntu) | Used for |
|---|---|---|---|
| `scanimage` | required | `sane-utils` | all scanning |
| `gs` | optional | `ghostscript` | shrinking PDF files |
| `rclone` | optional | `rclone` | uploading albums to cloud storage |

A missing program is shown with the package to install.

## The scanner is not found

Check from the terminal, as normal user:

~~~bash
scanimage -L
~~~

`-L` lists all devices SANE can see. If your network scanner is missing:
install `sane-airscan`, make sure scanner and computer are in the same
network, and close other scanning programs (for example Document Scanner),
which can hold the device. Device profiles with a fixed address arrive with
milestone M1. `scanbench devices` shows what scanbench sees;
`scanbench devices --test` must at least show SANE's virtual scanner `test`.

## Photos are not found or merged

- Leave a few millimetres between the photos.
- Close the lid; an open lid makes the background dark.
- Very light photos on a white lid: add the frame by hand (right-click on
  free space > Add frame here) and move it into place.

## Printing does not work

~~~bash
lpstat -t
scanbench printers
~~~

| Command | Shows | Privilege |
|---|---|---|
| `lpstat -t` | scheduler state, queues, default printer, waiting jobs | normal user |
| `scanbench printers` | queues as scanbench sees them, with driver options | normal user |

"No printer is set up in CUPS" means no queue exists: add the printer in the
printer settings of your desktop. If an option such as the CD/DVD tray is
missing, the queue uses a driver without it (often the driverless IPP
Everywhere driver).

## No icon in the dock or the menu

Run `scanbench install-desktop` again, then check that both files listed in
the [installation guide](installation.md#4-launcher-entry) exist. On Wayland
the window is matched to the entry by its app ID
`io.github.peddanet.scanbench`; the desktop file name must stay unchanged.
