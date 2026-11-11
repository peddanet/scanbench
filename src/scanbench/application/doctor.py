"""Use case ``scanbench doctor``: report version, paths and external programs."""

from collections.abc import Sequence

from scanbench.domain.tool_requirement import ToolRequirement
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.tool_probe import ToolProbe

DEFAULT_REQUIREMENTS = (
    ToolRequirement("scanimage", True, "scanning through SANE", "sane-utils"),
    ToolRequirement("gs", False, "shrinking PDF files", "ghostscript"),
    ToolRequirement("rclone", False, "export to cloud storage", "rclone"),
)
"""Programs checked by default; the package hints refer to Debian/Ubuntu."""


class Doctor:
    """Collect a diagnosis that helps users and bug reports.

    The report lists the version, the resolved directories and every
    external program with its location or the package that provides it.
    """

    def __init__(
        self,
        probe: ToolProbe,
        paths: AppPaths,
        version_text: str,
        requirements: Sequence[ToolRequirement] = DEFAULT_REQUIREMENTS,
    ) -> None:
        """Store the collaborators.

        Args:
            probe: Finder of external programs.
            paths: Resolver of the application directories.
            version_text: Version text including a source-checkout marker.
            requirements: Programs to check.
        """
        self._probe = probe
        self._paths = paths
        self._version_text = version_text
        self._requirements = requirements

    def _tool_lines(self) -> tuple[list[str], bool]:
        """Check every program.

        Returns:
            The report lines and whether all required programs were found.
        """
        lines, complete = [], True
        for req in self._requirements:
            location = self._probe.locate(req.name)
            if location is None:
                complete = complete and not req.required
                found = f"MISSING, install package {req.package_hint}"
            else:
                found = location
            lines.append(f"  {req.name:<10} {req.label():<9} {req.purpose:<26} {found}")
        return lines, complete

    def run(self) -> tuple[int, list[str]]:
        """Build the report.

        Returns:
            Exit status (0 if all required programs exist, else 1) and lines.
        """
        tool_lines, complete = self._tool_lines()
        lines = [
            f"scanbench {self._version_text}",
            "Directories:",
            f"  config     {self._paths.config_dir}",
            f"  logs       {self._paths.log_dir}",
            f"  release    {self._paths.release_dir}",
            "External programs:",
            *tool_lines,
            "Result: " + ("OK" if complete else "required programs missing"),
        ]
        return (0 if complete else 1), lines
