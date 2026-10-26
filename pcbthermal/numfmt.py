"""!
@file numfmt.py
@brief Number to text for the screen and the reports: plain decimal in a window, engineering notation outside it.

@details A number whose size is inside the plain window (PLAIN_MIN <= |x| < PLAIN_MAX, 0.01 up to but not including
10000) is written in plain decimal with the decimal point and no thousands separator (0.9, 25.3, 1234.5). Zero is "0".
Every other number is written in engineering notation: an exponent that is a multiple of three and a mantissa from
1 up to 999.99 with two decimals, trailing zeros kept (10.03E-3, 10.00E-6, 10.04E3, 120.50E6). Machine-exchange files
(JSON projects, CSV tables) do not use this module: they keep the standard float text so that other programs read them.
"""

import math

PLAIN_MIN = 0.01        # Smallest size written in plain decimal (inclusive); below it the engineering notation is used
PLAIN_MAX = 10000.0     # Largest size written in plain decimal (exclusive); from it up the engineering notation is used
ENG_DECIMALS = 2        # Decimals of the mantissa in engineering notation


def eng(value, decimals=ENG_DECIMALS, sign=False):
    """!
    @brief Write a number in engineering notation, whatever its size.
    @param value Number to write (dimensionless; the caller adds the unit).
    @param decimals Decimals of the mantissa; trailing zeros are kept (10.00E-3 stays 10.00E-3).
    @param sign True to write an explicit "+" in front of a positive number (a "-" is always written).
    @return str Text such as "12.00E-12", "1.50E-9", "120.00E-6", "3.30E3", "-4.70E-3"; "0" for zero ("+0" with sign); "nan", "inf" or "-inf" for those values.
    @note A mantissa that rounds up to 1000 carries to the next power of three (999.996E-6 is "1.00E-3"). Exponent 0 gives the mantissa alone ("47.00").
    """
    value = float(value)
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "-inf" if value < 0 else ("+inf" if sign else "inf")
    if value == 0.0:
        return "+0" if sign else "0"
    decimals = max(int(decimals), 0)
    mag = abs(value)

    def mantissa(e3):
        # Scale in two steps: 10.0 ** -324 is 0 and 10.0 ** 324 overflows, so a subnormal number (5e-324) cannot be divided by one power
        if abs(e3) < 300:
            return round(mag / 10.0 ** e3, decimals)
        half = (-e3) // 2
        return round(mag * 10.0 ** half * 10.0 ** (-e3 - half), decimals)

    exp3 = 3 * math.floor(math.floor(math.log10(mag)) / 3)
    mant = mantissa(exp3)
    if mant >= 1000.0:                                    # 999.996 with 2 decimals rounds to 1000.00: carry to the next power of three
        exp3 += 3
        mant = mantissa(exp3)
    if mant < 1.0:                                        # Floating-point error in log10 just below a power of ten
        exp3 -= 3
        mant = mantissa(exp3)
    text = f"{mant:.{decimals}f}"
    if exp3 != 0:
        text += f"E{exp3}"
    if value < 0:
        text = "-" + text
    elif sign:
        text = "+" + text
    return text


def num(value, digits=6, sign=False):
    """!
    @brief Write a number as plain decimal inside the window PLAIN_MIN <= |x| < PLAIN_MAX and in engineering notation outside it.
    @param value Number to write.
    @param digits Significant digits of the plain decimal (like the precision of the "g" format; trailing zeros are dropped there).
    @param sign True to write an explicit "+" in front of a positive number.
    @return str Plain text such as "0.45", "25.3", "1234.5", or engineering notation (see eng); "0" for zero.
    """
    value = float(value)
    mag = abs(value)
    if not math.isfinite(value) or value == 0.0 or not (PLAIN_MIN <= mag < PLAIN_MAX):
        return eng(value, ENG_DECIMALS, sign)
    # Significant digits without an exponent: round, then write in fixed notation and drop the trailing zeros
    decimals = max(int(digits) - 1 - math.floor(math.log10(mag)), 0)
    rounded = round(value, decimals)
    if abs(rounded) >= PLAIN_MAX:                         # 9999.96 rounded to 3 digits reaches the top of the window
        return eng(value, ENG_DECIMALS, sign)
    text = f"{rounded:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if sign and value > 0:
        text = "+" + text
    return text
