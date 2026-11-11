"""Command line entry point; also the composition root of the application."""

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import scanbench
from scanbench.application.doctor import Doctor
from scanbench.application.first_publication import FirstPublication
from scanbench.application.update_service import Chooser, UpdateService
from scanbench.domain.patch_archive import PatchArchive
from scanbench.domain.version import Version
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.archive_finder import ArchiveFinder
from scanbench.infrastructure.desktop_installer import DesktopInstaller
from scanbench.infrastructure.tool_probe import ToolProbe
from scanbench.infrastructure.update_lock import UpdateLock
from scanbench.infrastructure.version_info import VersionInfo
from scanbench.wiring import release_context

GuiRunner = Callable[[str, AppPaths, bool], int]
"""Starts the GUI: (version text, paths, is installed release) -> exit status."""

DEFAULT_REPO = "peddanet/scanbench"
"""GitHub repository used by ``scanbench publish``."""


def _run_gui(version_text: str, paths: AppPaths, is_release: bool) -> int:
    """Start the Qt GUI; imported lazily so CLI commands work without a display.

    Args:
        version_text: Version shown in the window.
        paths: Resolver of the installation directories.
        is_release: False when running from a source checkout.

    Returns:
        Exit status of the event loop.
    """
    from scanbench.ui.gui_application import GuiApplication  # pylint: disable=C0415

    return GuiApplication(version_text, paths, is_release).run(["scanbench"])


class Cli:
    """Parse the command line and dispatch to the use cases."""

    def __init__(self, paths: AppPaths, version: VersionInfo, gui: GuiRunner,
                 out: Callable[[str], object] = print,
                 ask: Callable[[str], str] = input) -> None:
        """Store the collaborators.

        Args:
            paths: Resolver of the application directories.
            version: Source of the version text.
            gui: Function that starts the GUI.
            out: Function that prints one line.
            ask: Function that asks a question and returns the answer.
        """
        self._paths = paths
        self._version = version
        self._gui = gui
        self._out = out
        self._ask = ask

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
        install = sub.add_parser("install-desktop", help="add the launcher entry and icon")
        install.add_argument("--exec", dest="exec_path", type=Path,
                             help="launcher written into the entry (default: this venv)")
        sub.add_parser("uninstall-desktop", help="remove the launcher entry and icon")
        update = sub.add_parser("update", help="release delivered patch archives and install")
        update.add_argument("--yes", action="store_true", help="apply all, do not ask")
        update.add_argument("--upto", type=Version.parse, help="apply up to this version")
        update.add_argument("--downloads", type=Path, help="folder with the archives")
        update.add_argument("--clone", type=Path, help="maintainer's git clone")
        publish = sub.add_parser("publish", help="first publication of the clone on GitHub")
        publish.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/NAME on GitHub")
        publish.add_argument("--clone", type=Path, help="maintainer's git clone")
        return parser

    def _doctor(self, _args: argparse.Namespace) -> int:
        """Print the diagnosis.

        Args:
            _args: Parsed arguments (unused).

        Returns:
            Exit status of the diagnosis.
        """
        status, lines = Doctor(ToolProbe(), self._paths, self._version.text()).run()
        for line in lines:
            self._out(line)
        return status

    def _desktop(self, args: argparse.Namespace) -> int:
        """Install or remove the launcher entry.

        Args:
            args: Parsed arguments.

        Returns:
            Always 0.
        """
        launcher = getattr(args, "exec_path", None) or Path(sys.prefix) / "bin" / "scanbench"
        # sys.prefix is the venv root; sys.executable must not be resolved, because
        # in a venv it links to the system interpreter outside the venv.
        home = os.environ.get("SCANBENCH_HOME") or None
        installer = DesktopInstaller(self._paths, launcher, home)
        install = args.command == "install-desktop"
        files = installer.install() if install else installer.uninstall()
        for path in files:
            self._out(f"{'written' if install else 'removed'}: {path}")
        return 0

    def _choose(self, args: argparse.Namespace) -> Chooser:
        """Return the selection of archives for an update.

        Args:
            args: Parsed arguments.

        Returns:
            Function that filters the pending archives.
        """
        def choose(pending: list[PatchArchive]) -> list[PatchArchive]:
            """Filter by --upto, by --yes (all) or by asking.

            Args:
                pending: Pending archives, ascending.

            Returns:
                The archives to apply.
            """
            limit = args.upto
            if limit is None and not args.yes:
                answer = self._ask(f"Apply up to version [{pending[-1].version}]: ").strip()
                limit = Version.parse(answer) if answer else None
            return [a for a in pending if limit is None or a.version <= limit]
        return choose

    def _update(self, args: argparse.Namespace) -> int:
        """Run the update workflow.

        Args:
            args: Parsed arguments.

        Returns:
            Exit status of the workflow.
        """
        ctx = release_context(self._paths, args.clone or self._paths.clone_dir, self._out)
        finder = ArchiveFinder(args.downloads or self._paths.downloads_dir)
        lock = UpdateLock(self._paths.release.lock_file)
        return UpdateService(ctx, finder, self._choose(args), lock).run()

    def _publish(self, args: argparse.Namespace) -> int:
        """Run the first publication.

        Args:
            args: Parsed arguments.

        Returns:
            Exit status of the workflow.
        """
        ctx = release_context(self._paths, args.clone or self._paths.clone_dir, self._out)
        return FirstPublication(ctx, args.repo).run()

    def run(self, argv: Sequence[str]) -> int:
        """Execute one command.

        Args:
            argv: Arguments without the program name.

        Returns:
            Exit status.
        """
        args = self.parser().parse_args(list(argv))
        handlers = {"doctor": self._doctor, "install-desktop": self._desktop,
                    "uninstall-desktop": self._desktop, "update": self._update,
                    "publish": self._publish}
        handler = handlers.get(args.command or "gui")
        if handler is not None:
            return handler(args)
        is_release = self._version.checkout_root() is None
        return self._gui(self._version.text(), self._paths, is_release)


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
