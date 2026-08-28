"""Double-click startup script for the DBS Garden Fete POS.

The app's only external dependency is `customtkinter`. This script checks
whether it is importable, installs it via pip if missing (requires internet,
expected on first setup before event day), then launches the application.
On event day the dependency is already installed and the script goes straight
to launching. If the dependency is missing and pip cannot reach the network,
a clear error tells the organizer to run this script once with internet first.
"""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

APP_DIR = Path(__file__).resolve().parent

DEPENDENCY = "customtkinter"


def dependency_available() -> bool:
    try:
        import customtkinter  # noqa: F401

        return True
    except Exception:  # noqa: BLE001  # any import failure means missing/broken dep
        return False


def install_dependency() -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", DEPENDENCY],
            check=True,
            cwd=APP_DIR,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.CalledProcessError, OSError):
        return False
    return dependency_available()


def fatal_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror("DBS Garden Fete POS", message)
    finally:
        root.destroy()


def main() -> int:
    if not dependency_available() and not install_dependency():
        fatal_error(
            "The customtkinter dependency is not installed and could not "
            "be installed automatically, so the app cannot start.\n\n"
            "Run this script once while connected to the internet so it "
            "can set itself up, then run it again on event day."
        )
        return 1
    sys.path.insert(0, str(APP_DIR))
    import main

    main.main()
    return 0


if __name__ == "__main__":
    main()
