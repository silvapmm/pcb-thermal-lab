#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sweep.py
@brief How big is the surface-minus-column-mean difference, against the thickness, the source size and the conductivity; and the same on a thin-copper board (it must not matter).

@details Independent 3D solver only (`tests/helpers/layered3d.py`, imports nothing from pcbthermal). Part 1: a plate 50 x 50 mm under a centred square source of side a, bottom film
         400 W/m2K, top adiabatic, thickness 0.035 to 20 mm, k 385 / 150 / 50 W/mK: the difference between the surface under the source centre and the column mean, divided by the
         bound q'' t / (2 k) of the program's warning, and the parabolic read-out `surface_readout.offsets` against it. Part 2: a four-layer-like board (35 um copper, 1.5 mm
         laminate, 35 um copper) with a part of 2 W on 5 x 5 mm: the surface of the copper under the part against the column mean of the copper slab, in mK and in % of the rise.
         Usage: .venv/bin/python research/through-thickness-readout/scripts/study_sweep.py   (about 40 s, under 1 GB)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "tests", "helpers")):
    sys.path.insert(0, p)
import layered3d as L                                          # noqa: E402
import surface_readout as sr                                   # noqa: E402

W = 50e-3                                                      # plate side in m
DX = 1e-3                                                      # plan cell in m
H = 400.0                                                      # bottom film in W/m2K
NSUB = 8                                                       # sub-slabs through the plate


def centre_cells(a):
    """!
    @brief Source rectangle centred on a plate cell corner (its edges on cell lines).
    @param a Side in m (a multiple of 2 DX).
    @return Tuple (x0, y0, x1, y1) in m.
    """
    c = W / 2
    return (c - a / 2, c - a / 2, c + a / 2, c + a / 2)


def one_case(t, k, a, power=10.0):
    """!
    @brief One plate: the 3D difference and the parabolic estimate at the source centre.
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param a Source side in m.
    @param power Source power in W (the ratio does not depend on it).
    @return dict with the 3D difference d3, the bound, the parabola, the flux ratio, all in K or W/m2.
    """
    n = int(round(W / DX))
    r = L.solve(DX, n, n, [(t, k, NSUB)], centre_cells(a), power, 0.0, H)
    dz = np.array(r["dz"])
    col = np.tensordot(dz / dz.sum(), r["T"], axes=(0, 0))
    j = n // 2
    sl = (slice(j - 1, j + 1), slice(j - 1, j + 1))
    d3 = float(r["surface_top"][sl].mean() - col[sl].mean())
    q = power / (a * a)
    theta_bot = float(r["T"][-1][sl].mean())
    qb = float(sr.bottom_flux(col[sl].mean(), H, t, k))        # the face loses heat: negative inflow, with the film through the half layer
    d_par, _ = sr.offsets(t, k, q, qb)
    return {"d3": d3, "bound": float(sr.column_bound(t, k, q)), "parabola": float(d_par), "qb_over_q": -qb / q, "rise_centre": float(col[sl].mean()), "theta_bot": theta_bot}


def main():
    """!
    @brief Part 1 (sweep) and part 2 (thin copper board); print the tables and write out/sweep.json.
    """
    out = {"sweep": [], "thin": {}}
    print("Part 1: 3D difference (surface under the source centre minus column mean) over the bound q'' t/(2k); parabola over the 3D difference")
    print("k W/mK  a mm  t mm  | d3 K    bound K  d3/bound | parabola/d3 | q_bot/q | d3 in % of the centre rise")
    for k in (385.0, 150.0, 50.0):
        for a_mm in (4.0, 10.0, 20.0):
            for t_mm in (0.035, 0.5, 2.0, 5.0, 10.0, 20.0):
                r = one_case(t_mm * 1e-3, k, a_mm * 1e-3)
                r.update(k=k, a_mm=a_mm, t_mm=t_mm)
                out["sweep"].append(r)
                print(f"{k:6.0f} {a_mm:5.0f} {t_mm:6.3f} | {r['d3']:8.4f} {r['bound']:8.4f} {r['d3'] / r['bound']:7.3f} | {r['parabola'] / r['d3']:9.3f} | {r['qb_over_q']:6.3f} | {100 * r['d3'] / r['rise_centre']:6.3f} %")
    # Part 2: thin copper on a laminate (independent 3D with the copper slab resolved)
    n = int(round(40e-3 / DX))
    src = (17e-3, 17e-3, 23e-3, 23e-3)
    slabs = [(35e-6, 385.0, 8), (1.53e-3, 0.3, 12), (35e-6, 385.0, 8)]
    r = L.solve(DX, n, n, slabs, src, 2.0, 10.0, 10.0, film_under_source=True)
    dz = np.array(r["dz"])
    cu = slice(0, 8)
    mean_cu = np.tensordot(dz[cu] / dz[cu].sum(), r["T"][cu], axes=(0, 0))
    j = n // 2
    sl = (slice(j - 1, j + 1), slice(j - 1, j + 1))
    d = float(r["surface_top"][sl].mean() - mean_cu[sl].mean())
    rise = float(mean_cu[sl].mean())
    q = 2.0 / (6e-3 * 6e-3)
    out["thin"] = {"d_mK": 1e3 * d, "rise": rise, "pct": 100 * d / rise, "bound_mK": 1e3 * float(sr.column_bound(35e-6, 385.0, q))}
    print(f"\nPart 2: 35 um copper / 1.53 mm laminate / 35 um copper, 2 W on 6 x 6 mm, h 10: surface minus copper column mean {1e3 * d:.3f} mK = {100 * d / rise:.5f} % of the {rise:.2f} K rise (bound q t/2k {out['thin']['bound_mK']:.3f} mK)")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "sweep.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
