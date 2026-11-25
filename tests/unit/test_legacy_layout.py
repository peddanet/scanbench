"""Tests of the one-time move from the single-root layout (LegacyLayout)."""

import os
from pathlib import Path

from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.legacy_layout import REPORT_FILE, LegacyLayout


def _write(path: Path, text: str = "x") -> Path:
    """Create a file with its folders.

    Args:
        path: File to create.
        text: Content.

    Returns:
        The path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_nothing_to_move(tmp_path: Path) -> None:
    """Without old folders the run reports nothing and writes no report file.

    Args:
        tmp_path: Temporary home directory.
    """
    paths = AppPaths({}, tmp_path)
    assert not LegacyLayout(paths, {}).run()
    assert not (paths.log_dir / REPORT_FILE).exists()


def test_scanbench_home_is_moved_without_overwriting(tmp_path: Path) -> None:
    """All entries of $SCANBENCH_HOME move; existing targets stay; venvs stay.

    Args:
        tmp_path: Temporary home directory.
    """
    paths = AppPaths({}, tmp_path)
    old = tmp_path / "custom.d"
    _write(old / "config" / "settings.toml", "old")
    _write(old / "config" / "presets" / "photos-a.toml")
    _write(old / "logs" / "scanbench.log")
    _write(old / "sessions" / "s1" / "state.json")
    _write(old / "releases" / "scanbench-0.2.0.tar.gz")
    _write(old / "privacy" / "deny.txt")
    _write(old / "update.lock", "")
    _write(old / "cache" / "devices.json")
    _write(old / "venvs" / "0.2.0" / "bin" / "python")
    _write(paths.config_dir / "settings.toml", "new")       # must not be overwritten
    report = LegacyLayout(paths, {"SCANBENCH_HOME": str(old)}).run()
    assert report[0].startswith("SCANBENCH_HOME is no longer used")
    assert (paths.config_dir / "settings.toml").read_text(encoding="utf-8") == "new"
    assert (old / "config" / "settings.toml").read_text(encoding="utf-8") == "old"
    assert (paths.config_dir / "presets" / "photos-a.toml").is_file()
    assert (paths.log_dir / "scanbench.log").is_file()
    assert (paths.sessions_dir / "s1" / "state.json").is_file()
    assert (paths.release.archive_store / "scanbench-0.2.0.tar.gz").is_file()
    assert (paths.config_dir / "privacy" / "deny.txt").is_file()
    assert paths.release.lock_file.is_file()
    assert not (old / "logs").exists() and not (old / "sessions").exists()
    _check_report(paths, old, report)


def _check_report(paths: AppPaths, old: Path, report: list[str]) -> None:
    """Check the report of the move from $SCANBENCH_HOME and a second run.

    Args:
        paths: Target directories.
        old: The old single-root folder.
        report: Report of the first run.
    """
    assert any(line.startswith("kept, target exists:") for line in report)
    assert any("re-creatable" in line for line in report)
    assert any("install again with install.sh" in line for line in report)
    assert sum(line.startswith("moved:") for line in report) == 6   # presets merged
    logged = (paths.log_dir / REPORT_FILE).read_text(encoding="utf-8")
    assert "moved:" in logged and "kept, target exists:" in logged
    again = LegacyLayout(paths, {"SCANBENCH_HOME": str(old)}).run()     # second run
    assert not any(line.startswith("moved:") for line in again)


def test_release_dir_of_old_menu_entries(tmp_path: Path) -> None:
    """config/ and logs/ below the release folder move; venvs and sessions stay.

    Args:
        tmp_path: Temporary home directory.
    """
    paths = AppPaths({}, tmp_path)
    root = paths.release_dir
    _write(root / "config" / "settings.toml")
    _write(root / "logs" / "crash.log")
    _write(root / "update.lock", "")
    _write(root / "sessions" / "s1" / "state.json")
    (root / "venvs" / "0.3.1").mkdir(parents=True)
    (root / "venv").symlink_to("venvs/0.3.1")
    report = LegacyLayout(paths, {}).run()
    assert sorted(line.split(" -> ")[1] for line in report) == sorted(
        [str(paths.config_dir), str(paths.log_dir), str(paths.release.lock_file)])
    assert (root / "venvs" / "0.3.1").is_dir() and (root / "venv").is_symlink()
    assert (root / "sessions" / "s1" / "state.json").is_file()
    assert root.is_dir()                                     # release folder stays


def test_old_default_root_is_found_and_removed_when_empty(tmp_path: Path) -> None:
    """~/scripts/scanbench.d is found without a variable and removed once empty.

    Args:
        tmp_path: Temporary home directory.
    """
    paths = AppPaths({}, tmp_path)
    old = tmp_path / "scripts" / "scanbench.d"
    _write(old / "logs" / "scanbench.log")
    layout = LegacyLayout(paths, {})
    assert layout.roots()[0] == old
    layout.run()
    assert (paths.log_dir / "scanbench.log").is_file()
    assert not old.exists() and (tmp_path / "scripts").is_dir()


def test_errors_are_reported_not_raised(tmp_path: Path) -> None:
    """A move that fails is reported; the run goes on.

    Args:
        tmp_path: Temporary home directory.
    """
    paths = AppPaths({}, tmp_path)
    old = tmp_path / "scripts" / "scanbench.d"
    _write(old / "logs" / "scanbench.log")
    paths.log_dir.parent.mkdir(parents=True)
    paths.log_dir.parent.chmod(0o500)                            # target not writable
    try:
        report = LegacyLayout(paths, {}).run()
    finally:
        paths.log_dir.parent.chmod(0o700)
    if os.geteuid() == 0:                                   # root ignores the mode
        assert any(line.startswith("moved:") for line in report)
    else:
        assert any(line.startswith("could not move") for line in report)
        assert (old / "logs" / "scanbench.log").is_file()
