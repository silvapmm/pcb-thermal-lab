#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lee_lemczyk_vias.py
@brief The closed forms of Lee, Lemczyk and Yovanovich (1992, equations 1 to 7) for a staggered via island, and the two numbers the paper prints for its resistance (0.196 and 0.342 K/W).
@details Equations 1 (die attach pad or fourth via pad: a ring source on one face, adiabatic rim, isothermal other face), 2 (the barrel, one-dimensional), 3 (intermediate pad: ring source,
         isothermal rim, adiabatic back face) and 7 (the island, four via layers) are evaluated with the Bessel-root series. The paper prints, on its page 60, the resistance of the via network
         0.196 K/W at 20 % routing and 0.342 K/W at 40 % routing for nine islands (Tables 1 and 2). The paper does not say which cell area a unit cell has nor what N counts, so two readings
         are run; the script prints both and says how far each is from the printed numbers. Nothing is fitted. Run: .venv/bin/python research/theory-sources/scripts/study_lee_lemczyk_vias.py
         (from the repository root; under a second).
"""

import numpy as np
from scipy.special import j0, j1, jn_zeros

A_IN, B_OUT, T_LAYER = 14e-6, 17.5e-6, 5e-6          # via inner and outer radius and layer thickness, Table 1 (35 um O.D., 28 um I.D., 5 um)
K_GOLD, K_CU = 310.0, 386.0                           # die attach pad and copper, Table 1
ISLANDS = {0.20: (1.683e-3, 314, 0.196), 0.40: (1.233e-3, 168, 0.342)}   # island side S, vias per island N, printed R_vias (page 60); Table 2


def r_pad_edge(k, c1, t, a, b, n=400):
    """!
    @brief Equation 1: pad with a ring source on one face, adiabatic rim, the other face isothermal (die attach pad or fourth via pad).
    @param k Conductivity in W/mK.
    @param c1 Radius of the unit cell in m.
    @param t Pad thickness in m.
    @param a Inner radius of the ring in m.
    @param b Outer radius of the ring in m.
    @param n Number of Bessel roots.
    @return float Resistance in K/W.
    """
    ts, a_, b_ = t / c1, a / c1, b / c1
    al = b_ ** 2 - a_ ** 2                              # equation 4 (alpha = b*^2 - a*^2, the reading that makes equation 2 the barrel area)
    d = jn_zeros(1, n)                                  # roots of J1 (equation 5)
    s = np.sum(np.tanh(d * ts) / d ** 3 * (b_ * j1(d * b_) - a_ * j1(d * a_)) ** 2 / j0(d) ** 2)
    return (ts + 4.0 / al ** 2 * s) / (k * np.pi * c1)


def r_barrel(k, t, a, b):
    """!
    @brief Equation 2: the barrel as a one-dimensional tube.
    @param k Conductivity in W/mK.
    @param t Length in m.
    @param a Inner radius in m.
    @param b Outer radius in m.
    @return float Resistance in K/W.
    """
    return t / (k * np.pi * (b * b - a * a))


def r_pad_via(k, c2, t, a, b, n=400):
    """!
    @brief Equation 3: intermediate pad with a ring source, isothermal rim, adiabatic back face.
    @param k Conductivity in W/mK.
    @param c2 Radius of the unit cell in m.
    @param t Pad thickness in m.
    @param a Inner radius of the ring in m.
    @param b Outer radius of the ring in m.
    @param n Number of Bessel roots.
    @return float Resistance in K/W.
    """
    ts, a_, b_ = t / c2, a / c2, b / c2
    al = b_ ** 2 - a_ ** 2
    lam = jn_zeros(0, n)                                # roots of J0 (equation 6)
    s = np.sum(1.0 / (lam ** 3 * np.tanh(lam * ts)) * (b_ * j1(lam * b_) - a_ * j1(lam * a_)) ** 2 / j1(lam) ** 2)
    return 4.0 / (k * np.pi * c2 * al ** 2) * s


def island_resistance(side, n_vias, reading, f2):
    """!
    @brief Resistance of the nine islands in parallel for one reading of the layout.
    @param side Side of one island in m.
    @param n_vias Vias per island (Table 2).
    @param reading "N per layer" (each of the N vias heads a column) or "N total" (N / 4 columns, the 4 / N of equation 7).
    @param f2 Area of the unit cell of the intermediate pads over that of the die pad cell.
    @return float R_vias in K/W.
    """
    cols = n_vias if reading == "N per layer" else n_vias / 4.0
    a1 = side ** 2 / cols
    c1, c2 = np.sqrt(a1 / np.pi), np.sqrt(a1 * f2 / np.pi)
    col = r_pad_edge(K_GOLD, c1, T_LAYER, A_IN, B_OUT) + r_pad_edge(K_CU, c1, T_LAYER, A_IN, B_OUT) \
        + 6 * r_pad_via(K_CU, c2, T_LAYER, A_IN, B_OUT) + 4 * r_barrel(K_CU, T_LAYER, A_IN, B_OUT)   # equation 7 inside the bracket
    return col / cols / 9.0                              # the island is cols columns in parallel; nine islands


def main():
    """!
    @brief Print the table of both readings against the printed numbers.
    @return None.
    """
    print("Lee, Lemczyk, Yovanovich (1992): R_vias of nine islands, K/W")
    print("routing | printed | N per layer, f2 = 1 | N per layer, f2 = 1/4 | N total (4/N of eq. 7), f2 = 1")
    for routing, (side, n, printed) in ISLANDS.items():
        a = island_resistance(side, n, "N per layer", 1.0)
        b = island_resistance(side, n, "N per layer", 0.25)
        c = island_resistance(side, n, "N total", 1.0)
        print(f"{routing * 100:3.0f} %   | {printed:.3f}   | {a:.3f} ({100 * (a / printed - 1):+.0f} %) | {b:.3f} ({100 * (b / printed - 1):+.0f} %) | {c:.3f} ({100 * (c / printed - 1):+.0f} %)")
    ratio = island_resistance(*ISLANDS[0.40][:2], "N per layer", 0.25) / island_resistance(*ISLANDS[0.20][:2], "N per layer", 0.25)
    print(f"ratio of the 40 and 20 percent routing: printed {0.342 / 0.196:.3f}, N per layer with f2 = 1/4 {ratio:.3f}")


if __name__ == "__main__":
    main()
