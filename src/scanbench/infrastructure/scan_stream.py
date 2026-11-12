"""Run ``scanimage`` while reading its progress and its image stream."""

import os
import re
import subprocess
import threading
import time
from pathlib import Path

from PIL import Image

from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_progress import ScanProgress
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.pnm_assembler import PnmAssembler
from scanbench.infrastructure.scan_observer import ScanObserver
from scanbench.infrastructure.shell import Shell

_PROGRESS = re.compile(r"Progress:\s*([\d.]+)%")
_SCANNING = re.compile(r"Scanning page (\d+)")
_SCANNED = re.compile(r"Scanned page (\d+)")


class ProgressParser:
    """Turn the error output of ``scanimage --progress`` into numbers.

    ``scanimage`` writes ``Progress: 12.3%`` lines (separated by carriage
    returns) and, in batch mode, ``Scanning page N`` and ``Scanned page N.``.
    """

    def __init__(self) -> None:
        """Start before the first page."""
        self.page = 1
        self.percent = 0.0
        self.done = 0
        self.messages: list[str] = []
        self._rest = ""

    def feed(self, text: str) -> None:
        """Parse more error output.

        Args:
            text: Decoded output, possibly ending in a partial line.
        """
        lines = re.split(r"[\r\n]", self._rest + text)
        self._rest = lines.pop()
        for line in lines:
            if match := _PROGRESS.search(line):
                self.percent = float(match[1])
            elif match := _SCANNING.search(line):
                self.page, self.percent = int(match[1]), 0.0
            elif match := _SCANNED.search(line):
                self.done = int(match[1])
            elif line.strip():
                self.messages.append(line.strip())

    def failure(self) -> str:
        """Return the last messages for an error report.

        Returns:
            Up to two message lines.
        """
        return " | ".join(self.messages[-2:]) or "no message"


class ScanStream:
    """Start ``scanimage`` and follow it until the page or the batch is done."""

    def __init__(self, shell: Shell) -> None:
        """Store the command runner.

        Args:
            shell: Runner whose ``start`` creates the process.
        """
        self._shell = shell

    def _start(self, argv: list[str]) -> "subprocess.Popen[bytes]":
        """Start the process.

        Args:
            argv: Arguments after the program name.

        Returns:
            The process.

        Raises:
            ScanError: If ``scanimage`` is not installed.
        """
        try:
            return self._shell.start("scanimage", *argv, "--progress")
        except UpdateError as exc:
            raise ScanError(f"{exc}; install the package sane-utils") from exc

    @staticmethod
    def _read_errors(process: "subprocess.Popen[bytes]", parser: ProgressParser) -> None:
        """Feed the error output into the parser until the process ends.

        Args:
            process: The running scan.
            parser: Receiver of the text.
        """
        if process.stderr is None:
            return
        descriptor = process.stderr.fileno()
        for chunk in iter(lambda: os.read(descriptor, 4096), b""):
            parser.feed(chunk.decode(errors="replace"))

    @staticmethod
    def _finish(process: "subprocess.Popen[bytes]", errors: threading.Thread) -> None:
        """Wait for the process and its error reader, then close the pipes.

        Args:
            process: The scan process.
            errors: Thread reading the error output.
        """
        process.wait()
        errors.join(timeout=5)
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()

    @staticmethod
    def _report(observer: ScanObserver, parser: ProgressParser, started: float,
                pages: int | None) -> None:
        """Send one progress report.

        Args:
            observer: Receiver.
            parser: Current state.
            started: Start time.
            pages: Known number of pages, or None.
        """
        if observer.progress is not None:
            observer.progress(ScanProgress(parser.page, pages, parser.percent,
                                           time.monotonic() - started, parser.done))

    def page(self, argv: list[str], target: Path, dpi: int, observer: ScanObserver) -> Path:
        """Scan one flatbed page as PNM stream and save it as PNG.

        Args:
            argv: ``scanimage`` arguments (without format and output).
            target: PNG file to write.
            dpi: Resolution written into the PNG.
            observer: Receiver of progress and partial image.

        Returns:
            The target.

        Raises:
            ScanError: If the scan fails or is cancelled.
        """
        process = self._start([*argv, "--format=pnm"])
        parser, image = ProgressParser(), PnmAssembler()
        errors = threading.Thread(target=self._read_errors, args=(process, parser), daemon=True)
        errors.start()
        started = last = time.monotonic()
        descriptor = process.stdout.fileno() if process.stdout is not None else -1
        for chunk in iter(lambda: os.read(descriptor, 65536), b""):
            image.feed(chunk)
            if observer.cancel.is_set():
                process.terminate()
                self._finish(process, errors)
                raise ScanError("scan cancelled")
            if time.monotonic() - last >= observer.interval:
                last = time.monotonic()
                self._report(observer, parser, started, 1)
                if observer.image is not None and image.rows():
                    observer.image(image.image())
        self._finish(process, errors)
        if process.returncode != 0 or image.height == 0 or image.rows() < image.height:
            raise ScanError(f"scanning failed: {parser.failure()}")
        parser.percent = 100.0
        self._report(observer, parser, started, 1)
        mode = {"P4": "1", "P5": "L", "P6": "RGB"}[image.kind]
        picture = Image.fromarray(image.image()).convert(mode)
        picture.save(target, format="PNG", dpi=(dpi, dpi))
        return target

    def batch(self, argv: list[str], directory: Path, stem: str,
              observer: ScanObserver) -> list[Path]:
        """Scan every sheet in the feeder into PNG files.

        Args:
            argv: ``scanimage`` arguments including ``--format=png``.
            directory: Target directory.
            stem: File name prefix.
            observer: Receiver of progress; cancelling keeps finished pages.

        Returns:
            The finished pages in feeder order.
        """
        process = self._start([*argv, f"--batch={directory / stem}-%03d.png",
                               "--batch-start=1"])
        parser = ProgressParser()
        errors = threading.Thread(target=self._read_errors, args=(process, parser), daemon=True)
        errors.start()
        started = time.monotonic()
        while process.poll() is None:
            if observer.cancel.is_set():
                process.terminate()
                break
            self._report(observer, parser, started, None)
            time.sleep(observer.interval)
        self._finish(process, errors)
        parser.page = max(parser.done, 1)    # the last "Scanning page" is the empty feeder
        self._report(observer, parser, started, None)
        pages = sorted(p for p in directory.glob(f"{stem}-*.png") if p.stat().st_size)
        if observer.cancel.is_set():
            pages = pages[:parser.done]
        return pages
