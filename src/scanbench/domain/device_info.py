"""A scanner found by SANE."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfo:
    """One scanner as listed by ``scanimage -f``.

    Attributes:
        name: SANE device name, e.g. ``airscan:w1:Canon MX920 series``.
        vendor: Manufacturer.
        model: Model name.
        kind: Device type, e.g. ``flatbed scanner``.
    """

    name: str
    vendor: str
    model: str
    kind: str

    @property
    def label(self) -> str:
        """Text for the device list.

        Returns:
            ``vendor model (name)``.
        """
        return f"{self.vendor} {self.model} ({self.name})"
