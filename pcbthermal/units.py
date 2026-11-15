#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file units.py
@brief The one place of the unit and typography rule of everything the user reads (window, guide, reports, warnings, command line).

The rule (maintainer, after the literature check `releases/2.8.0/fem-model/UNITS_DELTA_T.md`: SI Brochure 9th edition, p. 129 and 136, a temperature difference
is the same number in K or in degrees Celsius and K is the SI-preferred form):

* an ABSOLUTE temperature is written in `°C`;
* every DIFFERENCE, rise, margin, oscillation (swing), gradient step and oscillation threshold is written in `K`;
* a thermal resistance is `K/W` (and the compound units W/m·K, m²·K/W keep K);
* a micrometre is `µm` (U+00B5); dimensions use `×` between numbers; layers read `1 (top)`, `2`, `4 (bottom)`.

Files read by programs (CSV, JSON, project files) keep their ASCII names and plain numbers (the JSON field `threshold_c` stays; only its visible label follows the rule).
No GUI import: the command line and the reports use it too. A later change of the convention is one edit here and in `FORBIDDEN`.
"""

TEMP = "°C"                       # Absolute temperature
DELTA = "K"                       # Rise, difference, margin, oscillation, gradient step (the number is the same in °C; K is the SI-preferred form)
RESISTANCE = "K/W"                # Thermal resistance
MICRO_M = "µm"                    # Micrometre, with the micro sign U+00B5
TIMES = "×"                       # Between the numbers of a size: 100 × 80 mm
MINUS = "−"                  # The minus sign of an on-screen number (files keep the ASCII hyphen)
ELLIPSIS = "…"                    # A menu or button that opens a dialog ends with this character, not three dots
DELTA_T = "ΔT"                    # The symbol of a difference of temperature (its unit is DELTA)

# The old forms that must not appear in anything visible, each with the reason; the typography scan reads this list.
# Each item is (regular expression, what to write instead, why).
FORBIDDEN = (
    (r"\bdegC\b", TEMP, "plain-ASCII spelling of the degree sign; the symbol is °C"),
    (r"\bdT C\b", f"{DELTA_T} {DELTA}", "a difference is in K, and 'dT' is the symbol ΔT"),
    (r"ΔT \[?°C\]?", f"{DELTA_T} {DELTA}", "ΔT is a difference: K"),
    (r"Osc\. °C|Oscillation \[°C\]", f"Oscillation {DELTA}", "an oscillation is a difference: K"),
    (r"\d ?um\b", f"{MICRO_M}", "'um' is the ASCII spelling; the symbol is µm"),
    (r"\d x \d", f"{TIMES}", "a size is written with the multiplication sign"),
    (r"\bRth K/W\b", "Rθ K/W", "the resistance symbol is Rθ"),
    (r"\bCancel calculation\b", "Stop calculation", "one word for one action: Stop"),
    (r"\b[1-9] (top|bottom)\b", "1 (top), 4 (bottom)", "the layer reads as in the Properties panel"),
)


def layer_label(layer, n):
    """!
    @brief Text of a copper layer in a list (the Layer box of the tool bar): `1 (top)`, `2`, `4 (bottom)`.
    @param layer Layer index (0-based).
    @param n Number of copper layers of the board.
    @return str.
    """
    return f"{layer + 1}" + (" (top)" if layer == 0 else " (bottom)" if layer == n - 1 else "")


def delta_text(value, digits=1):
    """!
    @brief A temperature difference as text in K, with the on-screen minus sign.
    @param value Difference in K (the same number as in °C).
    @param digits Decimals, count.
    @return str, for example "12.3 K" or "−0.4 K".
    """
    return f"{value:.{digits}f} {DELTA}".replace("-", MINUS)


def temp_text(value, digits=1):
    """!
    @brief An absolute temperature as text in °C, with the on-screen minus sign.
    @param value Temperature in °C.
    @param digits Decimals, count.
    @return str, for example "85.3 °C".
    """
    return f"{value:.{digits}f} {TEMP}".replace("-", MINUS)
