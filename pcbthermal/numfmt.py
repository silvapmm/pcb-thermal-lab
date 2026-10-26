"""!
@file numfmt.py
@brief Number to text for the screen and the reports: engineering notation instead of the exponential form.

@details Every number that would be written as "1e-12" or "1.5e+03" is written with an exponent that is a
multiple of three and a mantissa from 1 up to 999.99...: 12E-12, 1.5E-9, 120E-6, 3.3E3. Numbers that need no
exponent are written in plain decimal with the decimal point and no thousands separator. Machine-exchange files
(JSON projects, CSV tables) do not use this module: they keep the standard float text so that other programs read them.
"""

import math


def eng(value, digits=3, sign=False):
    """!
    @brief Write a number in engineering notation.
    @param value Number to write (dimensionless; the caller adds the unit).
    @param digits Significant digits of the mantissa (at least 1).
    @param sign True to write an explicit "+" in front of a positive number (a "-" is always written).
    @return str Text such as "12E-12", "1.5E-9", "120E-6", "3.3E3", "-4.7E-3"; "0" for zero; "nan", "inf" or "-inf" for those values.
    @note Exponent 0 gives the plain mantissa ("47"); 0.5 is "500E-3". A mantissa that rounds up to 1000 carries to the next power of three (999.96E-6 with 3 digits is "1E-3").
    """
    value = float(value)
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 and not sign else ("+inf" if value > 0 else "-inf")
    digits = max(int(digits), 1)
    if value == 0.0:
        return "+0" if sign else "0"
    negative = value < 0
    mag = abs(value)
    # Decimal exponent of the number, then the multiple of three below it
    exp10 = math.floor(math.log10(mag))
    exp3 = 3 * math.floor(exp10 / 3)
    mant = mag / 10.0 ** exp3
    # Round to the significant digits; the digits after the point depend on how many the mantissa has before it
    int_digits = len(str(int(mant))) if mant >= 1 else 1
    decimals = max(digits - int_digits, 0)
    rounded = round(mant, decimals)
    if rounded >= 1000.0:                                 # 999.96 with 3 digits rounds to 1000: carry to the next power of three
        exp3 += 3
        mant = mag / 10.0 ** exp3
        int_digits = len(str(int(mant))) if mant >= 1 else 1
        decimals = max(digits - int_digits, 0)
        rounded = round(mant, decimals)
    text = f"{rounded:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")               # 1.50 is written 1.5
    if exp3 != 0:
        text += f"E{exp3}"
    if negative:
        text = "-" + text
    elif sign:
        text = "+" + text
    return text


def num(value, digits=6, sign=False):
    """!
    @brief Write a number like the "g" format, but in engineering notation when it would need an exponent.
    @param value Number to write.
    @param digits Significant digits (like the precision of the "g" format).
    @param sign True to write an explicit "+" in front of a positive number.
    @return str The plain decimal text when the "g" format gives no exponent (0.45, 12.5, 100000), otherwise eng(value, digits, sign).
    """
    value = float(value)
    if not math.isfinite(value) or value == 0.0:
        return eng(value, digits, sign)
    text = format(value, f"+.{max(int(digits), 1)}g" if sign else f".{max(int(digits), 1)}g")
    if "e" in text:
        return eng(value, digits, sign)
    return text
