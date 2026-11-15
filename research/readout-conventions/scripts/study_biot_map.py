#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_biot_map.py
@brief When does the surface temperature differ from the through-thickness mean: the map over Bi = h t / k and t / a, with the typical cases marked.
@details Answers: for a plate with a square source on one face and a film on the other, how large is (surface - column mean) as a share of the surface rise, over the two groups
         Bi = h t / k and t / a (plate side 5 a; sensitivity to 3 a and 10 a, and to the source mean in place of the centre). Closed-form series of lib/plate_series.py, checked against
         tests/helpers/layered3d.py. Prints the grid, the typical cases and the busbar closed form. Writes out/biot_map.npz for make_figures.py.
         Usage: .venv/bin/python research/readout-conventions/scripts/study_biot_map.py   (about 20 s, under 0.5 GB)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import plate_series as ps                                      # noqa: E402

BI = np.logspace(-4, 0.7, 25)
TA = np.logspace(-2.3, 1, 27)

# Typical cases: (name, t in m, k, h_eff of the cooled face in W/m2K, source side in m). h_eff of a copper layer on a PCB is the series film through the laminate
# gap to the next layer (k / d); of a plate it is the film or the TIM + heatsink figure that the case states. All are typical orders, not measurements.
CASES = [
    ("35 um Cu on FR-4 (0.3 W/mK, 0.2 mm gap), 5 mm part", 35e-6, 385.0, 0.3 / 0.2e-3, 5e-3),
    ("105 um Cu on FR-4, 5 mm part", 105e-6, 385.0, 0.3 / 0.2e-3, 5e-3),
    ("2 mm copper core, 1000 W/m2K, 5 mm part", 2e-3, 385.0, 1000.0, 5e-3),
    ("1.5 mm Al MCPCB base, 2000 W/m2K, 5 mm part", 1.5e-3, 150.0, 2000.0, 5e-3),
    ("case 2 plate (one centred source): 10 mm k150, 400 W/m2K, 10 mm", 10e-3, 150.0, 400.0, 10e-3),
    ("10 mm Al cold plate, 5000 W/m2K, 10 mm source", 10e-3, 200.0, 5000.0, 10e-3),
    ("3 mm Cu spreader, 20 W/m2K (air), 20 mm source", 3e-3, 385.0, 20.0, 20e-3),
    ("10 mm k50 plate, 400 W/m2K, 4 mm source", 10e-3, 50.0, 400.0, 4e-3),
]


def grid(W_over_a=5.0, source_mean=False):
    """!
    @brief The fraction (surface - mean) / surface rise over the Bi and t/a grid.
    @param W_over_a Plate side over source side.
    @param source_mean Average over the source instead of the centre.
    @return Array (len(TA), len(BI)).
    """
    return np.array([[ps.delta_fraction(b, ta, W_over_a, 160, source_mean) for b in BI] for ta in TA])


def main():
    """!
    @brief Run the map, the sensitivities and the typical cases and print them.
    @return None.
    """
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    g5 = grid(5.0)
    g3, g10, gm = grid(3.0), grid(10.0), grid(5.0, True)
    np.savez(os.path.join(HERE, "..", "out", "biot_map.npz"), BI=BI, TA=TA, g5=g5, g3=g3, g10=g10, gm=gm)
    print("fraction (surface - column mean) / surface rise, plate 5 a, centre of the source; rows t/a, columns Bi")
    print("t/a \\ Bi " + " ".join(f"{b:8.1e}" for b in BI[::4]))
    for i in range(0, len(TA), 3):
        print(f"{TA[i]:9.3f} " + " ".join(f"{100 * g5[i, j]:7.3f}%" for j in range(0, len(BI), 4)))
    # Review: the differences are printed in percentage points (the first version printed the raw fraction, 0.18 and 0.28, which the README read as
    # 0.18 and 0.28 points: they are 18 and 28 points; the plate width W/a is a third group of the map, not a detail)
    print("sensitivity: max over the grid of |g(3a) - g(5a)|, |g(10a) - g(5a)|, |source mean - centre| (percentage points):",
          f"{100 * np.abs(g3 - g5).max():.2f}", f"{100 * np.abs(g10 - g5).max():.2f}", f"{100 * np.abs(gm - g5).max():.2f}")
    print("\ntypical cases (plate 5 a at least; the plate side is 5 a and the film acts on the whole bottom face):")
    print(f"{'case':58s} {'Bi':>9s} {'t/a':>7s} {'centre %':>9s} {'src mean %':>10s}")
    rows = []
    for name, t, k, h, a in CASES:
        bi, ta = h * t / k, t / a
        c = ps.delta_fraction(bi, ta, 5.0, 300)
        m = ps.delta_fraction(bi, ta, 5.0, 300, True)
        rows.append((name, bi, ta, c, m))
        print(f"{name:58s} {bi:9.2e} {ta:7.3f} {100 * c:9.4f} {100 * m:10.4f}")
    np.save(os.path.join(HERE, "..", "out", "cases.npy"), np.array([(r[1], r[2], r[3]) for r in rows]))
    # Review: the same cases on plates 3, 10 and 12.5 source sides wide (the plates of study_thick_cases.py are 50 mm, 12.5 a for a 4 mm source):
    # the film rise q0/h of the whole plate is in the denominator, so a wider plate reads a larger share
    print(f"\nthe same cases, centre %, against the plate width W/a: {'3':>7s} {'5':>7s} {'10':>7s} {'12.5':>7s}")
    for name, t, k, h, a in CASES:
        bi, ta = h * t / k, t / a
        print(f"{name:58s} " + " ".join(f"{100 * ps.delta_fraction(bi, ta, w, 300):7.2f}" for w in (3.0, 5.0, 10.0, 12.5)))
    print("\nJoule-heated bar (busbar, IPC-2152 type conductor), generation g uniform, film h on both faces, 1D through the thickness t:")
    print("  (T_centre - T_surface) / (T_surface - T_amb) = Bi / 4 ;  (T_surface - T_mean) / (T_surface - T_amb) = -Bi / 6 (the mean is above the surface)")
    for name, t, k, h in (("3 mm Cu busbar, 15 W/m2K", 3e-3, 385.0, 15.0), ("2 mm Cu bar, 100 W/m2K", 2e-3, 385.0, 100.0),
                          ("35 um Cu trace, 15 W/m2K", 35e-6, 385.0, 15.0), ("10 mm Al bar, 15 W/m2K", 10e-3, 200.0, 15.0)):
        bi = h * t / k
        print(f"  {name:32s} Bi {bi:9.2e}   mean - surface {100 * bi / 6:8.4f} % of the rise")


if __name__ == "__main__":
    main()
