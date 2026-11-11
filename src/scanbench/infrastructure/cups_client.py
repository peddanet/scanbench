"""Adapter to CUPS through ``lpstat``, ``lpoptions`` and ``lp``."""

import re
from pathlib import Path

from scanbench.domain.command_result import CommandResult
from scanbench.domain.printer_info import PrinterInfo
from scanbench.domain.printer_option import PrinterOption
from scanbench.domain.scan_error import ScanError
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.shell import Shell

_DEFAULT = re.compile(r"destination:\s*(\S+)")
_JOB = re.compile(r"request id is (\S+)")


class CupsClient:
    """List printers, read their driver options and print files.

    The command line clients of CUPS (package ``cups-client``) are used
    instead of a Python binding: they exist on every desktop system and
    show the same options as the system print dialog, including paper
    source (e.g. photo tray, cassette, CD/DVD tray), media type and quality.
    """

    def __init__(self, shell: Shell) -> None:
        """Store the command runner.

        Args:
            shell: Command runner.
        """
        self._shell = shell

    def _run(self, *argv: str) -> CommandResult:
        """Run a CUPS client program.

        Args:
            *argv: Program and arguments.

        Returns:
            The successful result.

        Raises:
            ScanError: If the program is missing or fails.
        """
        try:
            result = self._shell.run(*argv, check=False)
        except UpdateError as exc:
            raise ScanError(f"{exc}; install the package cups-client") from exc
        if not result.ok:
            raise ScanError(f"{argv[0]} failed: {(result.stderr or result.stdout).strip()[:200]}")
        return result

    def printers(self) -> list[PrinterInfo]:
        """Return all print queues; the default queue is marked.

        Returns:
            The printers in CUPS order.
        """
        names = self._run("lpstat", "-e").stdout.split()
        match = _DEFAULT.search(self._run("lpstat", "-d").stdout)
        default = match[1] if match else None
        return [PrinterInfo(name, name == default) for name in names]

    def options(self, printer: str) -> list[PrinterOption]:
        """Return the driver options of a printer.

        Args:
            printer: Queue name.

        Returns:
            The options with their current defaults.
        """
        return PrinterOption.parse_all(self._run("lpoptions", "-p", printer, "-l").stdout)

    def print_files(self, printer: str, files: list[Path], copies: int,
                    options: dict[str, str]) -> str:
        """Send files to a printer as one job.

        Args:
            printer: Queue name.
            files: PDF or image files.
            copies: Number of copies.
            options: Driver and job options, e.g. ``{"InputSlot": "PhotoTray"}``.

        Returns:
            The job ID reported by CUPS.

        Raises:
            ScanError: If there is nothing to print or CUPS refuses the job.
        """
        if not files:
            raise ScanError("there is nothing to print")
        args = ["lp", "-d", printer, "-n", str(max(1, copies))]
        for key, value in sorted(options.items()):
            args += ["-o", f"{key}={value}" if value else key]
        result = self._run(*args, "--", *(str(f) for f in files))
        match = _JOB.search(result.stdout)
        return match[1] if match else "submitted"
