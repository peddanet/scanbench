# Installation

Back to: [User documentation](README.md) · [Documentation home](../README.md)

scanbench installs per user into its own virtual environment. Only the
scanner system packages need administrator rights.

## 1. System packages

~~~bash
sudo apt install sane-utils sane-airscan
~~~

| Package | Provides | Why `sudo` |
|---|---|---|
| `sane-utils` | `scanimage`, the SANE command-line frontend scanbench calls | packages are written below `/usr`; `sudo` from your user context, no root shell needed |
| `sane-airscan` | SANE backend for network scanners (eSCL, WSD) | as above |

Package names are those of Debian and Ubuntu (including Pop!_OS). Other
distributions use similar names; `scanimage` must be on `PATH`.

## 2. Install a release

~~~bash
curl -fsSLO https://raw.githubusercontent.com/peddanet/scanbench/main/install.sh
less install.sh
bash install.sh
~~~

| Line | What it does | Privilege |
|---|---|---|
| 1 | downloads the installer; `-f` fail on HTTP errors, `-sS` quiet but show errors, `-L` follow redirects, `-O` keep the file name | normal user |
| 2 | lets you read the script before running it | normal user |
| 3 | finds the newest release tag, creates a venv, installs that release, checks the version, links the launcher and adds the desktop entry | normal user; writes only below your home directory |

A specific release: `bash install.sh v0.1.0`.

## 3. Where the installation goes

| Variable | Default | Meaning |
|---|---|---|
| `SCANBENCH_HOME` | `~/.local/share/scanbench` | root of the installation (venv); if set, configuration and logs move below it too |
| `SCANBENCH_BIN` | `~/.local/bin` | directory of the `scanbench` launcher link |

Example: everything in one folder below `~/scripts`:

~~~bash
export SCANBENCH_HOME=~/scripts/scanbench.d SCANBENCH_BIN=~/scripts
bash install.sh
~~~

Put the `export` line into `~/.profile` so that scanbench finds its
configuration later as well.

## 4. Launcher entry

`install.sh` runs `scanbench install-desktop`, which writes

* `~/.local/share/applications/io.github.peddanet.scanbench.desktop`
* `~/.local/share/icons/hicolor/scalable/apps/io.github.peddanet.scanbench.svg`

scanbench then appears in the application menu of GNOME, KDE Plasma, COSMIC
and other freedesktop desktops. Run the command again after moving the
installation. Remove the entry with `scanbench uninstall-desktop`.

## 5. Update and uninstall

Update: run `bash install.sh` again; it replaces the venv with the newest
release.

Uninstall (normal user, everything is in your home directory):

~~~bash
scanbench uninstall-desktop
rm -r ~/.local/share/scanbench
rm ~/.local/bin/scanbench
~~~

Adjust the paths if you set `SCANBENCH_HOME` or `SCANBENCH_BIN`. Settings in
`~/.config/scanbench` stay unless you delete them as well.
