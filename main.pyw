"""DBS Garden Fete POS launcher.

Double-clickable on Windows (no console window). Copy this whole folder to
each laptop; the local database and the failure log are created next to this
file. A startup failure (e.g. the device database cannot be opened) shows a
window and is written to the local log instead of failing silently.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pos import observability
from pos.domain import CorruptRecordError, PosError
from pos.facade import PosSession
from pos.sqlite import SqlitePersistence
from pos.ui.app import PosApp


def fatal_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        messagebox.showerror("DBS Garden Fete POS", message)
    finally:
        root.destroy()


def main() -> None:
    app_dir = Path(__file__).resolve().parent
    observability.set_log_dir(app_dir)
    db_path = app_dir / "pos.db"
    try:
        session = PosSession(SqlitePersistence(db_path))
        app = PosApp(session)
        app.mainloop()
    except CorruptRecordError as exc:
        observability.log_failure("device database", f"corrupt records: {exc}")
        fatal_error(
            "The device database contains records the app cannot read.\n\n"
            f"{exc}\n\n"
            f"Details were written to:\n{observability.log_path()}"
        )
    except PosError as exc:
        observability.log_failure("device database", str(exc))
        fatal_error(
            "The device database could not be opened or read.\n\n"
            f"{exc}\n\n"
            f"Details were written to:\n{observability.log_path()}"
        )
    except Exception as exc:  # noqa: BLE001  # record any unhandled failure
        observability.log_failure("app", str(exc), detail=repr(exc))
        fatal_error(
            "The app hit an unexpected problem and could not continue.\n\n"
            f"Details were written to:\n{observability.log_path()}"
        )


if __name__ == "__main__":
    main()
