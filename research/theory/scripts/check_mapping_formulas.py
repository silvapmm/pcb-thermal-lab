"""!
@file check_mapping_formulas.py
@brief Numerical check of the properties of the 2D effective-medium formulas used by the mapping research (Bruggeman, Hashin-Shtrikman, Wiener), the only confirmation they have in this repository because no textbook was read.
@details Reads the formulas from research/gerber-models/lib/conduction.py and checks: the Bruggeman root satisfies its own defining equation; it is sqrt(ab) at a fraction of 1/2 and obeys the Keller-Dykhne duality k(f) k(1 - f) = ab; the Hashin-Shtrikman bounds bracket it and are bracketed by the Wiener bounds; and the upper bound is the dual of the lower one in two dimensions. Prints the largest deviation of each property.
         Run: PYTHONPATH=. .venv/bin/python research/theory/scripts/check_mapping_formulas.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gerber-models" / "lib"))
import conduction as cd                                            # noqa: E402


def hsf(f, a, b):
    """!
    @brief The Hashin-Shtrikman expression with phase `b` as the matrix (2D).
    @param f Fraction of phase `a`.
    @param a Conductivity of the inclusion phase.
    @param b Conductivity of the matrix phase.
    @return Effective conductivity (array).
    """
    return b + f / (1.0 / (a - b) + (1.0 - f) / (2.0 * b))


def checks():
    """!
    @brief Evaluate the properties on a grid of fractions with the contrast of copper on laminate.
    @return dict of property name -> largest deviation (0 means exact).
    """
    a, b = cd.S_CU, cd.S_LAM
    f = np.linspace(0.01, 0.99, 99)
    k = cd.map_bruggeman(f, a, b)
    lo, up = cd.map_hashin_shtrikman(f, "lower", a, b), cd.map_hashin_shtrikman(f, "upper", a, b)
    out = {
        "Bruggeman residual of its defining equation": float(np.abs(f * (a - k) / (a + k) + (1 - f) * (b - k) / (b + k)).max()),
        "Bruggeman at 1/2 against sqrt(ab) (relative)": float(abs(cd.map_bruggeman(np.array([0.5]), a, b)[0] / np.sqrt(a * b) - 1)),
        "Bruggeman duality k(f) k(1 - f) against ab (relative)": float(np.abs(k * cd.map_bruggeman(1 - f, a, b) / (a * b) - 1).max()),
        "lower bound <= Bruggeman <= upper bound (violation)": float(max(np.max(lo - k), np.max(k - up), 0.0)),
        "Wiener harmonic <= HS lower, HS upper <= Wiener arithmetic (violation)": float(max(np.max(cd.map_power(f, -1, a, b) - lo), np.max(up - cd.map_power(f, 1, a, b)), 0.0)),
        "2D duality 1 / HS_upper = HS_lower of the dual medium (relative)": float(np.abs(1.0 / up - hsf(1 - f, 1.0 / b, 1.0 / a)).max() * b),
    }
    return out


def main():
    """!
    @brief Print the deviations.
    @return None.
    """
    for name, v in checks().items():
        print(f"{name:75s} {v:.2e}")


if __name__ == "__main__":
    main()
