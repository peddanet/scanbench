"""Shared test setup: Qt renders offscreen, so no display or Xvfb is needed."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
