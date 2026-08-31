"""Bootstrap regression tests (spec #81, ticket 01).

The launcher accepts only the exact pinned `customtkinter` release: an
importable wrong version is not ready, a zero pip exit that leaves the pinned
version unimportable is a failure, and a dependency-sensitive application
import failure produces a logged fatal dialog naming the log location. The
launcher glue (the real subprocess call and the Tk dialog) is not exercised;
the seams are the pure readiness check, the pip-detail decision, and the
launch function with an injected display.
"""

from __future__ import annotations

import builtins
import importlib.metadata
import types

import start

import pos.fatal
from pos import diagnostics


def _fake_customtkinter_import(real_import, *, fail: bool = False):
    def fake_import(name, *args, **kwargs):
        if name == "customtkinter":
            if fail:
                raise ImportError("broken customtkinter")
            return types.ModuleType("customtkinter")
        return real_import(name, *args, **kwargs)

    return fake_import


# -- dependency readiness ---------------------------------------------------


def test_dependency_ready_false_for_importable_wrong_version(monkeypatch):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "5.9.3")
    monkeypatch.setattr(
        builtins, "__import__", _fake_customtkinter_import(builtins.__import__)
    )
    assert start.dependency_ready() is False


def test_dependency_ready_true_for_the_pinned_version(monkeypatch):
    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: diagnostics.PINNED_CUSTOMTKINTER_VERSION,
    )
    monkeypatch.setattr(
        builtins, "__import__", _fake_customtkinter_import(builtins.__import__)
    )
    assert start.dependency_ready() is True


def test_dependency_ready_false_when_the_import_fails(monkeypatch):
    monkeypatch.setattr(
        builtins,
        "__import__",
        _fake_customtkinter_import(builtins.__import__, fail=True),
    )
    assert start.dependency_ready() is False


# -- successful pip but not importable -------------------------------------


def test_zero_pip_exit_is_still_a_failure_without_an_importable_release(
    monkeypatch,
):
    monkeypatch.setattr(start, "dependency_ready", lambda: False)
    monkeypatch.setattr(
        start.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(returncode=0, stdout="", stderr=""),
    )
    detail = start.pip_detail_after_install(start.install_dependency(), ready=False)
    assert (
        detail
        == "pip reported success but the pinned customtkinter version still cannot be imported."
    )


def test_pip_detail_passes_through_install_failures(monkeypatch):
    assert (
        start.pip_detail_after_install("Permission denied", ready=False)
        == "Permission denied"
    )
    assert start.pip_detail_after_install("Permission denied", ready=True) is None


def test_install_dependency_returns_captured_pip_output_on_failure(monkeypatch):
    monkeypatch.setattr(start, "dependency_ready", lambda: False)
    monkeypatch.setattr(
        start.subprocess,
        "run",
        lambda *a, **k: types.SimpleNamespace(
            returncode=1, stdout="", stderr="Collecting customtkinter\nERROR"
        ),
    )
    detail = start.install_dependency()
    assert detail is not None
    assert "Collecting customtkinter" in detail


# -- application import failure ---------------------------------------------


def test_application_import_failure_is_logged_and_surfaced(monkeypatch, tmp_path):
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        pos.fatal, "fatal_error", lambda message: captured.setdefault("message", message)
    )
    real_import = builtins.__import__

    def fail_dependency_sensitive_import(name, *args, **kwargs):
        # `pos.ui.app` is where the app pulls in customtkinter; failing it
        # reproduces a broken-dependency startup on the real seam.
        if name == "pos.ui.app":
            raise ImportError("app import exploded")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_dependency_sensitive_import)

    # main() points the log at the app folder on a real laptop; in the test
    # keep the temp directory the assertion reads from.
    real_set_log_dir = diagnostics.set_log_dir
    original = diagnostics.log_dir()
    real_set_log_dir(tmp_path)
    monkeypatch.setattr(diagnostics, "set_log_dir", lambda *a, **k: None)
    try:
        start.launch()
    finally:
        real_set_log_dir(original)

    assert "unexpected problem" in captured["message"].lower()
    assert "pos.log" in captured["message"]
    text = diagnostics.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[app]" in text
    assert "app import exploded" in text


def test_bootstrap_install_failure_logs_and_names_the_log_location(
    monkeypatch, tmp_path
):
    captured: dict[str, str] = {}
    monkeypatch.setattr(
        pos.fatal, "fatal_error", lambda message: captured.setdefault("message", message)
    )
    monkeypatch.setattr(start, "dependency_ready", lambda: False)
    monkeypatch.setattr(start, "install_dependency", lambda: "Permission denied")
    # main() points the log at the app folder on a real laptop; in the test
    # keep the temp directory the assertion reads from.
    real_set_log_dir = diagnostics.set_log_dir
    original = diagnostics.log_dir()
    real_set_log_dir(tmp_path)
    monkeypatch.setattr(diagnostics, "set_log_dir", lambda *a, **k: None)
    try:
        code = start.main()
    finally:
        real_set_log_dir(original)

    assert code == 1
    assert "permissions problem" in captured["message"].lower()
    assert "pos.log" in captured["message"]
    text = diagnostics.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[bootstrap]" in text
    assert "Permission denied" in text
