"""Command line entry point; also the composition root of the application."""

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import scanbench
from scanbench.application.doctor import Doctor
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.desktop_installer import DesktopInstaller
from scanbench.infrastructure.tool_probe import ToolProbe
from scanbench.infrastructure.version_info import VersionInfo

GuiRunner = Callable[[str, list[str]], int]
"""Function that starts the GUI: (version text, Qt argv) -> exit status."""


def _run_gui(version_text: str, argv: list[str]) -> int:
    """Start the Qt GUI; imported lazily so CLI commands work without a display.

    Args:
        version_text: Version shown in the window.
        argv: Command line handed to Qt.

    Returns:
        Exit status of the event loop.
    """
    from scanbench.ui.gui_application import GuiApplication  # pylint: disable=C0415

    return GuiApplication(version_text).run(argv)


class Cli:
    """Parse the command line and dispatch to the use cases."""

    def __init__(self, paths: AppPaths, version: VersionInfo, gui: GuiRunner,
                 out: Callable[[str], object] = print) -> None:
        """Store the collaborators.

        Args:
            paths: Resolver of the application directories.
            version: Source of the version text.
            gui: Function that starts the GUI.
            out: Function that prints one line.
        """
        self._paths = paths
        self._version = version
        self._gui = gui
        self._out = out

    def parser(self) -> argparse.ArgumentParser:
        """Build the argument parser.

        Returns:
            The parser with all subcommands.
        """
        # The raw formatter keeps the version text on one line; install.sh compares it.
        parser = argparse.ArgumentParser(
            prog="scanbench", description="Scan documents and photo albums.",
            formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("--version", action="version",
                            version=f"scanbench {self._version.text()}")
        sub = parser.add_subparsers(dest="command")
        sub.add_parser("gui", help="start the graphical interface (default)")
        sub.add_parser("doctor", help="check version, directories and external programs")
        sub.add_parser("install-desktop", help="add the launcher entry and icon")
        sub.add_parser("uninstall-desktop", help="remove the launcher entry and icon")
        return parser

    def _installer(self) -> DesktopInstaller:
        """Create the installer for the launcher of the running installation.

        ``sys.prefix`` is the root of the active venv. ``sys.executable`` must
        not be resolved: in a venv it is a symlink to the system interpreter,
        whose directory does not contain the ``scanbench`` launcher.

        Returns:
            Installer pointing at ``<venv>/bin/scanbench``.
        """
        launcher = Path(sys.prefix) / "bin" / "scanbench"
        return DesktopInstaller(self._paths, launcher)

    def run(self, argv: Sequence[str]) -> int:
        """Execute one command.

        Args:
            argv: Arguments without the program name.

        Returns:
            Exit status.
        """
        args = self.parser().parse_args(list(argv))
        if args.command == "doctor":
            status, lines = Doctor(ToolProbe(), self._paths, self._version.text()).run()
            for line in lines:
                self._out(line)
            return status
        if args.command in ("install-desktop", "uninstall-desktop"):
            installer = self._installer()
            install = args.command == "install-desktop"
            files = installer.install() if install else installer.uninstall()
            verb = "written" if install else "removed"
            for path in files:
                self._out(f"{verb}: {path}")
            return 0
        # Qt options are taken from the environment (e.g. QT_QPA_PLATFORM).
        return self._gui(self._version.text(), ["scanbench"])


def main(argv: Sequence[str] | None = None) -> int:
    """Wire the real collaborators and run the command line.

    Args:
        argv: Arguments without the program name; defaults to ``sys.argv[1:]``.

    Returns:
        Exit status.
    """
    paths = AppPaths(os.environ, Path.home())
    version = VersionInfo(Path(scanbench.__file__).resolve().parent)
    cli = Cli(paths, version, _run_gui)
    return cli.run(sys.argv[1:] if argv is None else argv)
