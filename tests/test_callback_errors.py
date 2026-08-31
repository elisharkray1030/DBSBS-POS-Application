"""Callback-failure routing for the application shell (spec #81, ticket 02).

Tk's main loop reports an exception raised inside a screen callback to the
shell's `report_callback_exception`. This suite tests the routing decision
without a display: one logged entry naming the application as the failing
operation, and at most one fatal dialog per session.
"""

from __future__ import annotations

from pos import diagnostics
from pos.app_errors import CallbackFailureHandler
from pos.diagnostics import LogSource


def test_callback_failure_logs_the_application_operation() -> None:
    logged: list[tuple] = []
    handler = CallbackFailureHandler(
        log=lambda source, message, detail=None, *, base_dir=None: logged.append(
            (source, message, detail)
        ),
        show=lambda message: None,
    )
    handler.handle(RuntimeError("boom"))

    assert len(logged) == 1
    assert logged[0][0] == LogSource.APP
    assert logged[0][1] == "boom"
    assert "RuntimeError" in logged[0][2]


def test_repeated_callback_failures_open_at_most_one_dialog() -> None:
    shown: list[str] = []
    handler = CallbackFailureHandler(log=lambda *a, **k: None, show=shown.append)

    handler.handle(RuntimeError("one"))
    handler.handle(RuntimeError("two"))

    assert len(shown) == 1
    assert handler.dialog_shown is True
    assert "unexpected problem" in shown[0]
    assert "pos.log" in shown[0]


def test_callback_failure_writes_to_the_local_log(tmp_path) -> None:
    original = diagnostics.log_dir()
    diagnostics.set_log_dir(tmp_path)
    try:
        handler = CallbackFailureHandler(show=lambda message: None)
        handler.handle(RuntimeError("callback boom"))
    finally:
        diagnostics.set_log_dir(original)

    text = diagnostics.log_path(tmp_path).read_text(encoding="utf-8")
    assert "[app]" in text
    assert "callback boom" in text
