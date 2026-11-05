"""Double-click startup script for the DBS Garden Fete POS.

The app's only external dependency is `customtkinter`. This script checks
whether the exact pinned, tested release is importable, installs it via pip
if missing or wrong (requires internet, expected on first setup before event
day), then launches the application. On event day the dependency is already
installed and the script goes straight to launching. Readiness means the
pinned release actually imports: an importable wrong version, or a pip run
that exits zero without leaving the pinned release importable, is a failure.
If the dependency cannot be made ready, a clear error tells the organizer
what to fix and the captured pip output is written to the local failure log;
a dependency-sensitive application import failure is logged and shown the
same way instead of failing silently.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pos import launch

APP_DIR = launch.app_dir()


def dependency_ready() -> bool:
    """True only when the exact pinned `customtkinter` release imports."""
    from importlib.metadata import version

    from pos import diagnostics

    try:
        import customtkinter  # noqa: F401

        return version("customtkinter") == diagnostics.PINNED_CUSTOMTKINTER_VERSION
    except Exception:  # noqa: BLE001  # any import/version failure means not ready
        return False


def install_dependency() -> str | None:
    """Install the pinned dependency; return captured pip output on failure."""
    from pos import diagnostics

    try:
        result = subprocess.run(
            diagnostics.pip_install_command(sys.executable),
            capture_output=True,
            text=True,
            check=False,  # return code inspected below; pip output kept on failure
            cwd=APP_DIR,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        return f"Could not run pip: {exc}"
    if result.returncode == 0 or dependency_ready():
        return None
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    return output or "pip exited with an error and produced no output."


def pip_detail_after_install(detail: str | None, ready: bool) -> str | None:
    """What the installer reports after a pip attempt.

    None means the pinned dependency is now importable and the app can start.
    A non-None string is the detail to surface: the pip output, or a dedicated
    message when pip exited zero but the pinned release still will not import.
    """
    if ready:
        return None
    if detail:
        return detail
    return (
        "pip reported success but the pinned customtkinter version "
        "still cannot be imported."
    )


def install_failure_hint(detail: str) -> str:
    """Name the likely cause from the captured pip output."""
    lowered = detail.lower()
    if (
        "permission" in lowered
        or "access is denied" in lowered
        or "access denied" in lowered
    ):
        return "This looks like a permissions problem on this laptop."
    return "This usually means this laptop has no internet connection right now."


def launch() -> int:
    """Import and run the app, logging and surfacing any startup failure.

    An application-import failure (a broken dependency, a corrupt launcher,
    the dependency-sensitive app import) is logged under the application
    operation and shown through the fatal dialog instead of exiting silently
    in a `.pyw` deployment. The guarded block covers the import and the run
    itself, because the app's own startup handler only wraps what happens
    after its dependency-sensitive imports.
    """
    from pos import diagnostics
    from pos.diagnostics import LogSource
    from pos.fatal import fatal_error

    try:
        import main

        main.main()
    except Exception as exc:  # noqa: BLE001  # surface any startup failure
        diagnostics.log_failure(LogSource.APP, str(exc), detail=repr(exc))
        fatal_error(
            "The app could not start.\n\n"
            f"Details were written to:\n{diagnostics.log_path()}"
        )
        return 1
    return 0


def main() -> int:
    sys.path.insert(0, str(APP_DIR))
    from pos import diagnostics
    from pos.diagnostics import LogSource
    from pos.fatal import fatal_error

    diagnostics.set_log_dir(APP_DIR)
    if not dependency_ready():
        detail = pip_detail_after_install(install_dependency(), dependency_ready())
        if detail is not None:
            diagnostics.log_failure(
                LogSource.BOOTSTRAP,
                "The customtkinter dependency could not be installed.",
                detail=detail,
            )
            fatal_error(
                "The app's dependency (customtkinter) could not be installed, "
                "so the app cannot start.\n\n"
                f"{install_failure_hint(detail)}\n\n"
                "Run this script once while connected to the internet so it "
                "can set itself up, then run it again on event day.\n\n"
                f"The full installation details were written to:\n"
                f"{diagnostics.log_path()}"
            )
            return 1
    return launch()


if __name__ == "__main__":
    main()
