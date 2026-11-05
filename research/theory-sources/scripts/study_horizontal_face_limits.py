#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_horizontal_face_limits.py
@brief Where does the program's horizontal-plate law leave the published range and the Yovanovich-Jafarpur bounds, and what does that cost on a board?

Question (README 9.1, plan study S0): the face looking up uses 0.54 Ra^(1/4) (0.15 Ra^(1/3) above 1e7) on L = A/P.  Yovanovich and Jafarpur (1993) give
bounds for a plate with one active face (eq 25 upper 3.545 + 0.571 Ra^(1/4), eq 26 lower 2.257 + 0.382 Ra^(1/4), Ra on sqrt(A), air, p 11; the diffusive limits are eqs 20
and 21 on p 10) and quote the range of the Lloyd-Moran 0.54 law, eq 17, 2.2e4 <= Ra_L <= 8e6 on L = A/P (p 7, second hand; a mass-transfer correlation, Sc about 2300).  Part 1 prints the program's h against the two bounds and the Ra on A/P of seven plates; part 2 replaces both
faces in memory by the upper bound (eq 25 up, half the body-gravity function down, G_down = G_up / 2 as accepted on p 9) and runs the FVM at 2 mm on four canonical
two-layer boards (10 x 10 mm part in the middle, computed h with radiation).  The program is imported and never edited: the replacement lives in the process only.

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_horizontal_face_limits.py   (about 3 s, < 0.2 GB)
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import api, convection as cv  # noqa: E402
from pcbthermal.model import Problem  # noqa: E402

AMBIENT = 25.0                                              # degC, ambient of both parts
LLOYD_MORAN_RA = (2.2e4, 8e6)                               # published range of the 0.54 law on A/P (Yovanovich and Jafarpur 1993, p 7)
# Plates of part 1: (length mm, width mm, surface excess K)
PLATES = [(40, 30, 5), (40, 30, 20), (60, 40, 20), (100, 80, 20), (100, 80, 60), (160, 100, 40), (300, 200, 20)]
# Boards of part 2: (length mm, width mm, power W)
BOARDS = [(60, 40, 1.0), (100, 80, 2.0), (160, 100, 4.0), (300, 200, 3.0)]


def face_limits(plates=PLATES, ambient=AMBIENT):
    """!
    @brief The up-face coefficient of the program against the bounds of Yovanovich and Jafarpur (1993), eq 25 and 26.
    @param plates   List of (length mm, width mm, excess K).
    @param ambient  Ambient temperature in degC.
    @return list of dict: plate, h_prog, h_upper, h_lower in W/m2K, ra_ap (Ra on A/P), ratio_upper (h_prog/h_upper - 1), inside (Ra on A/P in the published range).
    """
    rows = []
    for a, b, dt in plates:
        area, per = a * b * 1e-6, 2 * (a + b) * 1e-3
        h_prog, ra_ap = cv.h_natural_horizontal(ambient + dt, ambient, area / per, True)
        props = cv.air_properties(ambient + dt / 2)
        side = math.sqrt(area)                                # the bounds use sqrt(A) as the length
        ra_s = cv.rayleigh(dt, side, props)
        h_up = (3.545 + 0.571 * ra_s ** 0.25) * props["k"] / side
        h_lo = (2.257 + 0.382 * ra_s ** 0.25) * props["k"] / side
        rows.append(dict(plate=(a, b, dt), h_prog=h_prog, h_upper=h_up, h_lower=h_lo, ra_ap=ra_ap, ratio_upper=h_prog / h_up - 1.0,
                         inside=LLOYD_MORAN_RA[0] <= ra_ap <= LLOYD_MORAN_RA[1]))
    return rows


def board_impact(boards=BOARDS, cell_mm=2.0):
    """!
    @brief Change of the FVM board maximum and mean when both faces use the Yovanovich-Jafarpur upper bound (in memory only).
    @param boards   List of (length mm, width mm, power W).
    @param cell_mm  FVM cell in mm.
    @return list of dict: board, rise_max, rise_mean (K, program), d_max, d_mean (fractions of the rise).
    """
    original = cv.h_natural_horizontal
    area_box = [0.0]

    def yj_upper(t_s, t_a, length, facing_up):
        """!
        @brief Replacement for h_natural_horizontal: eq 25 on sqrt(A) for the face looking up, G/2 for the face looking down.
        @param t_s Surface temperature in degC.
        @param t_a Ambient in degC.
        @param length A/P in m (ignored; sqrt(A) of the board in the closure is used).
        @param facing_up True if the hot face looks up.
        @return tuple (h in W/m2K, Ra).
        """
        side = math.sqrt(area_box[0])
        dt = t_s - t_a
        props = cv.air_properties(0.5 * (t_s + t_a))
        ra = cv.rayleigh(max(abs(dt), 1e-3), side, props)
        up = facing_up if dt >= 0 else not facing_up
        return (3.545 + (0.571 if up else 0.2855) * ra ** 0.25) * props["k"] / side, ra

    opts = api.SolverOptions(models=("fvm",), cell_mm=cell_mm)
    out = []
    try:
        for w, hgt, pw in boards:
            area_box[0] = w * hgt * 1e-6
            res = []
            for fn in (original, yj_upper):
                cv.h_natural_horizontal = fn
                pr = Problem.new(w, hgt, layers=2, h_mode="computed", ambient=AMBIENT)
                pr.add_zone(1, rect=(0, 0, w, hgt), fill=1.0)
                pr.add_zone(2, rect=(0, 0, w, hgt), fill=1.0)
                pr.add_heater(1, pw, rect=(w / 2 - 5, hgt / 2 - 5, w / 2 + 5, hgt / 2 + 5))
                r = api.simulate(pr, opts).results["fvm"]
                res.append((r.t_max - AMBIENT, r.t_mean - AMBIENT))
            out.append(dict(board=(w, hgt, pw), rise_max=res[0][0], rise_mean=res[0][1], d_max=res[1][0] / res[0][0] - 1.0, d_mean=res[1][1] / res[0][1] - 1.0))
    finally:
        cv.h_natural_horizontal = original                  # always restore the program's function
    return out


def main():
    """!
    @brief Print both tables.
    @return None.
    """
    print("1. up face: h program | YJ upper eq 25 (program vs upper) | YJ lower eq 26 | Ra on A/P (published range 2.2e4..8e6)")
    for r in face_limits():
        a, b, dt = r["plate"]
        print(f"  {a}x{b} dT {dt}: {r['h_prog']:.2f} | {r['h_upper']:.2f} ({100 * r['ratio_upper']:+.0f} %) | {r['h_lower']:.2f} | Ra {r['ra_ap']:.2e}{'' if r['inside'] else '  OUT'}")
    print("2. board maximum and mean with both faces on the YJ upper bound (FVM 2 mm, 2 layers, 10 x 10 mm part)")
    for r in board_impact():
        w, h, p = r["board"]
        print(f"  {w}x{h} {p} W: rise max {r['rise_max']:.2f} K mean {r['rise_mean']:.2f} K | max {100 * r['d_max']:+.1f} % mean {100 * r['d_mean']:+.1f} %")


if __name__ == "__main__":
    main()
