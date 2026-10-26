"""!
@file test_numfmt.py
@brief Tests of the engineering notation helper (pcbthermal.numfmt) and of its use on the screen.
"""

import math

import pytest

from pcbthermal.numfmt import eng, num


@pytest.mark.parametrize("value, text", [
    (0.0, "0"), (-0.0, "0"), (1e-12, "1E-12"), (12e-12, "12E-12"), (1.5e-9, "1.5E-9"), (120e-6, "120E-6"),
    (999.9e-6, "1E-3"), (1e3, "1E3"), (3300.0, "3.3E3"), (1.2345e6, "1.23E6"), (-4.7e-3, "-4.7E-3"), (47.0, "47"),
    (999.4, "999"), (123456.0, "123E3"), (-1e-12, "-1E-12"), (0.5, "500E-3"), (1e12, "1E12"),
])
def test_eng_three_digits(value, text):
    """!
    @brief Engineering notation: the exponent is a multiple of three, the mantissa from 1 up to 999.
    @param value Number written.
    @param text Expected text.
    """
    assert eng(value) == text


def test_eng_rounding_carries_to_the_next_power_of_three():
    """!
    @brief 999.96E-6 with 3 digits is 1E-3, never "1000E-6"; with 5 digits it stays.
    """
    assert eng(999.96e-6, 3) == "1E-3"
    assert eng(999.96e-6, 5) == "999.96E-6"
    assert eng(999.5, 3) == "1E3"
    assert eng(-999.96e-6, 3) == "-1E-3"


def test_eng_sign_and_special_values():
    """!
    @brief Explicit sign on request, and the non-finite values.
    """
    assert eng(1.5e-9, 3, sign=True) == "+1.5E-9" and eng(-1.5e-9, 3, sign=True) == "-1.5E-9" and eng(0.0, 3, sign=True) == "+0"
    assert eng(math.nan) == "nan" and eng(math.inf) == "inf" and eng(-math.inf) == "-inf"


@pytest.mark.parametrize("value", [1e-12, 1.5e-9, 120e-6, 3.3e3, 1.2345e6, 47.0, -4.7e-3, 999.4, 5e-7])
def test_eng_value_is_kept(value):
    """!
    @brief The text read back as a number equals the value to the digits written.
    @param value Number written.
    """
    assert float(eng(value, 6)) == pytest.approx(value, rel=1e-5)


def test_num_is_plain_when_no_exponent_is_needed():
    """!
    @brief num follows the "g" format except that an exponent becomes engineering notation.
    """
    assert num(0.45) == "0.45" and num(12.5, 3) == "12.5" and num(100000.0) == "100000"
    assert num(1e6) == "1E6" and num(2.5e-7, 3) == "250E-9" and num(1234.5, 3) == "1.23E3" and num(0.0) == "0"
    assert "e" not in num(1e-20) and "e" not in num(123456789.0, 4)


def test_balance_column_of_the_summary_is_in_engineering_notation():
    """!
    @brief The Markdown summary shows the power balance without an "e" exponent and with an explicit sign.
    """
    from pcbthermal.api import SolverOptions, simulate
    from pcbthermal.examples import example_board
    res = simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))
    row = [ln for ln in res.to_markdown().split("\n") if ln.startswith("| fvm")][0]
    balance = row.split("|")[7].strip()
    assert "e" not in balance.lower().replace("e-", "x") or "E" in balance
    assert balance[0] in "+-" and "e" not in balance
    assert balance == "+0" or "E" in balance or balance[1:].replace(".", "").isdigit()
