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

**git-flow** -- branch model with `main`, `develop` and short-lived feature,
release and hotfix branches.
[V. Driessen](https://nvie.com/posts/a-successful-git-branching-model/)

**git format-patch / git am** -- export commits as patch files / apply them as
commits. [git-format-patch](https://git-scm.com/docs/git-format-patch)

**hicolor** -- fallback icon theme every freedesktop desktop searches.
[Icon Theme Specification](https://specifications.freedesktop.org/icon-theme-spec/latest/)

**Keep a Changelog** -- convention for human-readable change logs.
[keepachangelog.com](https://keepachangelog.com/en/1.1.0/)

**Lead document** -- the `README.md` of a documentation area; links every page
of that area.

**Matrix (CI)** -- one job definition run once per value, here per Python version.
[GitHub Docs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations)

**McCabe complexity** -- number of independent paths through a function.
[pylint optional checkers](https://pylint.readthedocs.io/en/latest/user_guide/checkers/extensions.html)

**Mermaid** -- text format for diagrams; GitHub renders it in Markdown.
[mermaid.js.org](https://mermaid.js.org/)

**mypy** -- static type checker for Python. [mypy](https://mypy.readthedocs.io/)

**offscreen platform** -- Qt platform plugin that renders without a display;
used for GUI tests. [pytest-qt troubleshooting](https://pytest-qt.readthedocs.io/en/latest/troubleshooting.html)

**PEP 668** -- marks the system Python as externally managed; packages go into
virtual environments. [PEP 668](https://peps.python.org/pep-0668/)

**pre-push hook** -- script git runs before a push; a non-zero exit stops the
push. [githooks](https://git-scm.com/docs/githooks)

**pycodestyle** -- checker for PEP 8 style. [pycodestyle](https://pycodestyle.pycqa.org/)

**pylint** -- static analyser; scores code from 0 to 10. [pylint](https://pylint.readthedocs.io/)

**PySide6** -- official Python binding of Qt 6. [Qt for Python](https://doc.qt.io/qtforpython-6/)

**pytest-qt** -- pytest plugin for Qt applications. [pytest-qt](https://pytest-qt.readthedocs.io/)

**Quality gate** -- automated check that must pass before a change moves on.

**rclone** -- program that copies files to cloud storage. [rclone](https://rclone.org/docs/)

**SANE** -- Scanner Access Now Easy, the scanner framework of Linux.
[SANE project](http://www.sane-project.org/)

**scanimage** -- command-line frontend of SANE, used by scanbench.
[scanimage(1)](https://manpages.ubuntu.com/manpages/noble/man1/scanimage.1.html)

**Semantic Versioning** -- `MAJOR.MINOR.PATCH` with defined meaning.
[semver.org](https://semver.org/)

**Release switching** -- an open scanbench window restarts into a newly
installed release at a safe moment (no running job).

**Source checkout** -- code run from a git clone instead of an installed
release; scanbench marks it in its version text.

**Symbolic link** -- file system entry that points to another path; scanbench
switches its active release by replacing the link `venv` atomically.
[symlink(7)](https://man7.org/linux/man-pages/man7/symlink.7.html)

**Virtual environment (venv)** -- self-contained Python directory with its own
packages. [venv](https://docs.python.org/3/library/venv.html)

**Wayland app ID** -- identifier compositors match with the desktop file name
to show the right icon.
[QGuiApplication::desktopFileName](https://doc.qt.io/qt-6/qguiapplication.html#desktopFileName-prop)

**XDG base directories** -- standard locations for configuration, data and
state. [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)
