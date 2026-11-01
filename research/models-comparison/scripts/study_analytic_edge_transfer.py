#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_analytic_edge_transfer.py
@brief How good is the Analytic model with the edge loss moved to the faces (Muzychka, Culham and Yovanovich 2003, eq. 29), and is its warning true?

@details Uniform boards (full copper on every layer, 2 W on a 10 mm square at the centre or in a corner; faces 10 W/m2K), 30 x 20, 60 x 40 and 100 x 80 mm,
         2 layers of 0.8, 1.6 and 3.2 mm and 4 and 6 layers of 1.6 mm, edge coefficient 10, 50 and 200 W/m2K: 90 boards. For each: the Analytic as it was
         (edge left out, the same board with h_side None), the Analytic now, the FVM at 1 and 0.5 mm, the share of the power that the transfer puts in the wrong
         place (the quantity of the warning) and, with --3d, an independent 3D finite-volume solver with convective side faces (written here, imports nothing
         from pcbthermal: every copper layer and every dielectric sub-slab a slab, FR-4 0.9 / 0.3 W/mK in plane / through, film on the whole top face as in the
         program) on the boards up to 60 x 40 mm (about 1.5 GB at most). The last lines summarise the errors and the warning rule.

         With --time: the time to 63 % of the unit-step response of the part (2 mm cell, as the frozen numbers) of the Analytic before and now and of the FVM,
         on two uniform boards and the example board.

         Run from the repository root: .venv/bin/python research/models-comparison/scripts/study_analytic_edge_transfer.py [--3d] [--time]  (about 5 minutes)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import numpy as np                                        # noqa: E402
import scipy.sparse as sp                                 # noqa: E402
import scipy.sparse.linalg as spla                        # noqa: E402

from pcbthermal import Problem, SolverOptions, analytic, simulate   # noqa: E402

T0 = 25.0


def solve_3d(dx, nx, ny, slabs, source, power, h_face, h_side):
    """!
    @brief Independent steady 3D finite volumes of a laminated plate with films on both faces and on the four sides.
    @param dx Cell size in the plane in m (square cells).
    @param nx Cells along x.
    @param ny Cells along y.
    @param slabs List of (thickness m, k in plane W/mK, k through W/mK, sub-slabs) from the top down.
    @param source (x0, y0, x1, y1) of the heated rectangle of the top face in m, on cell edges.
    @param power Power in W, spread uniformly over the source cells.
    @param h_face Film coefficient of both faces in W/m2K (on the whole top face, also under the source).
    @param h_side Film coefficient of the side faces in W/m2K.
    @return Tuple (top-slab field in K, heat out by faces and sides in W).
    """
    dz, kin, kth = [], [], []
    for t, ki, kt, n in slabs:
        dz += [t / n] * n
        kin += [ki] * n
        kth += [kt] * n
    dz, kin, kth = np.array(dz), np.array(kin), np.array(kth)
    nz = len(dz)
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the conductance g between the node arrays a and b (symmetric).
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/K (scalar or array).
        @return None.
        """
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()])
        cols.extend([b.ravel(), a.ravel()])
        vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel())
        np.add.at(diag, b.ravel(), g.ravel())

    area = dx * dx
    for k in range(nz):                                   # in-plane links: k dz dy / dx with dy = dx
        link(idx[k, :, :-1], idx[k, :, 1:], kin[k] * dz[k])
        link(idx[k, :-1, :], idx[k, 1:, :], kin[k] * dz[k])
    for k in range(nz - 1):                               # vertical links: two half cells in series
        link(idx[k], idx[k + 1], 1.0 / (dz[k] / (2 * kth[k] * area) + dz[k + 1] / (2 * kth[k + 1] * area)))
    g_top = 1.0 / (dz[0] / (2 * kth[0] * area) + 1.0 / (h_face * area))     # film behind half a cell
    g_bot = 1.0 / (dz[-1] / (2 * kth[-1] * area) + 1.0 / (h_face * area))
    diag[idx[0].ravel()] += g_top
    diag[idx[-1].ravel()] += g_bot
    g_side = np.zeros((nz, ny, nx))
    for k in range(nz):                                   # side film behind half a cell of the slab, on the outer cells of every slab
        g = 1.0 / (dx / (2 * kin[k] * dz[k] * dx) + 1.0 / (h_side * dz[k] * dx)) if h_side > 0 else 0.0
        g_side[k, :, 0] += g
        g_side[k, :, -1] += g
        g_side[k, 0, :] += g
        g_side[k, -1, :] += g
    diag += g_side.ravel()
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    m = (xs[None, :] > source[0]) & (xs[None, :] < source[2]) & (ys[:, None] > source[1]) & (ys[:, None] < source[3])
    q = np.zeros(n)
    q[idx[0][m]] = power / m.sum()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    out = g_top * T[0].sum() + g_bot * T[-1].sum() + float((g_side * T).sum())
    return T[0], out


def board(w, h, layers, t, h_side, pos):
    """!
    @brief A uniform board of the study.
    @param w Width in mm.
    @param h Height in mm.
    @param layers Copper layers (35 um each, full copper).
    @param t Thickness in mm.
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @param pos "centre" or "corner" for the 10 mm source of 2 W.
    @return Tuple (Problem, corner (x0, y0) of the source in mm).
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=t, copper_um=35.0, ambient=T0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, w, h))
    x0, y0 = ((w - 10.0) / 2, (h - 10.0) / 2) if pos == "centre" else (0.0, 0.0)
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + 10.0, y0 + 10.0))
    return p, (x0, y0)


def rise(p, model, cell):
    """!
    @brief Hottest rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float Rise in K.
    """
    return simulate(p, SolverOptions(cell_mm=cell, models=(model,))).results[model].t_max - T0


def misplaced_share(p):
    """!
    @brief Share of the power that the transfer puts in the wrong place (the quantity of the warning of analytic.solve_steady).
    @param p Problem.
    @return float Signed share (positive: the edge is warmer than the mean).
    """
    sh = analytic._effective_sheet(p, 1.0)
    th = analytic.solve_steady(p, cell_mm=1.0).T - T0
    rim = [np.concatenate([x[0], x[-1], x[1:-1, 0], x[1:-1, -1]]).mean() - x.mean() for x in th]
    return float(sum(sh["h_edge"][k] * sh["W"] * sh["H"] * rim[k] for k in range(len(rim)))) / p.total_power()


def time_to_63(p, model):
    """!
    @brief Time to 63.2 % of the steady resistance in the unit-step response of the first part.
    @param p Problem.
    @param model Model key.
    @return float Time in s (log-linear interpolation between the samples).
    """
    import math
    from pcbthermal.api import step_response
    sr = step_response(p, model, SolverOptions(models=(model,), cell_mm=2.0))
    t, z = np.asarray(sr.times, dtype=float), np.asarray(sr.z[0], dtype=float)
    target = (1.0 - math.exp(-1.0)) * float(sr.rth[0])
    k = int(np.argmax(z >= target))
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    return math.exp(math.log(t[k - 1]) + f * (math.log(t[k]) - math.log(t[k - 1])))


def time_cases():
    """!
    @brief Print the times to 63 % of the Analytic before (edge left out) and now, and of the FVM.
    @return None.
    """
    import copy
    from pcbthermal.examples import example_board
    cases = [("60 x 40 mm, h_side 50", board(60, 40, 2, 1.6, 50.0, "centre")[0]), ("30 x 20 mm, h_side 50", board(30, 20, 2, 1.6, 50.0, "centre")[0]),
             ("example board", example_board())]
    for name, p in cases:
        q = copy.deepcopy(p)
        q.board.h_side = None
        print(f"time to 63 %, {name}: Analytic before {time_to_63(q, 'analytic'):.1f} s, now {time_to_63(p, 'analytic'):.1f} s, FVM {time_to_63(p, 'fvm'):.1f} s", flush=True)


def main(argv=None):
    """!
    @brief Run the 90 boards and print one line each and the summary.
    @param argv Arguments (default sys.argv[1:]).
    @return int 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--3d", dest="ref3d", action="store_true", help="add the independent 3D solver (boards up to 60 x 40 mm)")
    ap.add_argument("--time", action="store_true", help="only the times to 63 %% of the step response")
    a = ap.parse_args(argv)
    if a.time:
        time_cases()
        return 0
    rows = []
    for w, h in ((30, 20), (60, 40), (100, 80)):
        for layers, t in ((2, 0.8), (2, 1.6), (2, 3.2), (4, 1.6), (6, 1.6)):
            for hs in (10.0, 50.0, 200.0):
                for pos in ("centre", "corner"):
                    p, (x0, y0) = board(w, h, layers, t, hs, pos)
                    before = rise(board(w, h, layers, t, None, pos)[0], "analytic", 1.0)
                    after = rise(p, "analytic", 1.0)
                    f1, f05 = rise(p, "fvm", 1.0), rise(p, "fvm", 0.5)
                    mis = misplaced_share(p)
                    r3 = float("nan")
                    if a.ref3d and w <= 60:
                        gaps = p.board.gap_thicknesses()
                        slabs = []
                        for k in range(layers):
                            slabs.append((35e-6, 385.0, 385.0, 1))
                            if k < layers - 1:
                                slabs.append((float(gaps[k]), 0.9, 0.3, 4))
                        top, _ = solve_3d(1e-3, w, h, slabs, (x0 * 1e-3, y0 * 1e-3, (x0 + 10) * 1e-3, (y0 + 10) * 1e-3), 2.0, 10.0, hs)
                        r3 = float(top.max())
                    ratio = float(analytic._effective_sheet(p, 1.0)["h_edge"].sum()) / 20.0
                    rows.append((before / f05 - 1, after / f05 - 1, mis, ratio, f05 / r3 - 1, after / r3 - 1))
                    print(f"{w}x{h} L{layers} t{t} hs{hs:4.0f} {pos:6s} edge/face {ratio:4.2f} | Analytic before {100 * (before / f05 - 1):+6.1f} % "
                          f"now {100 * (after / f05 - 1):+6.1f} % of the FVM 0.5 mm (FVM 1 mm {100 * (f1 / f05 - 1):+5.2f} %) | misplaced {100 * mis:+5.2f} % "
                          f"| FVM/3D {100 * (f05 / r3 - 1):+6.1f} %  Analytic/3D {100 * (after / r3 - 1):+6.1f} %", flush=True)
    r = np.array(rows)
    print(f"\nboards {len(r)}; |error| before: mean {100 * np.abs(r[:, 0]).mean():.1f} %, max {100 * np.abs(r[:, 0]).max():.1f} %; "
          f"now: mean {100 * np.abs(r[:, 1]).mean():.1f} %, max {100 * np.abs(r[:, 1]).max():.1f} %; better now on {(np.abs(r[:, 1]) < np.abs(r[:, 0])).sum()}")
    for thr in (0.005, 0.01):
        warned = np.abs(r[:, 2]) > thr
        print(f"warning rule, misplaced share above {100 * thr:.1f} % (the program uses 1 %): {warned.sum()} warned, sense right on "
              f"{(np.sign(r[warned, 1]) == np.sign(r[warned, 2])).sum()}, largest silent error {100 * np.abs(r[~warned, 1]).max():.1f} %, "
              f"error / share {(r[warned, 1] / r[warned, 2]).min():.2f} to {(r[warned, 1] / r[warned, 2]).max():.2f}")
    old = r[:, 3] > 0.3
    print(f"for comparison, the ratio rule (edge/face above 0.3): {old.sum()} warned, largest silent error {100 * np.abs(r[~old, 1]).max():.1f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
