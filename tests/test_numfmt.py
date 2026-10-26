"""!
@file test_numfmt.py
@brief Tests of the number format helper (pcbthermal.numfmt): plain decimal in a window, engineering notation outside it.
"""

import math

import pytest

from pcbthermal import numfmt
from pcbthermal.numfmt import eng, num


@pytest.mark.parametrize("value, text", [
    (0.0, "0"), (-0.0, "0"), (1e-12, "1.00E-12"), (12e-12, "12.00E-12"), (1.5e-9, "1.50E-9"), (120e-6, "120.00E-6"),
    (10.03e-3, "10.03E-3"), (10e-3, "10.00E-3"), (10e-6, "10.00E-6"), (10.04e3, "10.04E3"), (120.5e6, "120.50E6"),
    (999.9e-6, "999.90E-6"), (1e3, "1.00E3"), (3300.0, "3.30E3"), (1.2345e6, "1.23E6"), (-4.7e-3, "-4.70E-3"), (47.0, "47.00"),
    (999.4, "999.40"), (123456.0, "123.46E3"), (-1e-12, "-1.00E-12"), (0.5, "500.00E-3"), (1e12, "1.00E12"),
])
def test_eng_two_decimals_trailing_zeros_kept(value, text):
    """!
    @brief Engineering notation: exponent a multiple of three, mantissa from 1 to 999.99 with two decimals, zeros kept.
    @param value Number written.
    @param text Expected text.
    """
    assert eng(value) == text


def test_eng_rounding_carries_to_the_next_power_of_three():
    """!
    @brief 999.996E-6 is 1.00E-3, never "1000.00E-6"; more decimals keep it.
    """
    assert eng(999.996e-6) == "1.00E-3"
    assert eng(999.996e-6, 4) == "999.9960E-6"
    assert eng(999.996) == "1.00E3"
    assert eng(-999.996e-6) == "-1.00E-3"
    assert eng(999.994e-6) == "999.99E-6"


def test_eng_sign_and_special_values():
    """!
    @brief Explicit sign on request, and the non-finite values.
    """
    assert eng(1.5e-9, sign=True) == "+1.50E-9" and eng(-1.5e-9, sign=True) == "-1.50E-9" and eng(0.0, sign=True) == "+0"
    assert eng(math.nan) == "nan" and eng(math.inf) == "inf" and eng(-math.inf) == "-inf"


@pytest.mark.parametrize("value", [1e-12, 1.5e-9, 120e-6, 3.3e3, 1.2345e6, 47.0, -4.7e-3, 999.4, 5e-7, 1e-3, 1e-6, 1e9])
def test_eng_value_is_kept(value):
    """!
    @brief The text read back as a number equals the value to the decimals written.
    @param value Number written.
    """
    assert float(eng(value, 6)) == pytest.approx(value, rel=1e-5)


def test_the_plain_window_has_named_limits():
    """!
    @brief The window is 0.01 up to but not including 10000, held in two constants.
    """
    assert numfmt.PLAIN_MIN == 0.01 and numfmt.PLAIN_MAX == 10000.0


@pytest.mark.parametrize("value, text", [
    (0.9, "0.9"), (0.5, "0.5"), (25.3, "25.3"), (1234.5, "1234.5"), (0.45, "0.45"), (0.01, "0.01"), (9999.5, "9999.5"), (0.0, "0"),
    (-25.3, "-25.3"), (100000.0 / 10, "10.00E3"), (10000.0, "10.00E3"), (0.00999, "9.99E-3"), (1e-12, "1.00E-12"), (2.44e6, "2.44E6"),
    (1e-3, "1.00E-3"),
])
def test_num_plain_inside_the_window_and_engineering_outside(value, text):
    """!
    @brief Plain decimal for 0.01 <= |x| < 10000, engineering notation elsewhere, zero as "0".
    @param value Number written.
    @param text Expected text.
    """
    assert num(value) == text


def test_num_digits_sign_and_edge_of_the_window():
    """!
    @brief Significant digits of the plain part, explicit sign, and a rounding that reaches the top of the window.
    """
    assert num(12.3456, 3) == "12.3" and num(1234.7, 3) == "1235" and num(0.45, sign=True) == "+0.45" and num(-0.45, sign=True) == "-0.45"
    assert num(9999.96, 3) == "10.00E3"
    assert num(1.5e-9, sign=True) == "+1.50E-9" and num(0.0, sign=True) == "+0" and num(math.inf) == "inf" and num(math.nan) == "nan"


def test_balance_column_of_the_summary_is_in_engineering_notation():
    """!
    @brief The Markdown summary shows the power balance without an "e" exponent and with an explicit sign.
    """
    from pcbthermal.api import SolverOptions, simulate
    from pcbthermal.examples import example_board
    res = simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))
    row = [ln for ln in res.to_markdown().split("\n") if ln.startswith("| fvm")][0]
    balance = row.split("|")[7].strip()
    assert balance[0] in "+-" and "e" not in balance and (balance == "+0" or "E" in balance or float(balance) < 0.01)
