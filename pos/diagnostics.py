"""Startup diagnostics and failure observability for the DBS Garden Fete POS.

Pure functions only — no UI, no network. The register records a failure by
naming the operation that failed (a `LogSource`), and this module writes a
timestamped entry to a log file beside the device database, keeping the file
bounded so it can never fill the laptop's disk across an event day. It also
owns the pinned dependency release and the pip command that installs it, so
first-run setup is reproducible.

Secret-safety: the module writes exactly the strings callers pass. It never
reads the environment, never logs full command lines, and never scans for
secrets; callers must not pass secrets.
"""

from __future__ import annotations

import sys
from datetime import datetime
from enum import StrEnum
from pathlib import Path

# The single concrete release the app is verified against (ticket 02).
PINNED_CUSTOMTKINTER_VERSION = "6.0.0"
PINNED_CUSTOMTKINTER = f"customtkinter=={PINNED_CUSTOMTKINTER_VERSION}"

# One bounded file, capped so it can never fill the disk on event day.
MAX_LOG_BYTES = 64 * 1024

LOG_FILE_NAME = "pos.log"


class LogSource(StrEnum):
    """The operation a failure entry names (CONTEXT.md vocabulary where one exists)."""

    BOOTSTRAP = "bootstrap"
    DEVICE_DATABASE = "device database"
    APP = "app"
    SETUP = "setup"
    SETUP_CATALOG = "setup catalog"
    EXPORT = "export"
    SETTLEMENT = "settlement"
    CASH_ADJUSTMENT = "cash adjustment"
    VOID = "void"
    CORRECTION = "correction"
    WIPE = "wipe"
    ADD_TO_SALE = "add to sale"
    SOLD_OUT = "sold out"
    SET_QUANTITY = "set quantity"


_log_dir: Path = Path.cwd()


def set_log_dir(base_dir: str | Path) -> None:
    """Point the failure log at a directory. Called once at startup."""
    global _log_dir
    _log_dir = Path(base_dir)


def log_dir() -> Path:
    """The directory the failure log is currently configured to use."""
    return _log_dir


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
    source: LogSource,
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


def _entry(source: LogSource, message: str, detail: str | None, now: datetime) -> str:
    """An entry that fits the log bound, keeping its identity first.

    The header (timestamp, operation, primary message) is kept whole whenever
    possible; only an oversized detail is truncated to make room. When the
    header alone cannot fit, the primary message is truncated. The timestamp
    and the operation always survive, so a huge pip output or message can
    never erase which operation failed.
    """
    stamp = now.isoformat(timespec="seconds")
    return _fit_entry(stamp, source, message, detail, MAX_LOG_BYTES)


def _fit_entry(
    stamp: str, source: LogSource, message: str, detail: str | None, limit: int
) -> str:
    if detail is None:
        return _fit_header(f"{stamp} [{source}] {message}", limit)
    full = f"{stamp} [{source}] {message}\n  detail: {detail}\n"
    if len(full.encode("utf-8", "replace")) <= limit:
        return full
    room = limit - len(f"{stamp} [{source}] {message}\n  detail: \n".encode("utf-8", "replace"))
    if room > 0:
        return f"{stamp} [{source}] {message}\n  detail: {_tail_bytes(detail, room)}\n"
    return _fit_header(f"{stamp} [{source}] {message}", limit)


def _fit_header(header: str, limit: int) -> str:
    text = f"{header}\n"
    if len(text.encode("utf-8", "replace")) <= limit:
        return text
    # Keep the timestamp and the operation, truncating the primary message.
    stamp, _bracket, rest = header.partition(" [")
    source, _sep, message = rest.partition("] ")
    kept = f"{stamp} [{source}] "
    room = max(limit - len(f"{kept}\n".encode("utf-8", "replace")), 1)
    return f"{kept}{_tail_bytes(message, room)}\n"


def _append_bounded(path: Path, entry: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    limit = MAX_LOG_BYTES
    encoded = (existing + entry).encode("utf-8", "replace")
    if len(encoded) <= limit:
        path.write_bytes(encoded)
        return
    # The entry alone fits (it was fitted above); keep it whole by trimming
    # the older content to make room for it.
    entry_bytes = len(entry.encode("utf-8", "replace"))
    room = limit - entry_bytes
    old = _tail_bytes(existing, room)
    path.write_bytes((old + entry).encode("utf-8", "replace"))


def _tail_bytes(text: str, room: int) -> str:
    """The longest suffix of `text` that encodes to at most `room` bytes,
    ending on a character boundary. Unencodable characters are replaced so a
    surrogate in a message cannot raise out of the writer."""
    if room <= 0:
        return ""
    encoded = text.encode("utf-8", "replace")
    if len(encoded) <= room:
        return text
    return encoded[-room:].decode("utf-8", "ignore")
