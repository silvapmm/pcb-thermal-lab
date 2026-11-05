#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief Independent checks of the review: is the Robin series right, and how far does one common edge parameter go on boards that are not stacks of identical layers?

@details Four parts (--part 1 to 4; default all), written by the reviewer:

         1. Basis. Orthogonality and norms by quadrature, the wavenumbers against the eigenvalues of a fine 1D finite-difference Laplacian with a Robin end, and the
            roots for a vanishing and a huge edge parameter.
         2. The same layered sheets solved independently. The sheet conductances, gap conductances and slabs of analytic._effective_sheet are put into a 2D
            finite-difference solver written here (five-point stencil per layer, vertical links, the true per-layer Robin edge h_side s_l behind half a cell), at
            0.5 and 0.25 mm with Richardson extrapolation, against the Robin series of lib/analytic_edge.py (which uses one common beta). On uniform boards both
            must agree; this tests the projections, the norms, the evaluation and the coupling of the layers without the FVM.
         3. Boards outside the study of the folder: the typical advanced stack-ups of the program (4, 6 and 8 layers, full copper, which have very different
            slab / S ratios even with full copper), two-layer boards with partial copper on one side, and one-layer boards. Hottest rise of faces, robin, robin_res and
            a temperature-weighted common beta (three passes) against the FVM at 0.5 mm, with the spread of slab / S, the ratio of the sheet conductances and the
            edge share sum(h_edge) / h_tot. One line per board is also written to out/review_checks.txt for figure 7.
         4. Where the rest of the error sits: (a) the FVM on full copper with and without its laminate nodes (a fill of 0.9999 switches them on) against the
            independent 3D solver with the side film; (b) the worst boards of part 3 against the FVM with one laminate node per gap.

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_review_checks.py [--part 1|2|3|4]  (about 8 minutes)
"""

import argparse
import os
import sys
import warnings

import numpy as np
import scipy.linalg as sl
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))

import analytic_edge as ae               # noqa: E402
import cases                             # noqa: E402
from robin_basis import Basis            # noqa: E402
from pcbthermal import Problem, analytic  # noqa: E402

OUT = os.path.join(ROOT, "out")


def part_1():
    """!
    @brief Basis checks: quadrature, finite-difference eigenvalues, extreme edge parameters.
    @return None.
    """
    print("1. basis")
    L = 0.06
    for beta in (1e-3, 1.0, 50.0, 1e3, 1e5):
        b = Basis(L, beta, 40)
        x = np.linspace(0, L, 200001)
        P = b.evaluate(x)
        G = np.trapezoid(P[:, :, None] * P[:, None, :], x, axis=0)
        off = np.abs(G - np.diag(np.diag(G))).max() / np.diag(G).min()
        print(f"  beta {beta:8g} 1/m: off-diagonal / diagonal {off:.1e}, norm error {np.abs(np.diag(G) / b.norm - 1).max():.1e}")
    for beta in (1e-2, 1.0, 500.0, 1e6):
        n = 4000
        dx = L / n
        main = np.full(n, 2.0)
        main[0] = main[-1] = 1.0 + dx / (dx / 2 + 1.0 / beta)         # half a cell in series with the edge parameter
        ev = sl.eigh_tridiagonal(main, -np.ones(n - 1), select="i", select_range=(0, 49), eigvals_only=True) / dx ** 2
        b = Basis(L, beta, 50)
        print(f"  beta {beta:8g} 1/m: first 50 wavenumbers against the 1D finite differences, max relative difference {np.abs(np.sqrt(ev) / b.lam - 1).max():.1e}")
    for beta in (1e-30, 1e-12, 1e-8, 1e12, 1e14):
        b = Basis(L, beta, 600)
        print(f"  beta {beta:8g} 1/m: 600 roots, ordered {bool(np.all(np.diff(b.lam) > 0))}, lam_1 L / pi = {b.lam[1] * L / np.pi:.9f}")
    print()


def sheet_fd(sh, b, heater, power, dx):
    """!
    @brief Independent 2D finite differences of the layered sheets of analytic._effective_sheet with a per-layer Robin edge.
    @param sh Dict of analytic._effective_sheet.
    @param b The Board (h_top, h_bottom, h_side).
    @param heater (x1, x2, y1, y2) of the heated rectangle on layer 1 in m.
    @param power Power in W.
    @param dx Cell in m.
    @return float Hottest rise in K.
    """
    W, H, L, S, slab, g = sh["W"], sh["H"], sh["L"], sh["S"], sh["slab"], sh["g_diel"]
    nx, ny = int(round(W / dx)), int(round(H / dx))
    n = nx * ny * L
    idx = np.arange(n).reshape(L, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, c, gg):
        """!
        @brief Symmetric conductance gg between node arrays a and c.
        @param a Nodes.
        @param c Nodes.
        @param gg Conductance in W/K.
        @return None.
        """
        gg = np.broadcast_to(gg, a.shape)
        rows.extend([a.ravel(), c.ravel()])
        cols.extend([c.ravel(), a.ravel()])
        vals.extend([-gg.ravel()] * 2)
        np.add.at(diag, a.ravel(), gg.ravel())
        np.add.at(diag, c.ravel(), gg.ravel())

    for l in range(L):
        link(idx[l, :, :-1], idx[l, :, 1:], S[l])                     # S dx dy / dx with dy = dx
        link(idx[l, :-1, :], idx[l, 1:, :], S[l])
        diag[idx[l].ravel()] += ((b.h_top if l == 0 else 0.0) + (b.h_bottom if l == L - 1 else 0.0)) * dx * dx
        ge = 1.0 / (dx / (2 * S[l] * dx) + 1.0 / (b.h_side * slab[l] * dx))     # the edge of layer l: h_side s_l per metre, behind half a cell
        for edge in (idx[l, :, 0], idx[l, :, -1], idx[l, 0, :], idx[l, -1, :]):
            np.add.at(diag, edge, ge)
    for l in range(L - 1):
        link(idx[l], idx[l + 1], g[l] * dx * dx)
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    x1, x2, y1, y2 = heater
    fx = np.clip(np.minimum(xs + dx / 2, x2) - np.maximum(xs - dx / 2, x1), 0, None) / dx
    fy = np.clip(np.minimum(ys + dx / 2, y2) - np.maximum(ys - dx / 2, y1), 0, None) / dx
    q = np.zeros(n)
    q[idx[0].ravel()] = (power / ((x2 - x1) * (y2 - y1)) * np.outer(fy, fx) * dx * dx).ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    return float(spla.spsolve(K.tocsc(), q).max())


def part_2():
    """!
    @brief The Robin series against an independent finite-difference solution of the same sheets.
    @return None.
    """
    print("2. Robin series against independent 2D finite differences of the same layered sheets (Richardson from 0.5 and 0.25 mm)")
    for w, h, layers, t, hs, pos in ((60, 40, 2, 1.6, 200, "corner"), (60, 40, 2, 1.6, 200, "edge"), (30, 20, 4, 1.6, 50, "centre"),
                                     (60, 40, 6, 1.6, 200, "corner"), (100, 80, 2, 3.2, 200, "corner")):
        p, _ = cases.board(w, h, layers, t, hs, pos)
        r = ae.solve(p, 1.0, edge="robin")
        sh = r["sh"]
        rect = analytic._equivalent_rectangle(p.heaters[0].polygon, sh["W"], sh["H"])
        a, b2 = (sheet_fd(sh, p.board, rect, p.total_power(), d) for d in (0.5e-3, 0.25e-3))
        ext = b2 + (b2 - a) / 3.0
        print(f"  {w}x{h} L{layers} t{t} h_side {hs:3d} {pos:6s}: Robin {r['t_max'] - cases.T0:8.4f} K, FD {a:8.4f} / {b2:8.4f} / extrapolated {ext:8.4f} K, "
              f"difference {100 * ((r['t_max'] - cases.T0) / ext - 1):+.3f} %, balance {(r['p_faces'] + r['p_edge']) / r['power']:.5f}", flush=True)
    print()


def board(layers, advanced, h_side, pos, fills, w=60, h=40):
    """!
    @brief A board of part 3: full-board zones with the given fills, a 10 mm, 2 W part on layer 1.
    @param layers Copper layers.
    @param advanced True for the typical advanced stack-up of the program (Board.apply_template), False for the simple 1.6 mm stack-up.
    @param h_side Edge coefficient in W/m2K.
    @param pos "centre" or "corner".
    @param fills Fill of each layer.
    @param w Width in mm.
    @param h Height in mm.
    @return Problem.
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=1.6, copper_um=35.0, ambient=cases.T0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    if advanced:
        p.board.dielectrics = []
        p.board.apply_template()
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, w, h))
        p.zones[-1].fill = float(fills[l - 1])
    x0, y0 = ((w - 10) / 2, (h - 10) / 2) if pos == "centre" else (0.0, 0.0)
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + 10, y0 + 10))
    return p


def t_weighted(p, passes=3):
    """!
    @brief Robin with the common edge parameter weighted by the edge temperature of each layer, beta = h sum(s_l E_l) / sum(S_l E_l), E_l the edge integral of layer l.
    @param p Problem.
    @param passes Number of passes from the flux-conserving beta.
    @return float Hottest temperature in degC.
    """
    orig = ae.edge_beta
    r = ae.solve(p, 1.0, edge="robin")
    sh = r["sh"]
    W, H = sh["W"], sh["H"]
    for _ in range(passes):
        bx, by, a = r["bx"], r["by"], r["a"]
        ex, ey = bx.evaluate([0.0, W]), by.evaluate([0.0, H])
        ix, iy = bx.project(0, W), by.project(0, H)
        E = np.array([float(((ex @ a[:, :, l]) @ iy).sum() + ((ey @ a[:, :, l].T) @ ix).sum()) for l in range(sh["L"])])
        _, heff = orig(sh, p)
        beta = heff * float((sh["slab"] * E).sum()) / float((sh["S"] * E).sum())
        ae.edge_beta = lambda sh_, pr_, rule="flux", _b=beta, _h=heff: (_b, _h)
        try:
            r = ae.solve(p, 1.0, edge="robin")
        finally:
            ae.edge_beta = orig
    return r["t_max"]


def part_3():
    """!
    @brief Advanced stack-ups, two-layer boards with partial copper on one side and one-layer boards.
    @return None.
    """
    print("3. boards outside the study: error of the hottest rise against the FVM at 0.5 mm (percent)")
    os.makedirs(OUT, exist_ok=True)
    lines = []
    sets = (("advanced 4 L", 4, True, (1, 1, 1, 1)), ("advanced 6 L", 6, True, (1,) * 6), ("advanced 8 L", 8, True, (1,) * 8),
            ("advanced 4 L partial", 4, True, (0.4, 1, 1, 0.4)), ("advanced 4 L 0.2", 4, True, (0.2, 0.2, 1, 1)),
            ("2 L top full, bottom 0.2", 2, False, (1, 0.2)), ("2 L top full, bottom 0.5", 2, False, (1, 0.5)), ("2 L top 0.2, bottom full", 2, False, (0.2, 1)),
            ("1 L", 1, False, (1,)))
    for label, layers, adv, fills in sets:
        for hs in (10.0, 50.0, 200.0):
            for pos in ("centre", "corner"):
                p = board(layers, adv, hs, pos, fills)
                f = cases.rise(p, "fvm", 0.5)
                sh = analytic._effective_sheet(p, 1.0)
                rat = sh["slab"] / sh["S"]
                share = float(sh["h_edge"].sum() / sh["h_tot"])
                o = {k: ae.solve(p, 1.0, edge=k)["t_max"] - cases.T0 for k in ("faces", "robin", "robin_res")}
                o["t_weighted"] = t_weighted(p) - cases.T0
                e = {k: 100 * (v / f - 1) for k, v in o.items()}
                line = (f"{label:26s} h_side {hs:3.0f} {pos:6s} FVM {f:7.2f} | slab/S spread {rat.max() / rat.min():5.2f} S max/min {sh['S'].max() / sh['S'].min():5.2f} "
                        f"edge share {share:.2f} | faces {e['faces']:+6.2f} robin {e['robin']:+6.2f} robin_res {e['robin_res']:+6.2f} T-weighted {e['t_weighted']:+6.2f}")
                print("  " + line, flush=True)
                lines.append(f"{label}|{hs}|{pos}|{rat.max() / rat.min()}|{sh['S'].max() / sh['S'].min()}|{share}|{e['faces']}|{e['robin']}|{e['robin_res']}|{e['t_weighted']}")
    with open(os.path.join(OUT, "review_checks.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    r = np.array([[float(x) for x in s.split("|")[3:]] for s in lines])
    print(f"  summary ({len(r)} boards): max |err| faces {np.abs(r[:, 3]).max():.2f} %, robin {np.abs(r[:, 4]).max():.2f} %, robin_res {np.abs(r[:, 5]).max():.2f} %, "
          f"T-weighted {np.abs(r[:, 6]).max():.2f} %; robin better than faces on {(np.abs(r[:, 4]) <= np.abs(r[:, 3])).sum()} of {len(r)}")
    print()


def part_4():
    """!
    @brief Where the rest of the error sits: the laminate nodes of the FVM at the edge, and the common beta alone.
    @details (a) Full-copper boards: the FVM puts no laminate nodes where both copper layers are full (laminate.py), so the edge loss of the laminate slab leaves at the
             copper temperature; a fill of 0.9999 on every layer switches the sub-gap nodes on (0.01 % less copper). Both against the independent 3D solver with the
             side film. (b) The worst boards of part 3 against the FVM with one laminate node per gap (SolverOptions.laminate_n_max = 1), which is what the Analytic
             idealises: the remainder is the common edge parameter alone.
    @return None.
    """
    print("4a. FVM full copper against fill 0.9999 (laminate nodes switched on) and the 3D solver with the side film (hottest rise, K)")
    for w, h, layers, t, hs, pos in ((60, 40, 2, 1.6, 10.0, "corner"), (60, 40, 2, 3.2, 10.0, "corner"), (60, 40, 2, 1.6, 50.0, "corner"), (60, 40, 2, 1.6, 200.0, "corner"),
                                     (60, 40, 2, 1.6, 200.0, "centre"), (60, 40, 2, 3.2, 200.0, "corner"), (60, 40, 2, 3.2, 200.0, "edge"),
                                     (60, 40, 4, 1.6, 200.0, "corner"), (30, 20, 2, 0.8, 200.0, "corner")):
        p, xy = cases.board(w, h, layers, t, hs, pos)
        f = cases.rise(p, "fvm", 0.5)
        r3 = cases.ref3d(p, xy, 1.0)
        for z in p.zones:
            z.fill = 0.9999
        f9 = cases.rise(p, "fvm", 0.5)
        print(f"  {w}x{h} L{layers} t{t} h_side {hs:3.0f} {pos:6s}: 3D {r3:7.2f} | FVM full {f:7.2f} ({100 * (f / r3 - 1):+5.1f} %) | FVM fill 0.9999 {f9:7.2f} "
              f"({100 * (f9 / r3 - 1):+5.1f} %) | jump {100 * (f9 / f - 1):+5.2f} %", flush=True)
    print("4b. Robin on the worst boards of part 3 against the FVM and against the FVM with one laminate node per gap (h_side 200, corner)")
    from pcbthermal import SolverOptions, simulate
    for label, layers, adv, fills in (("2 L top full, bottom 0.2", 2, False, (1, 0.2)), ("2 L top 0.2, bottom full", 2, False, (0.2, 1)),
                                      ("2 L top full, bottom 0.5", 2, False, (1, 0.5)), ("4 L (0.2, 0.2, 1, 1)", 4, False, (0.2, 0.2, 1, 1)),
                                      ("4 L (0.3, 1, 1, 1)", 4, False, (0.3, 1, 1, 1)), ("advanced 4 L", 4, True, (1, 1, 1, 1)), ("1 L", 1, False, (1,))):
        p = board(layers, adv, 200.0, "corner", fills)
        f = cases.rise(p, "fvm", 0.5)
        f1 = simulate(p, SolverOptions(cell_mm=0.5, models=("fvm",), laminate_n_max=1)).results["fvm"].t_max - cases.T0
        r = ae.solve(p, 1.0, edge="robin")["t_max"] - cases.T0
        fa = ae.solve(p, 1.0, edge="faces")["t_max"] - cases.T0
        print(f"  {label:26s}: FVM {f:7.2f}, one laminate node {f1:7.2f} | Robin {100 * (r / f - 1):+6.2f} % of the FVM, {100 * (r / f1 - 1):+6.2f} % of the one-node FVM | "
              f"faces {100 * (fa / f1 - 1):+6.2f} % of the one-node FVM", flush=True)
    print()


def main(argv=None):
    """!
    @brief Run the chosen parts.
    @param argv Arguments.
    @return int 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--part", choices=("1", "2", "3", "4"), default=None)
    a = ap.parse_args(argv)
    warnings.filterwarnings("ignore")
    for name, fn in (("1", part_1), ("2", part_2), ("3", part_3), ("4", part_4)):
        if a.part in (None, name):
            fn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
