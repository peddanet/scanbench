# Glossary

Back to: [Documentation home](README.md)

Terms used anywhere in the scanbench documentation, alphabetically. The
concept has a longer glossary of design terms:
[concept glossary](concept/scanbench-concept.md#glossary).

**ADF** -- automatic document feeder; pulls sheets through the scanner. Not
for photos.

**airscan (sane-airscan)** -- SANE backend for network scanners speaking eSCL
or WSD. [sane-airscan](https://github.com/alexpevzner/sane-airscan)

**Annotated tag** -- git tag with author, date and message; marks releases.
[git-tag](https://git-scm.com/docs/git-tag)

**bandit** -- security linter for Python. [bandit](https://bandit.readthedocs.io/)

**Branch coverage** -- share of statements and of taken branches executed by
the tests. [coverage.py](https://coverage.readthedocs.io/en/latest/branch.html)

**Branch protection** -- server rule that blocks direct pushes and merges
without passing checks.
[GitHub Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

**Canny edge detector** -- classic algorithm that marks strong brightness
changes; finds the shadow line around photos.
[OpenCV tutorial](https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html)

**CUPS** -- printing system of Linux and macOS; scanbench uses its command
line clients `lp`, `lpstat`, `lpoptions`.
[CUPS documentation](https://openprinting.github.io/cups/doc/options.html)

**Deskew** -- turning a slightly skewed scan back to horizontal; scanbench
rotates only, so results stay rectangles.

**Desktop entry** -- `.desktop` file that registers a program with menus and
launchers. [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry-spec/latest/)

**docparams** -- pylint extension that requires documented arguments, return
values and exceptions.
[pylint optional checkers](https://pylint.readthedocs.io/en/latest/user_guide/checkers/extensions.html)

**Duplex** -- scanning both sides of a sheet.

**flock** -- Linux advisory file lock; the kernel releases it when the process
ends, so a crashed update leaves no stale lock. [flock(2)](https://man7.org/linux/man-pages/man2/flock.2.html)

**gh (GitHub CLI)** -- command-line client for GitHub: pull requests, workflow
runs, repository settings. [GitHub CLI manual](https://cli.github.com/manual/)

**Ghostscript** -- PostScript and PDF interpreter; its `pdfwrite` device with
`-dPDFSETTINGS` reduces PDF files.
[Ghostscript documentation](https://ghostscript.readthedocs.io/en/latest/VectorDevices.html)

**git format-patch / git am** -- export commits as patch files / apply them as
commits. [git-format-patch](https://git-scm.com/docs/git-format-patch)

**git-flow** -- branch model with `main`, `develop` and short-lived feature,
release and hotfix branches.
[V. Driessen](https://nvie.com/posts/a-successful-git-branching-model/)

**Grip (frame editor)** -- small circle on the selected photo frame; white
grips resize, the orange grip above the top edge rotates the frame.

**hicolor** -- fallback icon theme every freedesktop desktop searches.
[Icon Theme Specification](https://specifications.freedesktop.org/icon-theme-spec/latest/)

**img2pdf** -- converts images to PDF without re-encoding them.
[img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf)

**InputSlot** -- PPD option for the paper source (tray, cassette, CD/DVD tray).

**Keep a Changelog** -- convention for human-readable change logs.
[keepachangelog.com](https://keepachangelog.com/en/1.1.0/)

**Lead document** -- the `README.md` of a documentation area; links every page
of that area.

**Line art** -- 1-bit black-and-white scan mode; smallest files for text.

**Manual duplex** -- two-sided scanning with a one-sided feeder: front sides
first, the turned stack second; the runs are interleaved afterwards.

**Matrix (CI)** -- one job definition run once per value, here per Python version.
[GitHub Docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)

**McCabe complexity** -- number of independent paths through a function.
[pylint optional checkers](https://pylint.readthedocs.io/en/latest/user_guide/checkers/extensions.html)

**Mermaid** -- text format for diagrams; GitHub renders it in Markdown.
[mermaid.js.org](https://mermaid.js.org/)

**Minimum-area rectangle** -- smallest rotated rectangle around a set of
points (`cv2.minAreaRect`); gives position, size and skew of a photo.
[OpenCV](https://docs.opencv.org/4.x/d3/dc0/group__imgproc__shape.html)

**mypy** -- static type checker for Python. [mypy](https://mypy.readthedocs.io/)

**offscreen platform** -- Qt platform plugin that renders without a display;
used for GUI tests. [pytest-qt troubleshooting](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html)

**PDFSETTINGS** -- Ghostscript presets `/screen` (72 dpi images), `/ebook`
(150 dpi), `/printer` and `/prepress` (300 dpi).

**PEP 668** -- marks the system Python as externally managed; packages go into
virtual environments. [PEP 668](https://peps.python.org/pep-0668/)

**PPD** -- PostScript Printer Description; lists the options of a printer
driver as shown by `lpoptions -l`.

**pre-push hook** -- script git runs before a push; a non-zero exit stops the
push. [githooks](https://git-scm.com/docs/githooks)

**pycodestyle** -- checker for PEP 8 style. [pycodestyle](https://pycodestyle.pycqa.org/)

**pylint** -- static analyser; scores code from 0 to 10. [pylint](https://pylint.readthedocs.io/)

**PySide6** -- official Python binding of Qt 6. [Qt for Python](https://doc.qt.io/qtforpython-6/)

**pytest-qt** -- pytest plugin for Qt applications. [pytest-qt](https://pytest-qt.readthedocs.io/)

**Quality gate** -- automated check that must pass before a change moves on.

**rclone** -- program that copies files to cloud storage. [rclone](https://rclone.org/docs/)

**Release switching** -- an open scanbench window restarts into a newly
installed release at a safe moment (no running job).

**SANE** -- Scanner Access Now Easy, the scanner framework of Linux.
[SANE project](http://www.sane-project.org/)

**scanimage** -- command-line frontend of SANE, used by scanbench.
[scanimage(1)](https://manpages.ubuntu.com/manpages/noble/man1/scanimage.1.html)

**Semantic Versioning** -- `MAJOR.MINOR.PATCH` with defined meaning.
[semver.org](https://semver.org/)

**Source checkout** -- code run from a git clone instead of an installed
release; scanbench marks it in its version text.

**Symbolic link** -- file system entry that points to another path; scanbench
switches its active release by replacing the link `venv` atomically.
[symlink(7)](https://man7.org/linux/man-pages/man7/symlink.7.html)

**Test backend (SANE)** -- virtual SANE scanner `test`; delivers test pictures
without hardware. [sane-test(5)](https://manpages.debian.org/sane-test)

**Virtual environment (venv)** -- self-contained Python directory with its own
packages. [venv](https://docs.python.org/3/library/venv.html)

**Wayland app ID** -- identifier compositors match with the desktop file name
to show the right icon.
[QGuiApplication::desktopFileName](https://doc.qt.io/qt-6/qguiapplication.html#desktopFileName-prop)

**XDG base directories** -- standard locations for configuration, data and
state. [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)
