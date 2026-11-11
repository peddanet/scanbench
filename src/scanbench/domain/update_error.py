"""Error that stops an update or publication with a message for the user."""


class UpdateError(RuntimeError):
    """A step of the release workflow failed; the message says which and why."""
