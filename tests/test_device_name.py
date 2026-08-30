"""Pure tests for the device-name validation rule (spec #65, ADR-0005).

The device name becomes the `stocks-<name>.csv` component of the end-of-day
export, so it must obey the file system's rules (ADR-0005). These tests cover
the domain-level `validate_device_name` helper directly; the facade seam and
the export guard are covered in `test_setup.py` and `test_reporting.py`.
"""

from __future__ import annotations

import pytest

from pos.domain import MAX_DEVICE_NAME_LENGTH, SetupError, validate_device_name


@pytest.mark.parametrize(
    "name",
    ["A", "Till A", "Till-A", "Till A 2", "Till.A", "Till_A"],
)
def test_validate_accepts_safe_names(name):
    assert validate_device_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "   ",
        ".",
        "..",
        "../evil",
        "..\\..\\evil",
        "a/b",
        "a\\b",
        "C:\\Windows",
        "CON",
        "con",
        "con.txt",
        "NUL",
        "NUL.csv",
        "PRN",
        "AUX",
        "COM1",
        "com9",
        "LPT1",
        "lpt9",
        "Till*A",
        "Till?A",
        "Till:A",
        "Till<A",
        "Till>A",
        "Till|A",
        'Till"A',
        "bad\x00name",
        "bad\nname",
    ],
)
def test_validate_rejects_unsafe_names(name):
    with pytest.raises(SetupError):
        validate_device_name(name)


def test_validate_rejects_a_name_too_long_for_the_export_filename():
    with pytest.raises(SetupError):
        validate_device_name("x" * (MAX_DEVICE_NAME_LENGTH + 1))


def test_validate_accepts_the_longest_allowed_name():
    name = "x" * MAX_DEVICE_NAME_LENGTH
    assert validate_device_name(name) == name


def test_validate_measures_length_in_utf16_units_like_ntfs():
    astral = "\U0001F600"  # one astral character = two UTF-16 units
    assert validate_device_name(astral * (MAX_DEVICE_NAME_LENGTH // 2)) == (
        astral * (MAX_DEVICE_NAME_LENGTH // 2)
    )


def test_validate_rejects_astral_characters_that_overflow_ntfs_length():
    astral = "\U0001F600"
    with pytest.raises(SetupError):
        validate_device_name(astral * (MAX_DEVICE_NAME_LENGTH // 2 + 1))


def test_validate_trims_surrounding_whitespace():
    assert validate_device_name("  Till A  ") == "Till A"


def test_validate_trims_a_trailing_dot_that_would_collide_on_ntfs():
    assert validate_device_name("Till A.") == "Till A"