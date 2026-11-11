"""Tests for VersionInfo."""

from pathlib import Path

from scanbench.infrastructure.version_info import VersionInfo


def _tree(root: Path, with_git: bool) -> Path:
    """Create a minimal source tree and return its package directory."""
    package = root / "src" / "scanbench"
    package.mkdir(parents=True)
    (root / "pyproject.toml").write_text("", encoding="utf-8")
    if with_git:
        (root / ".git").mkdir()
    return package


def test_source_checkout_is_marked(tmp_path: Path) -> None:
    """A package inside a git source tree reports the checkout.

    Args:
        tmp_path: Temporary directory of the test.
    """
    info = VersionInfo(_tree(tmp_path, with_git=True), "1.2.3")
    assert info.checkout_root() == tmp_path
    assert info.text() == f"1.2.3 (source checkout {tmp_path}, not an installed release)"


def test_tree_without_git_is_release(tmp_path: Path) -> None:
    """Without .git the tree counts as installed (e.g. an unpacked sdist).

    Args:
        tmp_path: Temporary directory of the test.
    """
    assert VersionInfo(_tree(tmp_path, with_git=False), "1.2.3").text() == "1.2.3"


def test_site_packages_is_release(tmp_path: Path) -> None:
    """A package in site-packages reports the bare version.

    Args:
        tmp_path: Temporary directory of the test.
    """
    package = tmp_path / "site-packages" / "scanbench"
    package.mkdir(parents=True)
    assert VersionInfo(package, "1.2.3").text() == "1.2.3"
