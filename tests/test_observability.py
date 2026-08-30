"""Tests for the failure log and bootstrap helpers (spec #64, ticket 01)."""

from __future__ import annotations

import re
from pathlib import Path

from pos import observability


def test_entry_records_source_and_message(tmp_path: Path) -> None:
    observability.log_failure("export", "boom", base_dir=tmp_path)

    text = observability.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[export]" in text
    assert "boom" in text
    assert "detail:" not in text


def test_entry_records_detail(tmp_path: Path) -> None:
    observability.log_failure(
        "bootstrap", "install failed", detail="Permission denied", base_dir=tmp_path
    )

    text = observability.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[bootstrap] install failed" in text
    assert "detail: Permission denied" in text


def test_entries_append(tmp_path: Path) -> None:
    observability.log_failure("export", "one", base_dir=tmp_path)
    observability.log_failure("export", "two", base_dir=tmp_path)

    text = observability.log_path(tmp_path).read_text(encoding="utf-8")
    assert "one" in text
    assert "two" in text


def test_log_is_bounded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(observability, "MAX_LOG_BYTES", 512)
    for i in range(200):
        observability.log_failure("export", f"failure {i}", base_dir=tmp_path)

    path = observability.log_path(tmp_path)
    assert path.stat().st_size <= 512


def test_newest_entry_keeps_header_when_full(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(observability, "MAX_LOG_BYTES", 512)
    for i in range(50):
        observability.log_failure("export", f"filler {i}", base_dir=tmp_path)
    observability.log_failure("settlement", "latest failure", base_dir=tmp_path)

    text = observability.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[settlement] latest failure" in text


def test_log_failure_never_raises(tmp_path: Path) -> None:
    blocking = tmp_path / "not-a-dir"
    blocking.write_text("x", encoding="utf-8")

    # A base directory that is a file means the log cannot be written; the
    # recorder must swallow the failure, not raise.
    observability.log_failure("export", "boom", base_dir=blocking)


def test_configured_default_location(tmp_path: Path) -> None:
    original = observability._log_dir
    observability.set_log_dir(tmp_path)
    try:
        observability.log_failure("export", "boom")
        assert (tmp_path / observability.LOG_FILE_NAME).exists()
    finally:
        observability.set_log_dir(original)


def test_pinned_dependency_is_concrete() -> None:
    assert re.fullmatch(
        r"customtkinter==\d+(?:\.\d+){1,2}", observability.PINNED_CUSTOMTKINTER
    )


def test_pip_install_command_pins_version() -> None:
    command = observability.pip_install_command("python.exe")
    assert command == [
        "python.exe",
        "-m",
        "pip",
        "install",
        observability.PINNED_CUSTOMTKINTER,
    ]
