#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_film.py
@brief Item B of research/laminate-2-6: the FVM puts the edge film of a whole slab on the copper node, so with a large edge coefficient on a thick board it reads low against the independent
       3D solver. Which remedy removes it at the least cost: laminate nodes in the cells at the board edge (even where the copper is full), or an edge conductance with an efficiency of the laminate?
@details Boards: uniform full copper on every layer (35 um), a 10 mm part of 2 W (research/analytic-edge-spatial/lib/cases.py), faces 10 W/m2K, the edge coefficient 10, 50 and 200 W/m2K, thickness
         0.8, 1.6 and 3.2 mm, part in the corner / at the middle of an edge / at the centre. Reference: the independent 3D solver with the side film on every slab (layered3d_side.py), 1 mm cells,
         4 and 8 sub-slabs per gap (the difference is printed). Program: FVM at 0.5 mm with the rule as it is (default), with a fill of 0.9999 on every layer (nodes everywhere, the review's probe),
         with nodes in the cells at the edge only (`edge_margin` 0, 1, 2 cells; prototype lib/local_laminate.py) and with an efficiency factor eta on the laminate part of the edge conductance
         (eta = tanh(mL)/(mL), L = d/2, m = sqrt(h_side / (k_z delta)), delta = dx/2: it depends on the cell, which is the point of the comparison).
         Run (repository root, light): .venv/bin/python research/laminate-2-6/scripts/study_edge_film.py [--quick]
"""

import contextlib
import json
import math
import sys

import _boot26

import cases
import local_laminate as LL
import numpy as np
from pcbthermal import laminate

BOARDS = [(60, 40, 2, 1.6, 10.0, "corner"), (60, 40, 2, 3.2, 10.0, "corner"), (60, 40, 2, 1.6, 50.0, "corner"), (60, 40, 2, 1.6, 200.0, "corner"), (60, 40, 2, 1.6, 200.0, "centre"),
          (60, 40, 2, 3.2, 50.0, "corner"), (60, 40, 2, 3.2, 200.0, "corner"), (60, 40, 2, 3.2, 200.0, "edge"), (60, 40, 2, 3.2, 200.0, "centre"), (60, 40, 4, 1.6, 200.0, "corner"),
          (60, 40, 2, 0.8, 200.0, "corner"), (30, 20, 2, 0.8, 200.0, "corner"), (60, 40, 4, 3.2, 200.0, "corner")]


@contextlib.contextmanager
def eta_rule(problem, delta_factor=0.5):
    """!
    @brief Replace the edge conductance of the copper nodes by one with an efficiency eta on the laminate part (edge film of the slab in series with the vertical conduction).
    @param problem The Problem.
    @param delta_factor delta / dx of the fin model.
    @return Context manager.
    """
    orig = laminate.build

    def wrapped(board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans):
        """!
        @brief laminate.build followed by the efficiency on the edge conductance.
        @param board A Board.
        @param fill Copper fill.
        @param cell Cell area.
        @param cover Board share.
        @param active Cells on the board.
        @param edge Edge length per cell.
        @param S Lateral conductance.
        @param C Capacity.
        @param gz Vertical links.
        @param g_bottom Bottom conductance.
        @param g_side Edge conductance.
        @param plans Plans.
        @return LadderBuild.
        """
        res = orig(board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans)
        dx = math.sqrt(float(np.median(cell[cell > 0])))
        slab = np.asarray(board.slab_thicknesses(), dtype=float)
        t_cu = np.asarray(board.copper_thickness, dtype=float)
        kz = board.gap_properties()[0]
        hs = float(board.h_side or 0.0)
        L = board.layers
        for l in range(L):
            lam = slab[l] - t_cu[l]                                   # laminate held by the node
            gaps = [g for g in (l - 1, l) if 0 <= g < L - 1]
            kz_l = float(np.mean([kz[g] for g in gaps])) if gaps else float(board.materials.k_fr4_through)
            half = lam / max(len(gaps), 1) if gaps else lam           # one half-gap on each side
            m = math.sqrt(hs / (kz_l * dx * delta_factor))
            ml = m * half
            eta = math.tanh(ml) / ml if ml > 1e-12 else 1.0
            res.g_side[l] = res.g_side[l] * (t_cu[l] + eta * lam) / slab[l]
        return res

    laminate.build = wrapped
    try:
        yield
    finally:
        laminate.build = orig


def main_fine(argv=None):
    """!
    @brief The same comparison with a finer laminate rule (0.2 mm, 8 sub-gaps) and the unknowns of each variant: is the remaining error the edge or the sub-gap?
    @param argv Command line (unused).
    @return None
    """
    from pcbthermal import SolverOptions, fvm, simulate
    print("fine rule (0.2, 8): board | 3D(8) | default | fill.9999 | edge m0 | edge m1 | edge m2 (errors %), unknowns default / m1 / fill.9999")
    for w, h, layers, t, hs, pos in [b for b in BOARDS if b[3] >= 1.6 and b[4] >= 50.0]:
        p, xy = cases.board(w, h, layers, t, hs, pos)
        r8 = cases.ref3d(p, xy, 1.0, sub=8)
        opt = SolverOptions(cell_mm=0.5, models=("fvm",), laminate_s_max_mm=0.2, laminate_n_max=8)
        rise = lambda: simulate(p, opt).results["fvm"].t_max - cases.T0
        with laminate.using(0.2e-3, 8):
            u0 = fvm.unknowns(p, 0.5)[0]
        res = {"default": rise()}
        for z in p.zones:
            z.fill = 0.9999
        with laminate.using(0.2e-3, 8):
            u9 = fvm.unknowns(p, 0.5)[0]
        res["fill"] = rise()
        for z in p.zones:
            z.fill = 1.0
        for m in (0, 1, 2):
            with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=m):
                if m == 1:
                    with laminate.using(0.2e-3, 8):
                        u1 = fvm.unknowns(p, 0.5)[0]
                res[f"m{m}"] = rise()
        e = lambda k: 100.0 * (res[k] / r8 - 1.0)
        print(f"{w}x{h} L{layers} t{t} hs{hs:4.0f} {pos:6s} | {r8:6.2f} | {e('default'):+6.1f} | {e('fill'):+6.1f} | {e('m0'):+6.1f} | {e('m1'):+6.1f} | {e('m2'):+6.1f} | {u0} / {u1} / {u9}", flush=True)


def main(argv=None):
    """!
    @brief Run the comparison and print the table.
    @param argv Command line (--quick: five boards).
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    if "--fine" in argv:
        return main_fine(argv)
    boards = BOARDS[:5] if "--quick" in argv else BOARDS
    rows = []
    print("board                              | 3D(4) 3D(8) | default | fill.9999 | edge m0 | edge m1 | edge m2 | eta   (errors vs 3D(8), %)")
    for w, h, layers, t, hs, pos in boards:
        p, xy = cases.board(w, h, layers, t, hs, pos)
        r4 = cases.ref3d(p, xy, 1.0, sub=4)
        r8 = cases.ref3d(p, xy, 1.0, sub=8)
        out = {"default": cases.rise(p, "fvm", 0.5)}
        for z in p.zones:
            z.fill = 0.9999
        out["fill0.9999"] = cases.rise(p, "fvm", 0.5)
        for z in p.zones:
            z.fill = 1.0
        for m in (0, 1, 2):
            with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=m):
                out[f"edge m{m}"] = cases.rise(p, "fvm", 0.5)
        with eta_rule(p):
            out["eta"] = cases.rise(p, "fvm", 0.5)
        rows.append(dict(w=w, h=h, layers=layers, t=t, hs=hs, pos=pos, r3d4=r4, r3d8=r8, **out))
        e = lambda k: 100.0 * (out[k] / r8 - 1.0)
        print(f"{w}x{h} L{layers} t{t} hs{hs:4.0f} {pos:6s} | {r4:6.2f} {r8:6.2f} | {e('default'):+6.1f} | {e('fill0.9999'):+6.1f} | {e('edge m0'):+6.1f} | {e('edge m1'):+6.1f} | "
              f"{e('edge m2'):+6.1f} | {e('eta'):+6.1f}", flush=True)
    (_boot26.OUT / "study_edge_film.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
