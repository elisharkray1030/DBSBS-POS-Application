"""Double-click startup script for the DBS Garden Fete POS.

The app's only external dependency is `customtkinter`. This script checks
whether it is importable, installs the pinned, tested version via pip if
missing (requires internet, expected on first setup before event day), then
launches the application. On event day the dependency is already installed
and the script goes straight to launching. If the dependency is missing and
pip cannot reach the network, a clear error tells the organizer to run this
script once with internet first, and the captured pip output is written to
the local failure log.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


def dependency_available() -> bool:
    try:
        import customtkinter  # noqa: F401

        return True
    except Exception:  # noqa: BLE001  # any import failure means missing/broken dep
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
    if result.returncode == 0 or dependency_available():
        return None
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    return output or "pip exited with an error and produced no output."


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


def main() -> int:
    sys.path.insert(0, str(APP_DIR))
    from pos import diagnostics
    from pos.diagnostics import LogSource
    from pos.fatal import fatal_error

    diagnostics.set_log_dir(APP_DIR)
    if not dependency_available():
        detail = install_dependency()
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
    import main

    main.main()
    return 0


if __name__ == "__main__":
    main()
