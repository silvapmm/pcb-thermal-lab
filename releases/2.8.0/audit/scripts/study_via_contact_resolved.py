#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_contact_resolved.py
@brief A via on partial copper (quarter, track end, via outside a copper edge, full plane) against a 3D finite-volume solve with the plated barrel resolved.
@details Question (audit of 2.8.0, REVIEW_A3.md): `docs/validation.md` 34.2 quotes an independent 3D reference for the contact cases of
         `research/via-contact-geometry` (quarter 5.70 K, track 10.34 / 10.89 K, via 0.3 mm outside 1.18 K), but that reference was a scratch script that is
         not in the repository. This script is a second, committed reference: a Cartesian 3D finite-volume solve that imports nothing of the program
         (graded tensor grid, cells of `--fine` mm within 0.45 mm of the via growing by 1.2 to 0.25 mm, the 0.3 mm drill with its 25 um plating as copper
         cells whose conductivity is mixed by the sampled area of the annulus, the hole as air, the plane drilled; copper 385 W/mK; FR-4 0.9 in the plane and
         0.3 through, 12 graded slabs; 3 slabs per copper layer, where a layer has no copper its slabs are FR-4; 50 W/m2K on both faces; sides insulated).
         The boards are those of `research/via-contact-geometry/scripts/study_reference_set.py` (10 x 10 mm, two layers, 1.6 mm, 35 um), rebuilt here from
         their rectangles. Via effect E = maximum of the top copper without the via minus with it. The program side (FVM and FDM at 1, 0.5 and 0.25 mm, the
         same boards built by that study) is printed next to it.
         Run from the repository root: `.venv/bin/python releases/2.8.0/audit/scripts/study_via_contact_resolved.py [--fine 0.025] [--program]`
         (the direct solver up to about 0.05 mm under 1.5 GB; finer cells need pyamg, in the scratch environment `.venv-research`, where the solve is CG preconditioned by smoothed aggregation and the energy balance is printed as the check).
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

ROOT = Path(__file__).resolve().parents[4]
W, C = 10.0, 5.0                     # board side and centre, mm
T_BOARD, T_CU = 1.6, 0.035           # mm
K_CU, K_IP, K_TH, K_AIR = 385.0, 0.9, 0.3, 0.026
H_FACE = 50.0                        # W/m2K, both faces
R_DRILL, PLATING = 0.15, 0.025       # mm

# Each board: top copper rectangles (mm), heater rectangle and power (W); the bottom layer is a full plane on every board
BOARDS = {
    "full d0.3": ([(0, 0, W, W)], (C - 0.5, C - 0.5, C + 0.5, C + 0.5), 0.5),
    "quarter": ([(1, 1, C, C)], (C - 2.5, C - 2.5, C - 0.5, C - 0.5), 0.3),
    "track 0.25": ([(C - 3.5, C - 1, C - 1.5, C + 1), (C - 1.5, C - 0.125, C, C + 0.125)], (C - 3.5, C - 1, C - 1.5, C + 1), 0.3),
    "bareout g0.3": ([(1, 1, C - 0.3, W - 1)], (C - 2.3, C - 1, C - 0.3, C + 1), 0.5),
}


def axis(fine, marks):
    """!
    @brief Cell faces along one axis: uniform `fine` cells within 0.45 mm of the via, geometric growth by 1.2 to 0.25 mm outside; every mark is a face.
    @param fine Cell size near the via in mm.
    @param marks Coordinates in mm that must be faces (copper and heater edges).
    @return numpy.ndarray of increasing faces from 0 to W in mm.
    """
    lo, hi = C - 0.45, C + 0.45
    core = list(np.arange(lo, hi + 1e-9, fine))
    right, h, x = [], fine, hi
    while x < W - 1e-9:
        h = min(h * 1.2, 0.25)
        x = min(x + h, W)
        right.append(x)
    left = [2 * C - v for v in right]
    f = np.array(sorted(set(np.round(left + core + right + list(marks) + [0.0, W], 9))))
    f = f[(f >= 0) & (f <= W)]
    # drop faces closer than a fiftieth of the fine cell (a mark next to a grid face)
    keep = [f[0]]
    for v in f[1:]:
        if v - keep[-1] > fine / 50:
            keep.append(v)
    keep[-1] = W
    return np.array(keep)


def z_faces():
    """!
    @brief Faces through the thickness: three slabs per copper layer, twelve graded slabs in the laminate.
    @return numpy.ndarray of faces in mm, 0 at the bottom.
    """
    d = T_BOARD - 2 * T_CU
    g = np.geomspace(1, 4, 6)
    g = np.concatenate([g, g[::-1]])
    lam = T_CU + np.concatenate([[0], np.cumsum(g / g.sum() * d)])
    return np.unique(np.concatenate([np.linspace(0, T_CU, 4), lam, np.linspace(T_BOARD - T_CU, T_BOARD, 4)]))


def solve(name, fine, with_via):
    """!
    @brief Steady 3D solve of one board.
    @param name Key of BOARDS.
    @param fine Cell size near the via in mm.
    @param with_via True to draw the via.
    @return tuple (maximum rise of the top copper slab in K, number of unknowns, relative energy balance error).
    """
    tops, heater, power = BOARDS[name]
    marks = [v for r in tops for v in (r[0], r[2])] + [heater[0], heater[2]]
    marks_y = [v for r in tops for v in (r[1], r[3])] + [heater[1], heater[3]]
    xf, yf, zf = axis(fine, marks) * 1e-3, axis(fine, marks_y) * 1e-3, z_faces() * 1e-3
    xc, yc, zc = 0.5 * (xf[1:] + xf[:-1]), 0.5 * (yf[1:] + yf[:-1]), 0.5 * (zf[1:] + zf[:-1])
    nx, ny, nz = len(xc), len(yc), len(zc)
    dx, dy, dz = np.diff(xf), np.diff(yf), np.diff(zf)
    top_cu = zc > (T_BOARD - T_CU) * 1e-3
    bot_cu = zc < T_CU * 1e-3
    # copper of the top layer in plan
    X, Y = np.meshgrid(xc * 1e3, yc * 1e3)                    # (ny, nx) in mm
    cu_top = np.zeros((ny, nx), bool)
    for r in tops:
        cu_top |= (X > r[0]) & (X < r[2]) & (Y > r[1]) & (Y < r[3])
    kx = np.empty((nz, ny, nx)); kz = np.empty((nz, ny, nx))
    for k in range(nz):
        if bot_cu[k]:
            kx[k] = kz[k] = K_CU
        elif top_cu[k]:
            kx[k] = np.where(cu_top, K_CU, K_IP); kz[k] = np.where(cu_top, K_CU, K_TH)
        else:
            kx[k] = K_IP; kz[k] = K_TH
    f_hole = np.zeros((ny, nx))
    if with_via:
        # sampled area fractions of the plating annulus and of the hole in every plan cell near the via
        s = (np.arange(16) + 0.5) / 16
        f_ring = np.zeros((ny, nx))
        near_x = np.nonzero(np.abs(xc * 1e3 - C) < 0.3)[0]
        near_y = np.nonzero(np.abs(yc * 1e3 - C) < 0.3)[0]
        for j in near_y:
            for i in near_x:
                px = (xf[i] + s * dx[i]) * 1e3 - C
                py = (yf[j] + s * dy[j]) * 1e3 - C
                r = np.hypot(px[None, :], py[:, None])
                f_ring[j, i] = np.mean((r <= R_DRILL) & (r > R_DRILL - PLATING))
                f_hole[j, i] = np.mean(r <= R_DRILL - PLATING)
        rest = 1.0 - f_ring - f_hole
        for k in range(nz):
            # area-weighted mix (exact for the vertical path; the radial entry of the plane into the plating is as resolved as the cell)
            kx[k] = f_ring * K_CU + f_hole * K_AIR + rest * kx[k]
            kz[k] = f_ring * K_CU + f_hole * K_AIR + rest * kz[k]
    n = nx * ny * nz
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def add(a, b, g):
        rows.append(a.ravel()); cols.append(b.ravel()); vals.append(-g.ravel())
        rows.append(b.ravel()); cols.append(a.ravel()); vals.append(-g.ravel())
        np.add.at(diag, a.ravel(), g.ravel()); np.add.at(diag, b.ravel(), g.ravel())

    area_x = dy[None, :, None] * dz[:, None, None]
    g = area_x / (dx[None, None, :-1] / 2 / kx[:, :, :-1] + dx[None, None, 1:] / 2 / kx[:, :, 1:])
    add(idx[:, :, :-1], idx[:, :, 1:], g)
    area_y = dx[None, None, :] * dz[:, None, None]
    g = area_y / (dy[None, :-1, None] / 2 / kx[:, :-1, :] + dy[None, 1:, None] / 2 / kx[:, 1:, :])
    add(idx[:, :-1, :], idx[:, 1:, :], g)
    area_z = dx[None, None, :] * dy[None, :, None]
    g = area_z / (dz[:-1, None, None] / 2 / kz[:-1] + dz[1:, None, None] / 2 / kz[1:])
    add(idx[:-1], idx[1:], g)
    a2 = (dx[None, :] * dy[:, None])
    g_top = a2 / (1 / H_FACE + dz[-1] / 2 / kz[-1])
    g_bot = a2 / (1 / H_FACE + dz[0] / 2 / kz[0])
    diag[idx[-1].ravel()] += g_top.ravel()
    diag[idx[0].ravel()] += g_bot.ravel()
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)) + sp.diags(diag)
    # source: the heater's power over the top copper slabs under its rectangle (by area), as the program puts it into the copper node
    q = np.zeros(n)
    under = (X > heater[0]) & (X < heater[2]) & (Y > heater[1]) & (Y < heater[3]) & cu_top
    vol = a2[None, :, :] * dz[:, None, None]
    sel = np.zeros((nz, ny, nx), bool)
    sel[top_cu] = under
    q[idx[sel]] = (vol * (1.0 - f_hole)[None, :, :])[sel]          # no heat in the open hole (the program spreads the power over the copper)
    q *= power / q.sum()
    try:
        import pyamg                                                  # in the scratch environment .venv-research: smoothed aggregation as a CG preconditioner
        ml = pyamg.smoothed_aggregation_solver(K.tocsr(), symmetry="symmetric", max_coarse=500)
        T, info = spla.cg(K, q, rtol=1e-12, maxiter=2000, M=ml.aspreconditioner())
        if info != 0:
            raise RuntimeError(f"CG did not converge ({info})")
    except ImportError:
        T = spla.spsolve(K.tocsc(), q, permc_spec="MMD_AT_PLUS_A")
    T = T.reshape(nz, ny, nx)
    loss = (g_top * T[-1]).sum() + (g_bot * T[0]).sum()
    solid = np.broadcast_to(f_hole < 0.5, (nz, ny, nx))
    tmax = float(T[top_cu][solid[top_cu]].max())                    # hottest top-copper cell that is not the open hole
    return tmax, n, abs(loss / power - 1)


def program(name, cell):
    """!
    @brief Via effect of the program's FVM and FDM on the same board (the study's own builder).
    @param name Key of BOARDS.
    @param cell Cell in mm.
    @return tuple (FVM E, FDM E) in K.
    """
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "research/via-contact-geometry/scripts"))
    import study_reference_set as RS  # noqa: E402
    from pcbthermal import SolverOptions, simulate  # noqa: E402
    from pcbthermal.model import Problem  # noqa: E402
    make = RS.make_cases(Problem)[name]
    out = []
    for m in ("fvm", "fdm"):
        t0 = simulate(make(False), SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max
        t1 = simulate(make(True), SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max
        out.append(t0 - t1)
    return tuple(out)


def main():
    """!
    @brief Print the reference via effect of every board (and the program's, with --program).
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--fine", type=float, nargs="+", default=[0.04, 0.025], help="cell sizes near the via, mm")
    ap.add_argument("--program", action="store_true", help="also run the FVM and FDM at 1, 0.5 and 0.25 mm")
    ap.add_argument("--boards", nargs="+", default=list(BOARDS))
    a = ap.parse_args()
    for name in a.boards:
        line = [name]
        for fine in a.fine:
            t0, n, b0 = solve(name, fine, False)
            t1, _, b1 = solve(name, fine, True)
            line.append(f"fine {fine} mm: E {t0 - t1:.3f} K (rise {t1:.1f} K, {n} unknowns, balance {max(b0, b1):.0e})")
        if a.program:
            for cell in (1.0, 0.5, 0.25):
                e = program(name, cell)
                line.append(f"cell {cell}: FVM {e[0]:.3f} FDM {e[1]:.3f}")
        print(" | ".join(line), flush=True)


if __name__ == "__main__":
    main()
