"""Frozen-aware app data directory resolution.

In a PyInstaller one-file build, `__file__` points inside an ephemeral
`_MEIPASS` bundle that is deleted on exit, so anything written relative to it
would be lost. `app_dir` returns the real home for the device database, the
failure log, and the export base: the exe's own folder when frozen, and the
repo root when run from source.
"""

from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """The folder holding the device database, failure log, and exports."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent