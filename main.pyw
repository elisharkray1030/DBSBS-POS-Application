"""DBS Garden Fete POS launcher.

Double-clickable on Windows (no console window). Copy this whole folder to
each laptop; the local database is created next to this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pos.facade import PosSession
from pos.sqlite import SqlitePersistence
from pos.ui.app import PosApp


def main() -> None:
    db_path = Path(__file__).resolve().parent / "pos.db"
    session = PosSession(SqlitePersistence(db_path))
    app = PosApp(session)
    app.mainloop()


if __name__ == "__main__":
    main()
