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
milestone M1.

## No icon in the dock or the menu

Run `scanbench install-desktop` again, then check that both files listed in
the [installation guide](installation.md#4-launcher-entry) exist. On Wayland
the window is matched to the entry by its app ID
`io.github.peddanet.scanbench`; the desktop file name must stay unchanged.
