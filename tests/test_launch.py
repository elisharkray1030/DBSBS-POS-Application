"""Frozen-aware data directory tests (spec #91, ticket #92).

`pos.launch.app_dir` resolves the app data folder: the exe's own directory
when the process is frozen (PyInstaller one-file, where `__file__` points at
the ephemeral `_MEIPASS` bundle) and the repo root when run from source. Both
launchers must route their app-data-dir derivation through the helper so
`pos.db`/`pos.log` survive a frozen run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pos
import pos.launch

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_app_dir_from_source_resolves_to_the_repo_root(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert pos.launch.app_dir() == _REPO_ROOT


def test_app_dir_from_a_frozen_process_resolves_to_the_exe_folder(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "DBSGardenFetePOS.exe")
    )
    assert pos.launch.app_dir() == tmp_path


def test_both_launchers_derive_app_dir_through_the_helper() -> None:
    for name in ("main.pyw", "start.pyw"):
        text = (_REPO_ROOT / name).read_text(encoding="utf-8")
        assert "launch.app_dir()" in text
        assert "APP_DIR = Path(__file__)" not in text
        assert "app_dir = Path(__file__)" not in text