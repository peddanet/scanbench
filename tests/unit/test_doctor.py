"""Tests for Doctor and ToolRequirement."""

from pathlib import Path

from scanbench.application.doctor import Doctor
from scanbench.domain.tool_requirement import ToolRequirement
from scanbench.infrastructure.app_paths import AppPaths
from scanbench.infrastructure.tool_probe import ToolProbe

REQS = (
    ToolRequirement("scanimage", True, "scanning", "sane-utils"),
    ToolRequirement("gs", False, "shrinking", "ghostscript"),
)


def _doctor(found: set[str]) -> Doctor:
    """Create a Doctor whose probe finds only the given programs."""
    probe = ToolProbe(lambda name: f"/usr/bin/{name}" if name in found else None)
    return Doctor(probe, AppPaths({}, Path("/h")), "9.9.9", REQS)


def test_all_present() -> None:
    """All programs found: status 0 and paths listed."""
    status, lines = _doctor({"scanimage", "gs"}).run()
    assert status == 0
    assert lines[0] == "scanbench 9.9.9"
    assert any("/usr/bin/scanimage" in line for line in lines)
    assert lines[-1] == "Result: OK"


def test_optional_missing_is_ok() -> None:
    """A missing optional program names its package but keeps status 0."""
    status, lines = _doctor({"scanimage"}).run()
    assert status == 0
    assert any("MISSING, install package ghostscript" in line for line in lines)


def test_required_missing_fails() -> None:
    """A missing required program gives status 1."""
    status, lines = _doctor({"gs"}).run()
    assert status == 1
    assert lines[-1] == "Result: required programs missing"


def test_requirement_label() -> None:
    """Labels reflect the importance."""
    assert REQS[0].label() == "required"
    assert REQS[1].label() == "optional"


def test_default_probe_uses_path() -> None:
    """The default probe searches PATH; a nonsense name is not found."""
    assert ToolProbe().locate("scanbench-no-such-program") is None
