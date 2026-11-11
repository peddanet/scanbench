"""Tests for AppPaths."""

from pathlib import Path

from scanbench.infrastructure.app_paths import AppPaths
from scanbench.wiring import release_context

HOME = Path("/home/user")


def test_xdg_defaults() -> None:
    """Without variables the XDG defaults below the home directory apply."""
    paths = AppPaths({}, HOME)
    assert paths.config_dir == HOME / ".config/scanbench"
    assert paths.log_dir == HOME / ".local/state/scanbench/logs"
    assert paths.release_dir == HOME / ".local/share/scanbench"
    assert paths.applications_dir == HOME / ".local/share/applications"
    assert paths.icon_dir == HOME / ".local/share/icons/hicolor/scalable/apps"


def test_absolute_xdg_overrides() -> None:
    """Absolute XDG variables replace the defaults."""
    env = {"XDG_CONFIG_HOME": "/c", "XDG_STATE_HOME": "/s", "XDG_DATA_HOME": "/d"}
    paths = AppPaths(env, HOME)
    assert paths.config_dir == Path("/c/scanbench")
    assert paths.log_dir == Path("/s/scanbench/logs")
    assert paths.applications_dir == Path("/d/applications")


def test_relative_xdg_value_is_ignored() -> None:
    """The XDG specification declares relative values invalid."""
    paths = AppPaths({"XDG_CONFIG_HOME": "relative"}, HOME)
    assert paths.config_dir == HOME / ".config/scanbench"


def test_single_root_layout() -> None:
    """SCANBENCH_HOME moves config, logs and release, but not desktop files."""
    paths = AppPaths({"SCANBENCH_HOME": "/opt/sb.d"}, HOME)
    assert paths.config_dir == Path("/opt/sb.d/config")
    assert paths.log_dir == Path("/opt/sb.d/logs")
    assert paths.release_dir == Path("/opt/sb.d")
    assert paths.applications_dir == HOME / ".local/share/applications"


def test_clone_and_downloads() -> None:
    """Clone and download folder have defaults and overrides."""
    paths = AppPaths({}, HOME)
    assert paths.clone_dir == HOME / "Projects/scanbench"
    assert paths.downloads_dir == HOME / "Downloads"
    paths = AppPaths({"SCANBENCH_CLONE": "/src/sb", "XDG_DOWNLOAD_DIR": "/dl"}, HOME)
    assert paths.clone_dir == Path("/src/sb")
    assert paths.downloads_dir == Path("/dl")
    assert paths.release.root == HOME / ".local/share/scanbench"


def test_release_context_wiring(tmp_path: Path) -> None:
    """The composition root wires all adapters on the clone.

    Args:
        tmp_path: Temporary directory of the test.
    """
    ctx = release_context(AppPaths({}, HOME), tmp_path, out=lambda _line: None)
    assert ctx.git.root == tmp_path
    assert ctx.installer.active_version() is None
