"""Adapter to SANE through the ``scanimage`` command line program."""

from pathlib import Path

from scanbench.domain.command_result import CommandResult
from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.domain.scan_area import ScanArea
from scanbench.domain.scan_error import ScanError
from scanbench.domain.scan_settings import ScanSettings
from scanbench.domain.scan_source import ScanSource
from scanbench.domain.update_error import UpdateError
from scanbench.infrastructure.scan_observer import ScanObserver
from scanbench.infrastructure.scan_stream import ScanStream
from scanbench.infrastructure.shell import Shell

LIST_FORMAT = "%d|%v|%m|%t%n"
"""``scanimage -f`` format: device|vendor|model|type, one per line."""

TEST_DEVICE = DeviceInfo("test", "SANE", "test backend", "virtual device")
"""SANE's virtual scanner; listed on request even if ``dll.conf`` disables it."""


class ScanimageBackend:
    """List devices, read their options and scan pages with ``scanimage``.

    ``scanimage`` is part of every SANE installation (package ``sane-utils``)
    and works with all backends, including ``escl``/``airscan`` network
    scanners and the ``test`` backend used by the tests. Images are written
    as PNG files, so nothing is lost before the user chooses the output.
    """

    def __init__(self, shell: Shell) -> None:
        """Store the command runner.

        Args:
            shell: Runner whose working directory receives no files.
        """
        self._shell = shell

    def _run(self, *argv: str) -> CommandResult:
        """Run ``scanimage`` and translate start errors.

        Args:
            *argv: Arguments after the program name.

        Returns:
            The result, successful or not.

        Raises:
            ScanError: If ``scanimage`` is not installed.
        """
        try:
            return self._shell.run("scanimage", *argv, check=False)
        except UpdateError as exc:
            raise ScanError(f"{exc}; install the package sane-utils") from exc

    @staticmethod
    def _failure(action: str, result: CommandResult) -> ScanError:
        """Build the error for a failed call.

        Args:
            action: What was attempted.
            result: The failed result.

        Returns:
            The error with the last lines of the error output.
        """
        lines = (result.stderr or result.stdout).strip().splitlines()[-2:]
        return ScanError(f"{action} failed: {' | '.join(lines) or 'no message'}")

    def devices(self, include_test: bool = False) -> list[DeviceInfo]:
        """Return the scanners SANE can reach.

        Args:
            include_test: Add SANE's virtual test scanner (for trying out).

        Returns:
            The devices; empty if none is connected.

        Raises:
            ScanError: If ``scanimage`` fails.
        """
        result = self._run("-f", LIST_FORMAT)
        if not result.ok:
            raise self._failure("listing scanners", result)
        found = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) == 4 and parts[0]:
                found.append(DeviceInfo(*parts))
        if include_test and all(d.name != TEST_DEVICE.name for d in found):
            found.append(TEST_DEVICE)
        return found

    def options(self, device: str) -> DeviceOptions:
        """Read sources, modes, resolutions and scan area of a device.

        Args:
            device: SANE device name.

        Returns:
            The options.

        Raises:
            ScanError: If the device cannot be opened.
        """
        result = self._run("-d", device, "-A")
        if not result.ok:
            raise self._failure(f"reading the options of {device}", result)
        return DeviceOptions.parse(result.stdout)

    @staticmethod
    def resolution(settings: ScanSettings, options: DeviceOptions) -> int:
        """Return the resolution actually used: the offered one nearest to the wish.

        Args:
            settings: Wanted settings.
            options: What the device offers.

        Returns:
            Resolution in dpi.
        """
        if not options.resolutions:
            return settings.resolution
        return min(options.resolutions, key=lambda d: abs(d - settings.resolution))

    @classmethod
    def _arguments(cls, device: str, settings: ScanSettings,
                   options: DeviceOptions) -> list[str]:
        """Translate settings into ``scanimage`` arguments.

        Args:
            device: SANE device name.
            settings: Wanted settings.
            options: What the device offers.

        Returns:
            The arguments (without format and output).

        Raises:
            ScanError: If the device lacks the source or mode.
        """
        source = options.source_name(settings.source)
        mode = options.mode_name(settings.mode)
        if source is None or mode is None:
            raise ScanError(f"{device} does not offer {settings.source.value} / "
                            f"{settings.mode.value}")
        args = ["-d", device, f"--source={source}", f"--mode={mode}"]
        if options.resolutions:
            args.append(f"--resolution={cls.resolution(settings, options)}")
        max_w = options.max_width_mm or settings.paper.width_mm
        max_h = options.max_height_mm or settings.paper.height_mm
        area = settings.area or ScanArea(0, 0, settings.paper.width_mm, settings.paper.height_mm)
        area = area.clamped(max_w, max_h)
        return [*args, "-l", f"{area.left:.1f}", "-t", f"{area.top:.1f}",
                "-x", f"{area.width:.1f}", "-y", f"{area.height:.1f}"]

    def scan(self, device: str, settings: ScanSettings, options: DeviceOptions,
             prefix: Path, observer: ScanObserver | None = None) -> list[Path]:
        """Scan one flatbed page or every page in the feeder.

        Args:
            device: SANE device name.
            settings: Wanted settings.
            options: What the device offers.
            prefix: Path prefix of the PNG files, e.g. ``work/scan001``; the
                pages become ``work/scan001-001.png`` and so on. The directory
                must exist; the prefix must be unique within it.
            observer: Receiver of progress and the partial image; with an
                observer the scan can be cancelled.

        Returns:
            The scanned pages in feeder order (front, back, front ... for
            duplex).

        Raises:
            ScanError: If nothing was scanned.
        """
        args = self._arguments(device, settings, options)
        directory, stem = prefix.parent, prefix.name
        if observer is not None:
            stream = ScanStream(self._shell)
            if settings.source is ScanSource.FLATBED:
                return [stream.page(args, directory / f"{stem}-001.png",
                                    self.resolution(settings, options), observer)]
            pages = stream.batch([*args, "--format=png"], directory, stem, observer)
            if not pages:
                raise ScanError("scanning failed: no page was scanned")
            return pages
        args.append("--format=png")
        if settings.source is ScanSource.FLATBED:
            target = directory / f"{stem}-001.png"
            result = self._run(*args, f"--output-file={target}")
            pages = [target] if result.ok and target.exists() else []
        else:
            result = self._run(*args, f"--batch={directory / stem}-%03d.png", "--batch-start=1")
            # An empty feeder at the end of a batch is the normal way to stop.
            pages = sorted(p for p in directory.glob(f"{stem}-*.png") if p.stat().st_size)
        if not pages:
            raise self._failure("scanning", result)
        return pages
