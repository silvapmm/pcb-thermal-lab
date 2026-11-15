#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_thick_cases.py
@brief Surface against column mean for thick metal: plates (copper core, aluminium, spreader, case 2), a copper-core board in the program, and MCPCB-like stacks, against the independent 3D solver.
@details Answers: where the surface under a source and the through-thickness mean of the layer differ, by how much, and how the program's node (the mean) and the parabolic read-out compare.
         Part 1: one-layer plates (program FVM at 1 mm against tests/helpers/layered3d.py with 8 sub-slabs, plate 50 x 50 mm, source on cell lines, adiabatic top). Part 2: a copper-core board
         (35 um Cu / 0.1 mm dielectric k 2 / 1.5 mm Cu) as a two-layer Problem of the program against the 3D solver. Part 3: MCPCB-like stacks (35 um Cu / dielectric / 1.5 mm Al k 150, film
         2000 W/m2K under the base) and a 1.6 mm two-layer FR-4 board in the 3D solver only: the surface of the top copper, the layer means, the Al faces and the mean of the whole stack.
         Usage: .venv/bin/python research/readout-conventions/scripts/study_thick_cases.py   (about 2 min, under 1.5 GB)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
THIN = os.path.join(ROOT, "research", "through-thickness-readout", "lib")
for p in (ROOT, THIN, os.path.join(ROOT, "tests", "helpers")):
    sys.path.insert(0, p)
import layered3d as L                                          # noqa: E402
import sublayers                                               # noqa: E402
import surface_readout as sr                                   # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate        # noqa: E402
from pcbthermal.model import Dielectric, Materials             # noqa: E402

W = 50e-3
DX = 1e-3
N = 50
C = W / 2


def centre(T):
    """!
    @brief Mean of the four cells around the plate centre.
    @param T Array (ny, nx).
    @return float.
    """
    j = T.shape[0] // 2
    return float(T[j - 1:j + 1, j - 1:j + 1].mean())


def src_rect(a):
    """!
    @brief Source rectangle centred on a cell corner.
    @param a Side in m.
    @return Tuple (x0, y0, x1, y1) in m.
    """
    return (C - a / 2, C - a / 2, C + a / 2, C + a / 2)


def run3d(slabs, a, P, h_top, h_bot, dx=DX):
    """!
    @brief Independent 3D solution reduced to per-slab-group values at the centre.
    @param slabs List (t, k, n_sub) from the top.
    @param a Source side in m.
    @param P Power in W.
    @param h_top Top film outside the source.
    @param h_bot Bottom film.
    @param dx Plan cell in m (the plate is 50 mm).
    @return dict with 'surface' (top face under the source centre), 'means' (thickness mean of each group), 'bottom' (centre of the last slab), 'whole' (mean of the whole stack), 'rise'.
    """
    n = int(round(W / dx))
    r = L.solve(dx, n, n, slabs, src_rect(a), P, h_top, h_bot)
    dz = np.array(r["dz"])
    T = np.array(r["T"])
    out, i = [], 0
    for _, _, n in slabs:
        w = dz[i:i + n] / dz[i:i + n].sum()
        out.append(centre(np.tensordot(w, T[i:i + n], axes=(0, 0))))
        i += n
    return {"surface": centre(r["surface_top"]), "means": out, "bottom": centre(T[-1]), "whole": centre(np.tensordot(dz / dz.sum(), T, axes=(0, 0))), "T": T, "dz": dz}


def plates():
    """!
    @brief Part 1: one-layer plates, the program node and the parabola against the 3D surface and mean.
    @return list of rows.
    """
    cases = [("2 mm copper, h 1000, 4 mm source", 2e-3, 385.0, 1000.0, 4e-3, 10.0),
             ("1.5 mm aluminium, h 2000, 4 mm source", 1.5e-3, 150.0, 2000.0, 4e-3, 10.0),
             ("3 mm copper, h 20 (air), 20 mm source", 3e-3, 385.0, 20.0, 20e-3, 2.0),
             ("10 mm Al, h 5000, 10 mm source", 10e-3, 200.0, 5000.0, 10e-3, 50.0),
             ("Muzychka case 2 plate (10 mm, k 150, h 400), 10 mm source", 10e-3, 150.0, 400.0, 10e-3, 25.0),
             ("10 mm k 50, h 400, 4 mm source", 10e-3, 50.0, 400.0, 4e-3, 10.0)]
    print("Part 1: one-layer plates, 50 x 50 mm, top adiabatic. All temperatures are rises above the ambient (K).")
    print(f"{'case':60s} {'3D surf':>8s} {'3D mean':>8s} {'node':>8s} {'node+par':>8s} {'surf-mean':>9s} {'% rise':>7s} {'bound':>7s} {'par err':>8s}")
    rows = []
    for name, t, k, h, a, P in cases:
        r = run3d([(t, k, 8)], a, P, 0.0, h)
        s3, m3 = r["surface"], r["means"][0]
        pr = sublayers.stack_problem(1, 50.0, 50.0, t * 1e3, k, h, sources=[((C * 1e3 - a * 5e2, C * 1e3 - a * 5e2, C * 1e3 + a * 5e2, C * 1e3 + a * 5e2), P)])
        res = simulate(pr, SolverOptions(models=("fvm",), cell_mm=1.0))
        node = centre(np.asarray(res.results["fvm"].T[0])) - pr.board.ambient
        q = P / a**2
        qb = float(sr.bottom_flux(node, h, t, k))
        d_top, _ = sr.offsets(t, k, q, qb)
        bound = q * t / (2 * k)
        rows.append((name, s3, m3, node, node + float(d_top), s3 - m3, 100 * (s3 - m3) / s3, bound, float(d_top) - (s3 - m3)))
        print(f"{name:60s} {s3:8.3f} {m3:8.3f} {node:8.3f} {node + float(d_top):8.3f} {s3 - m3:9.3f} {100 * (s3 - m3) / s3:7.2f} {bound:7.3f} {float(d_top) - (s3 - m3):+8.3f}")
    return rows


def copper_core():
    """!
    @brief Part 2: a copper-core board in the program (two layers, 35 um top, 1.5 mm base, dielectric 0.1 mm k 2) against the 3D solver.
    @return None.
    """
    a, P, h = 5e-3, 5.0, 2000.0
    print("\nPart 2: copper-core board, 35 um Cu / 0.1 mm dielectric (k 2) / 1.5 mm Cu, 5 W on 5 x 5 mm, film 2000 W/m2K under the base, top film 10 (K above the ambient)")
    r = run3d([(35e-6, 385.0, 2), (100e-6, 2.0, 2), (1.5e-3, 385.0, 8)], a, P, 10.0, h, 0.5e-3)
    pr = Problem.new(50.0, 50.0, layers=2, thickness_mm=1.0 + 0.1 + 0.035, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=h, h_side=None, materials=Materials(k_copper=385.0))
    pr.board.copper_thickness = [35e-6, 1.5e-3]
    pr.board.dielectrics = [Dielectric(thickness=100e-6, name="dielectric", k_through=2.0, k_inplane=2.0, rho=2000.0, cp=900.0)]
    pr.add_full_copper(layers=None)
    c = C * 1e3
    pr.add_heater(1, P, rect=(c - 2.5, c - 2.5, c + 2.5, c + 2.5), name="S")
    for cell in (1.0, 0.5, 0.25):
        res = simulate(pr, SolverOptions(models=("fvm",), cell_mm=cell))
        T = np.asarray(res.results["fvm"].T) - pr.board.ambient
        print(f"  program FVM {cell} mm: top node {centre(T[0]):.3f}  base node {centre(T[1]):.3f}")
    print(f"  3D: top surface {r['surface']:.3f}, top copper mean {r['means'][0]:.3f}, dielectric mean {r['means'][1]:.3f}, base mean {r['means'][2]:.3f}, base bottom {r['bottom']:.3f}, whole-stack mean {r['whole']:.3f}")
    print(f"  top copper: surface - mean {1e3 * (r['surface'] - r['means'][0]):.3f} mK ({100 * (r['surface'] - r['means'][0]) / r['surface']:.4f} % of the surface rise); base: top face - mean "
          f"{centre(r['T'][4]) - r['means'][2]:.3f} K (centre of the first base sub-slab, 0.09 mm below the face)")
    print(f"  surface minus whole-stack mean {r['surface'] - r['whole']:.3f} K ({100 * (r['surface'] - r['whole']) / r['surface']:.1f} % of the surface rise)")


def stacks():
    """!
    @brief Part 3: MCPCB-like stacks and an FR-4 board in the 3D solver; which temperature each convention reads.
    @return None.
    """
    a, P = 5e-3, 5.0
    print("\nPart 3: stacks in the independent 3D solver, 5 W on 5 x 5 mm, 50 x 50 mm, top film 10 W/m2K, film under the base 2000 W/m2K (K above the ambient)")
    print(f"{'stack':64s} {'surface':>8s} {'Cu mean':>8s} {'diel top':>8s} {'base mean':>9s} {'base bot':>8s} {'whole':>8s} {'surf-Cu mean mK':>15s}")
    stk = [("Al MCPCB 35 um Cu / 100 um k2 / 1.5 mm Al k150", [(35e-6, 385.0, 2), (100e-6, 2.0, 2), (1.5e-3, 150.0, 8)], 2000.0),
           ("Al MCPCB 35 um Cu / 75 um k1 / 1.5 mm Al k150", [(35e-6, 385.0, 2), (75e-6, 1.0, 2), (1.5e-3, 150.0, 8)], 2000.0),
           ("Al MCPCB 70 um Cu / 100 um k2 / 3 mm Al k150", [(70e-6, 385.0, 2), (100e-6, 2.0, 2), (3e-3, 150.0, 8)], 2000.0),
           ("2-layer FR-4 1.6 mm: 35 um Cu / 1.53 mm k0.3 / 35 um Cu (h 10 both)", [(35e-6, 385.0, 2), (1.53e-3, 0.3, 8), (35e-6, 385.0, 2)], 10.0)]
    for name, slabs, hb in stk:
        r = run3d(slabs, a, P, 10.0, hb, 0.5e-3)
        diel_top = centre(r["T"][2])                             # first dielectric slab centre (about t/4 below the copper)
        print(f"{name:64s} {r['surface']:8.2f} {r['means'][0]:8.2f} {diel_top:8.2f} {r['means'][2] if len(slabs) == 3 and slabs[2][1] < 200 else r['means'][2]:9.2f} "
              f"{r['bottom']:8.2f} {r['whole']:8.2f} {1e3 * (r['surface'] - r['means'][0]):15.3f}")


def main():
    """!
    @brief Run the three parts.
    @return None.
    """
    plates()
    copper_core()
    stacks()


if __name__ == "__main__":
    main()
