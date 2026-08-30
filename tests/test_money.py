"""Focused tests for the money coercion at the domain boundary.

`money()` is the single ingress for every price, float amount, tender amount,
cash-tendered value, and cash adjustment amount. It must reject non-numeric and
non-finite values regardless of input type, while staying sign-agnostic (a cash
adjustment is deliberately negative).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from pos.domain import InvalidMoney, PosError, money


def test_money_parses_a_plain_decimal_string():
    assert money("60") == Decimal("60")


def test_money_strips_surrounding_whitespace():
    assert money("  60 ") == Decimal("60")


def test_money_accepts_an_int():
    assert money(60) == Decimal("60")


def test_money_accepts_a_decimal_unchanged():
    assert money(Decimal("12.5")) == Decimal("12.5")


def test_money_accepts_a_float():
    assert money(12.5) == Decimal("12.5")


def test_money_accepts_a_negative_finite_value():
    assert money("-12.5") == Decimal("-12.5")


def test_money_accepts_a_huge_but_finite_value():
    assert money("1e1000000") == Decimal("1e1000000")


def test_money_rejects_a_non_numeric_string():
    with pytest.raises(InvalidMoney):
        money("sixty")


def test_money_rejects_an_empty_string():
    with pytest.raises(InvalidMoney):
        money("")


def test_money_rejects_a_whitespace_string():
    with pytest.raises(InvalidMoney):
        money("   ")


def test_money_rejects_nan_as_a_string():
    with pytest.raises(InvalidMoney):
        money("NaN")


def test_money_rejects_positive_infinity_as_a_string():
    with pytest.raises(InvalidMoney):
        money("Infinity")


def test_money_rejects_negative_infinity_as_a_string():
    with pytest.raises(InvalidMoney):
        money("-Infinity")


def test_money_rejects_float_nan():
    with pytest.raises(InvalidMoney):
        money(float("nan"))


def test_money_rejects_float_positive_infinity():
    with pytest.raises(InvalidMoney):
        money(float("inf"))


def test_money_rejects_float_negative_infinity():
    with pytest.raises(InvalidMoney):
        money(float("-inf"))


def test_money_rejects_a_decimal_nan():
    with pytest.raises(InvalidMoney):
        money(Decimal("NaN"))


def test_money_rejects_a_decimal_snan():
    with pytest.raises(InvalidMoney):
        money(Decimal("sNaN"))


def test_money_rejects_snan_as_a_string():
    with pytest.raises(InvalidMoney):
        money("sNaN")


def test_money_rejects_a_decimal_infinity():
    with pytest.raises(InvalidMoney):
        money(Decimal("Infinity"))


def test_invalid_money_is_a_domain_error():
    assert issubclass(InvalidMoney, PosError)
    with pytest.raises(PosError):
        money("NaN")