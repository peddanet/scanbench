"""Where the scanner takes the paper from."""

from enum import Enum


class ScanSource(Enum):
    """Scan source, independent of the backend's option names.

    The backend names differ (``ADF`` with airscan, ``Automatic Document
    Feeder`` with pixma); :class:`DeviceOptions` maps these values to them.
    """

    FLATBED = "Flatbed"
    ADF = "Feeder, one side"
    ADF_DUPLEX = "Feeder, both sides"
