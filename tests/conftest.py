"""Shared test setup: tests never touch the real desktop, session or user data.

* Qt renders offscreen, so no display or Xvfb is needed.
* ``WAYLAND_DISPLAY`` names a socket that does not exist, ``DISPLAY`` and the
  session bus address are removed: nothing can reach the running desktop.
* ``HOME``, ``XDG_RUNTIME_DIR`` and the XDG data folders point into one
  temporary directory that is removed when the test run ends.
* The maintainer's own scanbench variables are removed.
"""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

SANDBOX = Path(tempfile.mkdtemp(prefix="scanbench-tests-"))
"""Temporary home of the test run; removed at exit."""

atexit.register(shutil.rmtree, SANDBOX, True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["WAYLAND_DISPLAY"] = "scanbench-test-no-such-display"
for _variable in ("DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
    os.environ.pop(_variable, None)

os.environ["HOME"] = str(SANDBOX / "home")
for _variable, _folder in (("XDG_CONFIG_HOME", "home/.config"),
                           ("XDG_DATA_HOME", "home/.local/share"),
                           ("XDG_STATE_HOME", "home/.local/state"),
                           ("XDG_CACHE_HOME", "home/.cache"),
                           ("XDG_DOWNLOAD_DIR", "home/Downloads"),
                           ("XDG_RUNTIME_DIR", "runtime")):
    (SANDBOX / _folder).mkdir(parents=True, exist_ok=True)
    os.environ[_variable] = str(SANDBOX / _folder)
(SANDBOX / "runtime").chmod(0o700)          # required by Qt for a runtime dir

# Make tests/fakes.py importable as "fakes" and tools/privacy_scan.py as
# "privacy_scan".
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent / "tools"))
# Tests must not see the maintainer's own installation settings.
for _variable in ("SCANBENCH_HOME", "SCANBENCH_CLONE", "SCANBENCH_PRIVACY_DENY",
                  "SCANBENCH_PRIVACY_ALLOW", "SCANBENCH_BIN"):
    os.environ.pop(_variable, None)
