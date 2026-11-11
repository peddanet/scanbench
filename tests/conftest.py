"""Shared test setup: Qt renders offscreen, so no display or Xvfb is needed."""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Make tests/fakes.py importable as "fakes".
sys.path.insert(0, os.path.dirname(__file__))
# Tests must not see the maintainer's own installation settings.
for _variable in ("SCANBENCH_HOME", "SCANBENCH_CLONE", "SCANBENCH_PRIVACY_DENY",
                  "SCANBENCH_BIN"):
    os.environ.pop(_variable, None)
