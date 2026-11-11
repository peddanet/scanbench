# scanbench

Document and photo-album scanning for Linux, built on SANE.

> **Status: milestone M0 (version 0.1.0).** The repository skeleton, the
> quality gates, the CI and the desktop integration are in place; the window
> opens, but scanning arrives with milestones M1 to M3. See the
> [roadmap](docs/concept/README.md#roadmap).

![scanbench main window, milestone M0](docs/user/img/main-window-m0.png)

## What scanbench will do

* **Documents:** A4, A5 and A6 from the flatbed or the document feeder,
  duplex for A4, 150/300/600 dpi, colour or grey, as PDF; back pages are
  rotated and ordered automatically, oversized PDFs can be shrunk.
* **Photo albums:** put several photos on the glass, scan once at 300 or
  600 dpi; scanbench finds each photo, straightens and crops it and saves it
  as lossless PNG or as JPEG into one album folder, batch after batch. The
  finished album can be packed as an archive or uploaded with rclone.
* **Any freedesktop desktop:** GNOME, KDE Plasma, COSMIC and others, on
  Wayland and X11.

The first tested device is a Canon PIXMA MX925 over the network
(sane-airscan); the scanner access is encapsulated, so other SANE devices can
be added through device profiles.

## Updates

Every release is installed into its own environment; an open scanbench window
switches to a newly installed release as soon as it is idle. For the
maintainer, `scanbench update` turns delivered patches into releases with all
quality gates and CI runs: see [Updating](docs/user/updating.md).

## Quick start

~~~bash
sudo apt install sane-utils sane-airscan
curl -fsSLO https://raw.githubusercontent.com/peddanet/scanbench/main/install.sh
bash install.sh
~~~

Details, privilege levels and the per-user installation layout are in the
[installation guide](docs/user/installation.md). Installation works once the
first release tag exists.

## Documentation

| Start here | For |
|---|---|
| [Documentation home](docs/README.md) | overview of all documents |
| [User documentation](docs/user/README.md) | installing and using scanbench |
| [Developer documentation](docs/developer/README.md) | architecture, coding standard, quality gates, CI, releases |
| [Concept](docs/concept/README.md) | design rationale, requirements, roadmap |

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). In short: git-flow branches, pull
requests only, all six quality gates green (`tools/check.sh`).

## Licence

Not yet decided (see [decisions](docs/concept/README.md#open-decisions)).
Until a licence file exists, no rights beyond viewing are granted.
