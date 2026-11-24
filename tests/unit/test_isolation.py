"""The test run is isolated from the real desktop, session and user data."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from child_wait import finish
from conftest import SANDBOX


def test_environment_points_into_the_sandbox() -> None:
    """Home, XDG folders and runtime dir are temporary; no display is reachable."""
    for variable in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                     "XDG_CACHE_HOME", "XDG_DOWNLOAD_DIR", "XDG_RUNTIME_DIR"):
        assert Path(os.environ[variable]).is_relative_to(SANDBOX), variable
    assert Path.home().is_relative_to(SANDBOX)
    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    assert not (runtime / os.environ["WAYLAND_DISPLAY"]).exists()
    assert "DISPLAY" not in os.environ and "DBUS_SESSION_BUS_ADDRESS" not in os.environ
    assert not any(v.startswith("SCANBENCH_") for v in os.environ)


def test_finish_returns_the_output() -> None:
    """A child that ends in time hands over its output."""
    with subprocess.Popen([sys.executable, "-c", "print('done')"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
        out, err = finish(child)
    assert out.strip() == b"done" and err == b"" and child.returncode == 0


def test_finish_kills_a_hanging_child_and_reports_its_output() -> None:
    """A child over the limit is killed; the failure shows its last lines."""
    code = "import sys, time; print('last words', flush=True); time.sleep(60)"
    with subprocess.Popen([sys.executable, "-c", code],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as child:
        with pytest.raises(pytest.fail.Exception, match="last words"):
            finish(child, limit=2)
    assert child.returncode is not None
