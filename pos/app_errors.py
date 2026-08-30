"""Routing of unexpected runtime failures for the application shell.

Tk's main loop reports an exception raised inside a screen callback to the
shell's `report_callback_exception`. This module owns what the shell does with
it: one logged entry naming the application as the failing operation, and at
most one fatal dialog for the whole session, so a mid-event crash leaves a
trace on the device instead of failing silently (spec #81, ticket 02).

The log writer and the dialog are injected so the routing is unit-testable
without a real display; the production app uses the diagnostics and fatal
defaults.
"""

from __future__ import annotations

from collections.abc import Callable

from . import diagnostics
from .diagnostics import LogSource
from .fatal import fatal_error


class CallbackFailureHandler:
    """Logs a callback failure and shows one fatal dialog per session."""

    def __init__(
        self,
        log: Callable[..., None] = diagnostics.log_failure,
        show: Callable[[str], None] = fatal_error,
    ) -> None:
        self._log = log
        self._show = show
        self._dialog_shown = False

    @property
    def dialog_shown(self) -> bool:
        """True once a fatal dialog has been shown; later failures are quiet."""
        return self._dialog_shown

    def handle(self, exc: BaseException) -> None:
        self._log(LogSource.APP, str(exc), detail=repr(exc))
        if not self._dialog_shown:
            self._dialog_shown = True
            self._show(
                "The app hit an unexpected problem and could not continue.\n\n"
                f"Details were written to:\n{diagnostics.log_path()}"
            )
