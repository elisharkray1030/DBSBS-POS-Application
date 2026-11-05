"""Cross-platform source loading tests for the start.pyw launcher."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

from pos import diagnostics
from pos.diagnostics import LogSource
from tests._source_loader import load_source_module

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_start_launcher() -> ModuleType:
    return load_source_module("start_launcher_test", _REPO_ROOT / "start.pyw")


def _stub_fatal_dialog(monkeypatch) -> None:
    fatal = ModuleType("pos.fatal")
    fatal.fatal_error = lambda message: None
    monkeypatch.setitem(sys.modules, "pos.fatal", fatal)


def test_start_launcher_loads_main_pyw_and_calls_main_once(
    tmp_path: Path, monkeypatch
) -> None:
    launcher = _load_start_launcher()
    _stub_fatal_dialog(monkeypatch)
    marker = tmp_path / "called.txt"
    main_source = (
        "from pathlib import Path\n"
        f"def main():\n"
        f"    with Path({str(marker)!r}).open('a', encoding='utf-8') as marker:\n"
        "        marker.write('called\\n')\n"
    )
    (tmp_path / "main.pyw").write_text(main_source, encoding="utf-8")
    monkeypatch.setattr(launcher, "APP_DIR", tmp_path)

    previous_main = sys.modules.pop("main", None)
    try:
        assert launcher.launch() == 0
    finally:
        sys.modules.pop("main", None)
        if previous_main is not None:
            sys.modules["main"] = previous_main

    assert marker.read_text(encoding="utf-8").splitlines() == ["called"]


def test_start_launcher_logs_main_pyw_load_failure(
    tmp_path: Path, monkeypatch
) -> None:
    launcher = _load_start_launcher()
    (tmp_path / "main.pyw").write_text("def main(:\n", encoding="utf-8")
    monkeypatch.setattr(launcher, "APP_DIR", tmp_path)
    previous_log_dir = diagnostics.log_dir()
    diagnostics.set_log_dir(tmp_path)
    _stub_fatal_dialog(monkeypatch)

    try:
        assert launcher.launch() == 1
        log = diagnostics.log_path(tmp_path).read_text(encoding="utf-8")
    finally:
        diagnostics.set_log_dir(previous_log_dir)

    assert f"[{LogSource.APP.value}]" in log
