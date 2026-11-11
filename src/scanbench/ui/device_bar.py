"""Scanner selection shared by all tabs."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from scanbench.domain.device_info import DeviceInfo
from scanbench.domain.device_options import DeviceOptions
from scanbench.infrastructure.scanimage_backend import ScanimageBackend
from scanbench.ui.task_runner import TaskRunner


class DeviceBar(QWidget):
    """Combo box of the SANE devices with a refresh button (Observer subject).

    Device discovery and option reading can take seconds on network
    scanners, so both run in the task runner. Tabs listen to
    ``options_changed`` and adapt their source, mode and resolution lists.
    """

    options_changed = Signal()
    """The selected device or its options changed."""

    message = Signal(str)
    """A status text for the status bar."""

    def __init__(self, scanner: ScanimageBackend, runner: TaskRunner,
                 include_test: bool = False) -> None:
        """Build the widgets.

        Args:
            scanner: SANE adapter.
            runner: Background job runner.
            include_test: Offer SANE's virtual test scanner.
        """
        super().__init__()
        self._scanner = scanner
        self._runner = runner
        self._include_test = include_test
        self._options: DeviceOptions | None = None
        self.combo = QComboBox()
        self.combo.setMinimumContentsLength(30)
        self.refresh_button = QPushButton("Search scanners")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Scanner:"))
        layout.addWidget(self.combo, 1)
        layout.addWidget(self.refresh_button)
        self.refresh_button.clicked.connect(self.refresh)
        self.combo.currentIndexChanged.connect(self._select)

    def refresh(self) -> None:
        """Search the devices in the background."""
        self.refresh_button.setEnabled(False)
        self.message.emit("Searching scanners ...")
        self._runner.run(lambda: self._scanner.devices(self._include_test), self._fill,
                         self._failed)

    def _failed(self, text: str) -> None:
        """Report an error.

        Args:
            text: Error message.
        """
        self.refresh_button.setEnabled(True)
        self.message.emit(text)

    def _fill(self, devices: list[DeviceInfo]) -> None:
        """Show the found devices and select the first.

        Args:
            devices: Found devices.
        """
        self.refresh_button.setEnabled(True)
        self.combo.blockSignals(True)
        self.combo.clear()
        for device in devices:
            self.combo.addItem(device.label, device.name)
        self.combo.blockSignals(False)
        self.message.emit(f"{len(devices)} scanner(s) found" if devices else
                          "No scanner found; check cable, network and 'scanimage -L'")
        self._select()

    def _select(self) -> None:
        """Read the options of the selected device in the background."""
        self._options = None
        device = self.device()
        if device is None:
            self.options_changed.emit()
            return
        self._runner.run(lambda: (device, self._scanner.options(device)), self._loaded,
                         self._failed)

    def _loaded(self, result: tuple[str, DeviceOptions]) -> None:
        """Store the options if the device is still selected.

        Args:
            result: Device name and its options.
        """
        device, options = result
        if device == self.device():
            self._options = options
            self.options_changed.emit()

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
