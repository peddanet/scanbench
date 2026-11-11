"""Error raised when scanning, saving or printing fails."""


class ScanError(Exception):
    """A device, file or external program could not do what was asked.

    The message is meant for the user and names the cause, e.g. the
    failing program and its last error lines.
    """
