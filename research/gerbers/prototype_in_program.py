"""!
@file prototype_in_program.py
@brief The mappings run through the program's own finite-volume network (pcbthermal.fvm.Network), without changing a line of it.
@details Shows that the integration of INTEGRATION.md needs no new algorithm: the program builds its network (cells, heater, losses, assembly, sparse solve) and only the
         conductance of the cells is replaced.
         1. The research solver and the program's FVM give the same temperature for the same conductances (the arithmetic mapping is the program's own formula).
         2. The geometric mean needs nothing but a different `S` array (stage 1): the program's assembly is used as it is.
         3. Directional conductances and flow-based faces (stage 2 and 3) replace the face conductances: a 20-line subclass overrides the assembly of the lateral couplings.
         Reference: the program's FVM on the 0.1 mm grid with S per pixel (the copper mask solved as it is). One copper layer, 36 x 36 mm windows (one per board), 6 x 6 mm heater.
         Needs the repository's own dependencies (numpy, scipy). Run: python prototype_in_program.py (about 3 minutes).
"""

import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # the repository root, to import pcbthermal

from pcbthermal import fvm                                              # noqa: E402
from pcbthermal.model import Problem                                    # noqa: E402

import conduction as cd                                                 # noqa: E402
import windows                                                          # noqa: E402

WIN = windows.WIN
PIX = windows.PIX


class FaceNetwork(fvm.Network):
    """!@brief The program's network with the lateral face conductances given from outside (one board layer)."""

    def set_faces(self, gx, gy):
        """!
        @brief Replace the lateral couplings and assemble.
        @param gx Face conductances along x (ny, nx - 1), W/K.
        @param gy Face conductances along y (ny - 1, nx), W/K.
        @return None.
        """
        self._gx, self._gy = gx, gy
        self.K = self._assemble()

    def _assemble(self):
        """!
        @brief Assemble K with the given faces instead of the harmonic mean of S (everything else of the program's assembly is kept: ambient losses on the diagonal).
        @return Sparse matrix.
        """
        ny, nx = self.ny, self.nx
        n = ny * nx
        idx = np.arange(n).reshape(ny, nx)
        a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
        b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
        g = np.concatenate([self._gx.ravel(), self._gy.ravel()])
        rows = [a, b, a, b, np.arange(n)]
        cols = [a, b, b, a, np.arange(n)]
        vals = [g, g, -g, -g, self.g_amb.ravel()]
        return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()


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
    @brief The two phase conductances of the program's formula S = f k_cu t_cu + k_lam (slab - f t_cu).
    @param problem Problem.
    @return Tuple (a, b): copper phase and laminate phase, W/K.
    """
    bd = problem.board
    k_lam = bd.layer_laminate()[0][0]
    slab = bd.slab_thicknesses()[0]
    tc = bd.copper_thickness[0]
    return bd.materials.k_copper * tc + k_lam * (slab - tc), k_lam * slab


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
    @brief One window per board: equality of the two solvers, then the errors of the mappings through the program's network.
    @return None.
    """
    masks, meta = windows.load()
    seen, picks = set(), []
    for i, m in enumerate(meta):
        if m[0] not in seen:
            seen.add(m[0])
            picks.append(i)
    p = make_problem(PIX)
    a, b = phases(p)
    print(f"phase conductances of the program's formula: copper {a:.5f} W/K, laminate {b:.5f} W/K")
    n_fine = int(round(WIN / PIX))
    hs, he = int(12 / PIX), int(18 / PIX)                                # heater columns (x from 12 to 18 mm)
    ys, ye = int(round((WIN - 18) / PIX)), int(round((WIN - 12) / PIX))     # heater rows after the flip (y from 18 to 24 mm)
    print("window | program FVM vs research solver (same conductances) | error of the heater-block mean temperature against the fine program run: iso (today), geometric, lam 0.5, dual")
    rows = {c: [] for c in (0.6, 1.0)}
    worst = 0.0
    for i in picks:
        mask = masks[i][::-1]                                           # row 0 = bottom (y up), as the program's grid
        S = np.where(mask, a, b)
        ref = solve_cells(p, n_fine, S=S)[ys:ye, hs:he].mean()          # the program's FVM at 0.1 mm
        mine = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), PIX, ys, ye, hs, he)[ys:ye, hs:he].mean()
        worst = max(worst, abs(mine / ref - 1))
        line = f"{meta[i][0]:8s} {abs(mine / ref - 1):.1e}    "
        for c in (0.6, 1.0):
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
            res["dual"] = solve_cells(p, cells, *cd.dual_faces(S, n, 0))[r0:r1, k0:k1].mean()
            errs = {k: 100 * (v / ref - 1) for k, v in res.items()}
            rows[c].append(errs)
            line += f"| {c} mm: " + "  ".join(f"{k} {e:+5.1f} %" for k, e in errs.items()) + "   "
        print(line, flush=True)
    print(f"\nlargest difference between the program's FVM and the research solver on the same conductances: {worst:.1e} (relative)")
    for c, lst in rows.items():
        print(f"cells {c} mm, MAE over {len(lst)} windows: " + ", ".join(f"{k} {np.mean([abs(e[k]) for e in lst]):.1f} %" for k in lst[0]))


if __name__ == "__main__":
    main()
