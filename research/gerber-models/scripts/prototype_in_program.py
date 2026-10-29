#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file prototype_in_program.py
@brief The mappings run through the program's own finite-volume network (pcbthermal.fvm.Network), without changing a line of it.
@details Shows that the integration of INTEGRATION.md needs no new algorithm: the program builds its network (cells, heater, losses, assembly, sparse solve) and only the
         conductance of the cells is replaced.
         1. The research solver (one sheet) against the program's FVM: they agreed to 3e-12 before the program gave a one-layer board laminate nodes (laminate.py); now they differ by that physics (printed).
         2. The geometric mean needs nothing but a different `S` array (stage 1): the program's assembly is used as it is.
         3. Directional conductances and flow-based faces (stage 2 and 3) replace the face conductances: a 20-line subclass overrides the assembly of the lateral couplings.
         Reference: the program's FVM on the 0.1 mm grid with S per pixel (the copper mask solved as it is). One copper layer, 36 x 36 mm windows (one per board), 6 x 6 mm heater.
         Needs the repository's own dependencies (numpy, scipy). Run: .venv/bin/python research/gerber-models/scripts/prototype_in_program.py (from the repository root) (about 30 s; `--all`: the 42 windows at 0.6, 1.0 and 2.0 mm, the table of 4.4 on the program as it is now, a few minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import sys
from pathlib import Path

import numpy as np

try:
    import pcbthermal                                                   # noqa: F401  (a copy of the program on PYTHONPATH is used as it is)
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))      # the repository root, to import pcbthermal

from pcbthermal import fvm                                              # noqa: E402
from pcbthermal.model import Problem                                    # noqa: E402

import conduction as cd                                                 # noqa: E402
import faces                                                            # noqa: E402
import windows                                                          # noqa: E402

WIN = windows.WIN
PIX = windows.PIX


class FaceNetwork(faces.FaceNetwork):
    """!@brief The program's network with the lateral face conductances of the copper layer given from outside (the laminate nodes of a one-layer board keep the program's couplings; see faces.FaceNetwork)."""

    def set_faces(self, gx, gy):
        """!
        @brief Replace the lateral couplings of the copper layer and assemble.
        @param gx Face conductances along x (ny, nx - 1), W/K.
        @param gy Face conductances along y (ny - 1, nx), W/K.
        @return None.
        """
        super().set_faces([(gx, gy)])


def make_problem(cell_mm):
    """!
    @brief A one-layer 36 x 36 mm board with the 6 x 6 mm heater (1 W) at 12..18 mm from the corner, 10 W/m2K on both faces, insulated edges.
    @param cell_mm Cell size (mm), used only for the name.
    @return Problem.
    """
    p = Problem.new(width_mm=WIN, height_mm=WIN, layers=1, thickness_mm=cd.T_LAM * 1000.0, copper_um=cd.T_CU * 1e6, h_top=cd.H_FACE, h_bottom=cd.H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=(12.0, 18.0, 18.0, 24.0))              # y up from the bottom edge: rows 12..18 mm from the top of the mask
    return p


def phases(problem):
    """!
    @brief The two phase conductances of the program's formula S = f k_cu t_cu + k_lam (slab - f t_cu) of the copper node (faces.phases: on a one-layer board the copper node holds the copper and half a laminate gap).
    @param problem Problem.
    @return Tuple (a, b): copper phase and laminate phase, W/K.
    """
    return faces.phases(problem, 0)


def solve_cells(problem, n, gx=None, gy=None, S=None):
    """!
    @brief Run the program's network on an n x n grid with given conductances.
    @param problem Problem.
    @param n Cells per side.
    @param gx Face conductances along x, or None to use S.
    @param gy Face conductances along y.
    @param S Cell sheet conductance array (ny, nx) for the program's own assembly (when gx is None).
    @return Temperature rise (ny, nx) of the layer.
    """
    if gx is not None:
        net = FaceNetwork(problem, n, n, assemble=False)
        net.set_faces(gx, gy)
    else:
        net = fvm.Network(problem, n, n, assemble=False)
        net.S[0] = S * net.cover
        net.K = net._assemble()
    return net.solve_steady()[0][0]


def main():
    """!
    @brief One window per board (or all 42 with `--all`, at 0.6, 1.0 and 2.0 mm cells): the program against the research solver, then the errors of the mappings through the program's network.
    @return None.
    """
    every = "--all" in sys.argv[1:]
    masks, meta = windows.load()
    seen, picks = set(), []
    for i, m in enumerate(meta):
        if every or m[0] not in seen:
            seen.add(m[0])
            picks.append(i)
    sizes = (0.6, 1.0, 2.0) if every else (0.6, 1.0)
    p = make_problem(PIX)
    a, b = phases(p)
    print(f"phase conductances of the program's formula: copper {a:.5f} W/K, laminate {b:.5f} W/K")
    n_fine = int(round(WIN / PIX))
    hs, he = int(12 / PIX), int(18 / PIX)                                # heater columns (x from 12 to 18 mm)
    ys, ye = int(round((WIN - 18) / PIX)), int(round((WIN - 12) / PIX))     # heater rows after the flip (y from 18 to 24 mm)
    print("window | program FVM vs research solver (same conductances) | error of the heater-block mean temperature against the fine program run: iso (today), geometric, lam 0.5, dual")
    rows = {c: [] for c in sizes}
    ar, br = cd.S_CU + cd.K_LAM * (cd.T_LAM - cd.T_CU), cd.S_LAM         # the research solver's own sheet (one node, the whole laminate in it)
    worst = 0.0
    for i in picks:
        mask = masks[i][::-1]                                           # row 0 = bottom (y up), as the program's grid
        S = np.where(mask, a, b)
        ref = solve_cells(p, n_fine, S=S)[ys:ye, hs:he].mean()          # the program's FVM at 0.1 mm
        Sr = np.where(mask, ar, br)
        mine = cd.solve_faces(cd.harm(Sr[:, :-1], Sr[:, 1:]), cd.harm(Sr[:-1, :], Sr[1:, :]), PIX, ys, ye, hs, he)[ys:ye, hs:he].mean()
        worst = max(worst, abs(mine / ref - 1))
        line = f"{meta[i][0]:8s} {abs(mine / ref - 1):.1e}    "
        for c in sizes:
            n = int(round(c / PIX))
            blk = cd.cell_blocks(S, n)
            f = (blk == a).mean(axis=(2, 3))
            k0, k1 = int(round(12 / c)), int(round(18 / c))
            r0, r1 = int(round((WIN - 18) / c)), int(round((WIN - 12) / c))
            cells = int(round(WIN / c))
            res = {}
            res["iso"] = solve_cells(p, cells, S=cd.map_power(f, 1.0, a, b))[r0:r1, k0:k1].mean()
            res["geo"] = solve_cells(p, cells, S=cd.map_power(f, 0.0, a, b))[r0:r1, k0:k1].mean()
            sx, sy = cd.map_lambda(blk, 0.5)
            res["lam"] = solve_cells(p, cells, *cd.faces_from_cells(sx, sy))[r0:r1, k0:k1].mean()
            if every:
                cx, cy = cd.map_cell_problem(blk)
                res["cellnum"] = solve_cells(p, cells, *cd.faces_from_cells(cx, cy))[r0:r1, k0:k1].mean()
            res["dual"] = solve_cells(p, cells, *cd.dual_faces(S, n, 0))[r0:r1, k0:k1].mean()
            errs = {k: 100 * (v / ref - 1) for k, v in res.items()}
            rows[c].append(errs)
            line += f"| {c} mm: " + "  ".join(f"{k} {e:+5.1f} %" for k, e in errs.items()) + "   "
        print(line, flush=True)
    # The research solver is one sheet with both films on it; the program gives a one-layer board two laminate nodes under the copper (laminate.py),
    # so since that correction the two differ by the physics of the laminate, not by the numerics (they agreed to 3e-12 before it)
    print(f"\nlargest difference between the program's FVM and the research solver (one sheet, no laminate nodes) on the same copper-node conductances: {worst:.1e} (relative)")
    for c, lst in rows.items():
        print(f"cells {c} mm, MAE (bias) over {len(lst)} windows: " + ", ".join(f"{k} {np.mean([abs(e[k]) for e in lst]):.1f} ({np.mean([e[k] for e in lst]):+.1f}) %" for k in lst[0]))


if __name__ == "__main__":
    main()
