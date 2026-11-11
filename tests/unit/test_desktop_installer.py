"""Tests for DesktopInstaller."""

from pathlib import Path

import pytest

from scanbench.app_info import APP_ID
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.desktop_installer import DesktopInstaller


def _installer(tmp_path: Path, launcher: str = "/opt/sb/bin/scanbench") -> DesktopInstaller:
    """Create an installer that writes below tmp_path."""
    return DesktopInstaller(AppPaths({}, tmp_path), Path(launcher))


def test_install_and_uninstall(tmp_path: Path) -> None:
    """Install writes both files; uninstall removes them; a second run is a no-op.

    Args:
        tmp_path: Temporary directory of the test.
    """
    installer = _installer(tmp_path)
    written = installer.install()
    assert written == [installer.desktop_file, installer.icon_file]
    text = installer.desktop_file.read_text(encoding="utf-8")
    assert "Exec=/opt/sb/bin/scanbench\n" in text
    assert f"Icon={APP_ID}\n" in text
    assert installer.icon_file.read_bytes().startswith(b"<svg")
    assert installer.uninstall() == written
    assert not installer.uninstall()


def test_exec_with_space_is_quoted(tmp_path: Path) -> None:
    """Paths with spaces are quoted as the Desktop Entry spec requires.

    Args:
        tmp_path: Temporary directory of the test.
    """
    assert _installer(tmp_path, "/my dir/scanbench").exec_value() == '"/my dir/scanbench"'


@pytest.mark.parametrize("launcher", ["bin/scanbench", "/a$b/scanbench", '/a"b/x'])
def test_exec_rejects_unsafe_paths(tmp_path: Path, launcher: str) -> None:
    """Relative paths and characters that need escaping are refused.

    Args:
        tmp_path: Temporary directory of the test.
        launcher: Launcher path under test.
    """
    with pytest.raises(ValueError):
        _installer(tmp_path, launcher).exec_value()


def test_exec_with_home_and_spaces(tmp_path: Path) -> None:
    """SCANBENCH_HOME is passed through env, quoted when it contains a space.

    Args:
        tmp_path: Temporary directory of the test.
    """
    env = {"SCANBENCH_HOME": "/my home", "SCANBENCH_BIN": "/b", "EMPTY": ""}
    installer = DesktopInstaller(AppPaths({}, tmp_path), Path("/x/scanbench"), env)
    assert installer.exec_value() == 'env SCANBENCH_BIN=/b "SCANBENCH_HOME=/my home" /x/scanbench'
