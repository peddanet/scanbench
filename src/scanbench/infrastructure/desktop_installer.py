"""Install and remove the per-user launcher entry (desktop file and icon)."""

from importlib import resources
from pathlib import Path

from scanbench.app_info import APP_ID
from scanbench.infrastructure.app_paths import AppPaths

_FORBIDDEN_EXEC_CHARS = '"`$\\'
"""Characters that would need escaping inside a desktop-file Exec key."""


class DesktopInstaller:
    """Write the desktop file and the icon below ``$XDG_DATA_HOME``.

    Everything is written inside the user's home directory, so no root
    rights are needed. Desktop environments watch the applications directory
    and pick up the entry without a restart.
    """

    def __init__(self, paths: AppPaths, exec_path: Path, home: str | None = None) -> None:
        """Store target locations and the program to launch.

        Args:
            paths: Resolver of the target directories.
            exec_path: Absolute path of the ``scanbench`` launcher.
            home: Value of ``SCANBENCH_HOME`` to pass to the program. A program
                started from the menu does not necessarily see variables set
                in ``~/.profile``, so the entry carries the value itself.
        """
        self._paths = paths
        self._exec_path = exec_path
        self._home = home

    @property
    def desktop_file(self) -> Path:
        """Target path of the desktop file.

        Returns:
            ``<applications>/<APP_ID>.desktop``.
        """
        return self._paths.applications_dir / f"{APP_ID}.desktop"

    @property
    def icon_file(self) -> Path:
        """Target path of the scalable icon.

        Returns:
            ``<hicolor>/scalable/apps/<APP_ID>.svg``.
        """
        return self._paths.icon_dir / f"{APP_ID}.svg"

    @staticmethod
    def _quote(text: str) -> str:
        """Quote one Exec argument as the Desktop Entry spec requires.

        Args:
            text: The argument.

        Returns:
            The argument, in double quotes if it contains a space.

        Raises:
            ValueError: If the argument contains characters that would need
                escaping.
        """
        if any(char in text for char in _FORBIDDEN_EXEC_CHARS):
            raise ValueError(f"unsupported characters in launcher entry: {text}")
        return f'"{text}"' if " " in text else text

    def exec_value(self) -> str:
        """Return the Exec value.

        Returns:
            ``[env SCANBENCH_HOME=<home>] <launcher>``, quoted where needed.

        Raises:
            ValueError: If the launcher path is relative or an argument contains
                characters that would need escaping.
        """
        if not self._exec_path.is_absolute():
            raise ValueError(f"launcher path must be absolute: {self._exec_path}")
        launcher = self._quote(str(self._exec_path))
        if self._home:
            return f"env {self._quote(f'SCANBENCH_HOME={self._home}')} {launcher}"
        return launcher

    def render(self) -> str:
        """Fill the packaged template with the launcher path and the app ID.

        Returns:
            The content of the desktop file.
        """
        template = resources.files("scanbench.resources").joinpath("scanbench.desktop.in")
        content = template.read_text(encoding="utf-8")
        return content.replace("@EXEC@", self.exec_value()).replace("@APP_ID@", APP_ID)

    def install(self) -> list[Path]:
        """Write desktop file and icon, replacing older versions.

        Returns:
            The written files.
        """
        icon = resources.files("scanbench.resources").joinpath("icons", f"{APP_ID}.svg")
        self.desktop_file.parent.mkdir(parents=True, exist_ok=True)
        self.icon_file.parent.mkdir(parents=True, exist_ok=True)
        self.desktop_file.write_text(self.render(), encoding="utf-8")
        self.icon_file.write_bytes(icon.read_bytes())
        return [self.desktop_file, self.icon_file]

    def uninstall(self) -> list[Path]:
        """Remove desktop file and icon if present.

        Returns:
            The files that were removed.
        """
        removed = []
        for path in (self.desktop_file, self.icon_file):
            if path.exists():
                path.unlink()
                removed.append(path)
        return removed
