#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cavity.py
@brief Does the new primitive-variable solver (lib/mac2d.py) reproduce the differentially heated square cavity of de Vahl Davis (1983)?
@details Published case: air, Pr = 0.71, square cavity, hot wall x = 0, cold wall x = 1, adiabatic top and bottom, Ra = 1e3, 1e4, 1e5 (1e6 optional). Mean Nusselt number
         of the cavity 1.118, 2.243, 4.519, 8.800 and of the hot wall (Nu_0) 1.117, 2.238, 4.509, 8.817 (de Vahl Davis 1983, Int. J. Numer. Meth. Fluids 3, 249-264,
         Table V, printed page 256, PDF page 8; read by the reviewer in the page image of the paper, which the first version of this study quoted from memory: every value
         agreed). The solver's wall Nusselt number is compared with Nu_0 (the hot-wall value of the benchmark) and, as the first version did, with the cavity mean Nu-bar; the
         benchmark's own estimated error is 0.1 / 0.2 / 0.3 / 1 % at Ra 1e3 / 1e4 / 1e5 / 1e6 (Table VII, p 261). Runs two or three grids per Ra to show the trend (uniform grids for Ra up to 1e4, mildly graded ones at 1e5: a strongly graded grid (ratio 1.12) loses the second order of the central differences and gave +0.7 % at Ra 1e3 and +18 % at 1e5).
         Output: out/cavity.json and a printed table.
Usage: .venv/bin/python research/convection-laws/scripts/study_cavity.py [--fine] (about 1 minute; --fine adds Ra 1e6)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import mac2d  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
REF_U = {1e3: 3.649, 1e4: 16.178, 1e5: 34.73, 1e6: 64.63}      # max u on the vertical midplane, de Vahl Davis (1983) Table V (read)
REF_V = {1e3: 3.697, 1e4: 19.617, 1e5: 68.59, 1e6: 219.36}     # max v (w in the paper) on the horizontal midplane, same table
REFERENCE = {1e3: 1.118, 1e4: 2.243, 1e5: 4.519, 1e6: 8.800}     # de Vahl Davis (1983) Table V, Nu-bar (mean over the cavity)
REFERENCE_WALL = {1e3: 1.117, 1e4: 2.238, 1e5: 4.509, 1e6: 8.817}    # same table, Nu_0 (mean Nu of the hot wall x = 0)


def cavity(ra, n, ratio=1.12):
    """!
    @brief Solve the square cavity.
    @param ra Rayleigh number.
    @param n Cells per side.
    @param ratio Geometric growth of the cells away from each wall (1.0 = uniform).
    @return dict with Nu (hot wall mean), Nu cold wall, midplane Nu range, umax, steps, converged and the solver object under key "box".
    """
    f = mac2d.graded([(0.5, n // 2, 1.0 / ratio), (0.5, n // 2, ratio)]) if ratio != 1.0 else np.linspace(0, 1, n + 1)
    f = f / f[-1]
    box = mac2d.Box(f, f, ra, west=("wall", 1.0), east=("wall", 0.0), south=("wall", None), north=("wall", None))
    t0 = time.time()
    steps = box.run(t_end=60.0, tol=1e-8)
    qw, qe = box.wall_gradient("W"), box.wall_gradient("E")
    nu_h = float((qw * box.dy).sum())
    nu_c = float(-(qe * box.dy).sum())
    mid = n // 2                                         # a face at 0.5 exists for even n and an even number of cells per half
    umid = float(np.abs(box.u[mid, :]).max())            # max |u| on the vertical midplane x = 0.5
    vmid = float(np.abs(box.v[:, mid]).max())            # max |v| on the horizontal midplane y = 0.5
    return {"umid_max": umid, "vmid_max": vmid, "ra": ra, "n": n, "nu_hot": nu_h, "nu_cold": nu_c, "umax": float(np.abs(box.u).max()), "vmax": float(np.abs(box.v).max()),
            "steps": steps, "converged": bool(box.converged), "t": box.t, "seconds": time.time() - t0, "nu_hot_local_max": float(qw.max()), "nu_hot_local_min": float(qw.min())}


def main():
    """!
    @brief Run the cases and print the comparison.
    @return None.
    """
    ras = [1e3, 1e4, 1e5] + ([1e6] if "--fine" in sys.argv else [])
    rows = []
    print("Ra      grid  Nu_hot   Nu_cold  Nu-bar  error%  Nu_0  error%  umid(ref) vmid(ref)   steps  conv  seconds")
    for ra in ras:
        for n, ratio in ((48, 1.0), (96, 1.0)) if ra < 1e5 else ((64, 1.0), (96, 1.0), (144, 1.0)):
            r = cavity(ra, n, ratio)
            r["ratio"] = ratio
            r["reference"] = REFERENCE[ra]
            r["error_pct"] = 100.0 * (r["nu_hot"] / REFERENCE[ra] - 1.0)
            r["reference_wall"] = REFERENCE_WALL[ra]
            r["error_wall_pct"] = 100.0 * (r["nu_hot"] / REFERENCE_WALL[ra] - 1.0)
            rows.append(r)
            print(f"{ra:7.0e} {n:4d} {ratio:4.2f}  {r['nu_hot']:.4f}  {r['nu_cold']:.4f}  {REFERENCE[ra]:.3f}   {r['error_pct']:+.2f}  {REFERENCE_WALL[ra]:.3f}  {r['error_wall_pct']:+.2f}   {r['umid_max']:6.2f}/{REF_U[ra]:.2f} {r['vmid_max']:6.2f}/{REF_V[ra]:.2f} {r['steps']:6d}  {r['converged']!s:5} {r['seconds']:.0f}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "cavity.json"), "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
