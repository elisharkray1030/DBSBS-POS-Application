"""Local failure observability for the DBS Garden Fete POS.

The register's bounded, secret-safe, never-raising failure log (spec #64).
Pure functions only — no UI, no network. Callers name the operation that
failed and the module writes a timestamped entry to a log file beside the
device database, keeping the file bounded so it can never fill the laptop's
disk across an event day.

Secret-safety: the module writes exactly the strings callers pass. It never
reads the environment, never logs full command lines, and never scans for
secrets; callers must not pass secrets.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# The single concrete release the app is verified against (ticket 02).
PINNED_CUSTOMTKINTER = "customtkinter==6.0.0"

# One bounded file, capped so it can never fill the disk on event day.
MAX_LOG_BYTES = 64 * 1024

LOG_FILE_NAME = "pos.log"

_log_dir: Path = Path.cwd()


def set_log_dir(base_dir: str | Path) -> None:
    """Point the failure log at a directory. Called once at startup."""
    global _log_dir
    _log_dir = Path(base_dir)


def log_path(base_dir: str | Path | None = None) -> Path:
    """The log file for a directory; defaults to the configured location."""
    directory = Path(base_dir) if base_dir is not None else _log_dir
    return directory / LOG_FILE_NAME


def pip_install_command(python_executable: str | None = None) -> list[str]:
    """The pip command that installs the pinned dependency release."""
    return [
        python_executable or sys.executable,
        "-m",
        "pip",
        "install",
        PINNED_CUSTOMTKINTER,
    ]


def log_failure(
    source: str,
    message: str,
    detail: str | None = None,
    *,
    base_dir: str | Path | None = None,
) -> None:
    """Append a bounded failure entry. Never raises, even on write failure."""
    try:
        entry = _entry(source, message, detail, datetime.now())
        _append_bounded(log_path(base_dir), entry)
    except Exception:  # noqa: BLE001  # the log is advisory, never fatal
        return


def _entry(source: str, message: str, detail: str | None, now: datetime) -> str:
    stamp = now.isoformat(timespec="seconds")
    lines = [f"{stamp} [{source}] {message}"]
    if detail:
        lines.append(f"  detail: {detail}")
    return "\n".join(lines) + "\n"


def _append_bounded(path: Path, entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    encoded = (existing + entry).encode("utf-8")
    limit = MAX_LOG_BYTES
    if len(encoded) > limit:
        entry_bytes = len(entry.encode("utf-8"))
        if entry_bytes < limit:
            # Make room for the whole newest entry by trimming the older
            # content, so the newest entry keeps its timestamp and source.
            room = limit - entry_bytes
            old = _tail_bytes(existing, room)
            encoded = (old + entry).encode("utf-8")
        if len(encoded) > limit:
            # Even the newest entry alone is too big; keep its tail.
            encoded = encoded[-limit:].decode("utf-8", "ignore").encode("utf-8")
    path.write_bytes(encoded)


def _tail_bytes(text: str, room: int) -> str:
    """The longest suffix of `text` that encodes to at most `room` bytes,
    ending on a character boundary."""
    encoded = text.encode("utf-8")
    if len(encoded) <= room:
        return text
    return encoded[-room:].decode("utf-8", "ignore")
