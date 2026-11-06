"""Shared text used to identify the active Stock sheet in UI screens."""


def stock_sheet_label(filename: str | None) -> str:
    """Return the consistent status label for an active or unrecorded sheet."""
    if filename:
        return f"Stock sheet: {filename}"
    return "Stock sheet: Source not recorded"
