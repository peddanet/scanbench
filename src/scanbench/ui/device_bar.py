"""Scanner selection shared by all tabs."""

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.infrastructure.device_cache import DeviceCache, KnownDevices
from scanbench.infrastructure.scanimage_backend import ScanimageBackend
from scanbench.ui.task_runner import TaskRunner


@dataclass
class DeviceSource:
    """Where the device bar gets its devices from.

    Attributes:
        scanner: SANE adapter.
        runner: Background job runner.
        include_test: Offer SANE's virtual test scanner.
        cache: Devices remembered from the last run, or None.
    """

    scanner: ScanimageBackend
    runner: TaskRunner
    include_test: bool = False
    cache: DeviceCache | None = None


class DeviceBar(QWidget):
    """Combo box of the SANE devices with a search button (Observer subject).

    Device search and option reading can take seconds on network scanners,
    so both run in the task runner. With a cache the bar starts with the
    devices and options of the last run (``restore``) while the search runs
    in the background; a device chosen before the search has confirmed it is
    checked by reading its options. Tabs listen to ``options_changed`` and
    adapt their source, mode and resolution lists.
    """

    options_changed = Signal()
    """The selected device or its options changed."""

    message = Signal(str)
    """A status text for the status bar."""

    def __init__(self, scanner: ScanimageBackend, runner: TaskRunner,
                 include_test: bool = False, cache: DeviceCache | None = None) -> None:
        """Build the widgets.

        Args:
            scanner: SANE adapter.
            runner: Background job runner.
            include_test: Offer SANE's virtual test scanner.
            cache: Devices remembered from the last run, or None for none.
        """
        super().__init__()
        self._source = DeviceSource(scanner, runner, include_test, cache)
        self._known = KnownDevices()
        self._searched = False          # the device list comes from a search of this run
        self._options: DeviceOptions | None = None
        # device to select after the search, e.g. the one used before a release switch
        self.preferred: str | None = None
        self.combo = QComboBox()
        self.combo.setMinimumContentsLength(30)
        self.refresh_button = QPushButton("Search scanners")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Scanner:"))
        layout.addWidget(self.combo, 1)
        layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self._search_again)
        self.combo.currentIndexChanged.connect(lambda _index: self._select(check=True))

    def restore(self) -> None:
        """Show the devices of the last run at once, with their remembered options."""
        if self._source.cache is None:
            return
        self._known = self._source.cache.load()
        if not self._known.devices:
            return
        self._show(self._known.devices, self.preferred or self._known.selected)
        self.message.emit(f"{len(self._known.devices)} scanner(s) known from the last run; "
                          "searching in the background ...")
        self._select(check=False)

    def refresh(self) -> None:
        """Search the devices in the background."""
        self.refresh_button.setEnabled(False)
        if not self._known.devices:
            self.message.emit("Searching scanners ...")
        self._source.runner.run(lambda: self._source.scanner.devices(self._source.include_test),
                                self._fill, self._failed)

    def _search_again(self) -> None:
        """Search on request; the options of the selected device are read anew."""
        device = self.device()
        if device is not None:
            self._known.options.pop(device, None)
        self.message.emit("Searching scanners ...")
        self.refresh()

    def _failed(self, text: str) -> None:
        """Report an error.

        Args:
            text: Error message.
        """
        self.refresh_button.setEnabled(True)
        self.message.emit(text)

    def _show(self, devices: list[DeviceInfo], wanted: str | None) -> bool:
        """Fill the combo box without reporting a selection.

        Args:
            devices: Devices to list.
            wanted: Device to select if listed.

        Returns:
            True if the selected device changed.
        """
        before = self.device()
        self.combo.blockSignals(True)
        self.combo.clear()
        for device in devices:
            self.combo.addItem(device.label, device.name)
        index = self.combo.findData(wanted)
        if index >= 0:
            self.combo.setCurrentIndex(index)
        self.combo.blockSignals(False)
        return self.device() != before

    def _fill(self, devices: list[DeviceInfo]) -> None:
        """Show the found devices; keep the selected one if it is still there.

        Args:
            devices: Found devices.
        """
        self.refresh_button.setEnabled(True)
        self._searched = True
        current = self.device()
        changed = self._show(devices, self.preferred or current)
        self._known.devices = list(devices)
        self._remember()
        text = (f"{len(devices)} scanner(s) found" if devices else
                "No scanner found; check cable, network and 'scanimage -L'")
        if current is not None and self.combo.findData(current) < 0:
            text += f"; {current} is no longer reachable"
        self.message.emit(text)
        if changed or self._options is None:
            self._select(check=False)

    def _select(self, check: bool) -> None:
        """Take the options of the selected device; read them if needed.

        Args:
            check: Read the options even if they are remembered, because the
                user chose a device the search of this run has not confirmed.
        """
        device = self.device()
        self._options = self._known.options.get(device) if device else None
        if device is None or self._options is not None:
            self._remember()
            self.options_changed.emit()
            if device is None or not check or self._searched:
                return
        self._source.runner.run(lambda: (device, self._source.scanner.options(device)),
                                self._loaded, self._unreachable)

    def _unreachable(self, text: str) -> None:
        """Report a device that could not be opened.

        Args:
            text: Error message.
        """
        self.message.emit(f"Scanner not reachable: {text}")

    def _loaded(self, result: tuple[str, DeviceOptions]) -> None:
        """Store the options; report them if the device is still selected.

        Args:
            result: Device name and its options.
        """
        device, options = result
        changed = self._known.options.get(device) != options
        self._known.options[device] = options
        if device == self.device():
            self._options = options
            self._remember()
            if changed:
                self.options_changed.emit()

    def _remember(self) -> None:
        """Write the known devices, the selection and the options to the cache."""
        if self._source.cache is not None:
            self._known.selected = self.device() or self._known.selected
            self._source.cache.save(self._known)

    def device(self) -> str | None:
        """Return the selected SANE device name.

        Returns:
            The name, or None if no device is selected.
        """
        data = self.combo.currentData()
        return str(data) if data else None

    def options(self) -> DeviceOptions | None:
        """Return the options of the selected device.

        Returns:
            The options, or None while they are unknown.
        """
        return self._options
