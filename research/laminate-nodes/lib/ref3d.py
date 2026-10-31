#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d.py
@brief The independent resolved reference of this investigation: a 3D finite-volume solver of a laminated board with patterned copper (steady and in time), graded sub-slabs through every
        gap, a one-layer board with its laminate, vias as copper area in the through conductivity, quadrant symmetry, and the Richardson/GCI extrapolation of a sequence of grids.
@details It imports nothing from the program (the numbers of the board come in as a dict, `boards.board_numbers`). The matrix is the one of `bare-spot-under-source/lib/resolved3d.py`
         (series of half-cell resistances, films through the half outer cell, insulated sides, the source a flux on a rectangle of the top face, the surface temperature of a source cell
         corrected from the cell centre to the face), written again here to have the heat capacities and the graded slabs; `tests/test_ref3d.py` checks it against that solver, against a
         series circuit, the energy balance and the closed form of Muzychka, Culham and Yovanovich (2003) (`bare-spot-under-source/lib/closed_forms.py`).
         The reference peak is the face temperature (`surf`), the quantity a user of a part on the face wants; the value at the centre of the top slab is returned too (`max_centre`).
         Slabs top down: copper layer l (thickness t_cu, in-plane/through conductivity mixed arithmetically with the laminate of the adjacent gap by the copper fill), then the gap l
         cut into `nsub` sub-slabs (graded by `ratio`: thinner towards the copper faces); a one-layer board has its laminate under the copper cut the same way.
@note Written without a run in the preparation phase (py_compile only).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import boards as BD
import rule as RU


def slabs(nb, fills, nsub, ratio=1.0, via_cols=None, dx_m=None):
    """!
    @brief The slab list of a board, top down.
    @param nb dict from boards.board_numbers.
    @param fills List (one per copper layer) of copper fill arrays (ny, nx).
    @param nsub Sub-slabs per gap (int, or one per gap).
    @param ratio Grading of the sub-slabs (rule.sub_gaps).
    @param via_cols List of (i, j, copper area in m2) of the cells with a via barrel (its copper area is added to the through conductivity of the laminate slabs of the cell).
    @param dx_m Cell size in m (needed with via_cols).
    @return list of dicts with dz (m), kxy and kz (arrays (ny, nx)), rcp (J/m3K array), kind ("cu" or "gap").
    """
    L = nb["layers"]
    ny, nx = fills[0].shape
    nsub = [nsub] * len(nb["gaps"]) if np.isscalar(nsub) else list(nsub)
    out = []

    def lam(g):
        return nb["kxy"][g], nb["kz"][g], nb["rcp"][g]

    for l in range(L):
        g = max(l - 1, 0) if L > 1 else 0
        kxy_l, kz_l, rcp_l = lam(g)
        f = fills[l]
        out.append(dict(kind="cu", dz=nb["t_cu"][l], kxy=kxy_l + f * (nb["k_cu"] - kxy_l), kz=kz_l + f * (nb["k_cu"] - kz_l), rcp=rcp_l + f * (nb["rcp_cu"] - rcp_l)))
        if l < L - 1 or L == 1:
            gg = l
            kxy_g, kz_g, rcp_g = lam(gg)
            for dz in RU.sub_gaps(nb["gaps"][gg], nsub[gg], ratio):
                kz_arr = np.full((ny, nx), kz_g)
                if via_cols:
                    for (i, j, area) in via_cols:
                        kz_arr[i, j] += nb["k_cu"] * area / dx_m ** 2
                out.append(dict(kind="gap", dz=dz, kxy=np.full((ny, nx), kxy_g), kz=kz_arr, rcp=np.full((ny, nx), rcp_g)))
    return out


def assemble(dx, sl, h_top, h_bottom):
    """!
    @brief Conductance matrix and heat capacities of the slab list.
    @param dx Cell size in m.
    @param sl Slab list from slabs().
    @param h_top Film on the top face in W/m2K (acts on the whole face, also under the source, as the program does).
    @param h_bottom Film on the bottom face.
    @return tuple (K csc, C vector in J/K, dz array, shape (nz, ny, nx)).
    """
    nz, (ny, nx) = len(sl), sl[0]["kxy"].shape
    dz = np.array([s["dz"] for s in sl])
    kxy = np.stack([s["kxy"] for s in sl])
    kz = np.stack([s["kz"] for s in sl])
    rcp = np.stack([s["rcp"] for s in sl])
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        a, b, g = a.ravel(), b.ravel(), g.ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    dzv = dz[:, None, None]
    ga = kxy * dzv * dx / (dx / 2)
    link(idx[:, :, :-1], idx[:, :, 1:], ga[:, :, :-1] * ga[:, :, 1:] / (ga[:, :, :-1] + ga[:, :, 1:]))
    link(idx[:, :-1, :], idx[:, 1:, :], ga[:, :-1, :] * ga[:, 1:, :] / (ga[:, :-1, :] + ga[:, 1:, :]))
    A = dx * dx
    gz = kz * A / (dzv / 2)
    link(idx[:-1], idx[1:], gz[:-1] * gz[1:] / (gz[:-1] + gz[1:]))
    gt = 1.0 / (1.0 / (h_top * A) + 1.0 / gz[0]) if h_top > 0 else np.zeros((ny, nx))
    gb = 1.0 / (1.0 / (h_bottom * A) + 1.0 / gz[-1]) if h_bottom > 0 else np.zeros((ny, nx))
    diag[idx[0].ravel()] += gt.ravel()
    diag[idx[-1].ravel()] += gb.ravel()
    K = (sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)) + sp.diags(diag)).tocsc()
    C = (rcp * dzv * A).ravel()
    return K, C, dz, (nz, ny, nx), gt, gb


def source_mask(nx, ny, dx_mm, rect_mm, x_lo=0.0, y_lo=0.0):
    """!
    @brief Cells whose centre lies in a rectangle.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx_mm Cell size in mm.
    @param rect_mm (x0, y0, x1, y1) in mm in board coordinates.
    @param x_lo x of the left edge of the grid in mm.
    @param y_lo y of the bottom edge of the grid in mm.
    @return Boolean array (ny, nx).
    @throws ValueError If the rectangle covers no cell.
    """
    xs, ys = x_lo + (np.arange(nx) + 0.5) * dx_mm, y_lo + (np.arange(ny) + 0.5) * dx_mm
    m = (xs[None, :] > rect_mm[0]) & (xs[None, :] < rect_mm[2]) & (ys[:, None] > rect_mm[1]) & (ys[:, None] < rect_mm[3])
    if not m.any():
        raise ValueError("the source covers no cell")
    return m


def setup(spec, p, dx_mm, nsub, ratio=1.0, quadrant=None):
    """!
    @brief Everything of a reference run before the solve: slabs, matrix, source vector, geometry of the domain.
    @param spec A boards.Spec.
    @param p The program's Problem of the spec (only its numbers are read).
    @param dx_mm Cell size in mm (the shapes must lie on its lines).
    @param nsub Sub-slabs per gap.
    @param ratio Grading.
    @param quadrant True: the quadrant x, y >= centre with the sides insulated (None: when the spec is symmetric).
    @return dict with K, C, q, dz, shape, mask, gt, gb, power, dx, frac.
    """
    nb = BD.board_numbers(p)
    quadrant = spec.symmetric() if quadrant is None else quadrant
    c = spec.size / 2
    lo = c if quadrant else 0.0
    n = int(round((spec.size - lo) / dx_mm))
    fills = [BD.raster(spec.shape(l), n, n, dx_mm, spec.size, lo, lo) for l in range(nb["layers"])]
    via_cols = []
    if spec.vias:
        for (x, y), v in zip(spec.vias, p.vias):
            via_cols.append((int((y - lo) / dx_mm), int((x - lo) / dx_mm), v.thermal_area(p.board.via_plating, nb["k_cu"])))
    sl = slabs(nb, fills, nsub, ratio, via_cols, dx_mm * 1e-3)
    K, C, dz, shape, gt, gb = assemble(dx_mm * 1e-3, sl, nb["h_top"], nb["h_bottom"])
    pr = spec.part_rect()
    rect = (max(pr[0], lo), max(pr[1], lo), pr[2], pr[3])
    mask = source_mask(n, n, dx_mm, rect, lo, lo)
    frac = ((rect[2] - rect[0]) * (rect[3] - rect[1])) / ((pr[2] - pr[0]) * (pr[3] - pr[1]))
    q = np.zeros(shape)
    q[0][mask] = spec.power * frac / mask.sum()
    return dict(K=K, C=C, q=q, dz=dz, shape=shape, mask=mask, gt=gt, gb=gb, power=spec.power * frac, dx=dx_mm * 1e-3, sl=sl, nb=nb)


def solve_fills(nb, fills, dx_mm, nsub, rect_mm, power, ratio=1.0):
    """!
    @brief Steady reference of a board given by copper fill arrays on a square grid (real windows), the source a rectangle of the top face; the whole grid is solved (no symmetry).
    @param nb dict from boards.board_numbers.
    @param fills List (one per copper layer) of fill arrays (n, n) with row 0 at y = 0.
    @param dx_mm Cell size in mm.
    @param nsub Sub-slabs per gap.
    @param rect_mm Source rectangle (x0, y0, x1, y1) in mm on the grid.
    @param power Heat in W.
    @param ratio Grading.
    @return dict with max and mean of the face over the source cells, unknowns, balance, surf (n, n) and mask.
    """
    ny, nx = fills[0].shape
    sl = slabs(nb, fills, nsub, ratio)
    K, C, dz, shape, gt, gb = assemble(dx_mm * 1e-3, sl, nb["h_top"], nb["h_bottom"])
    mask = source_mask(nx, ny, dx_mm, rect_mm)
    q = np.zeros(shape)
    q[0][mask] = power / mask.sum()
    T = spla.spsolve(K, q.ravel(), permc_spec="MMD_AT_PLUS_A").reshape(shape)
    A = (dx_mm * 1e-3) ** 2
    surf = (T[0] + np.where(mask, q[0], 0.0) * dz[0] / (2 * sl[0]["kz"] * A)) / (1 + nb["h_top"] * dz[0] / (2 * sl[0]["kz"]))
    out = float((gt * T[0]).sum() + (gb * T[-1]).sum())
    return {"max": float(surf[mask].max()), "mean": float(surf[mask].mean()), "unknowns": int(T.size), "balance": out / power, "surf": surf, "mask": mask}


def solve_spec(spec, p, dx_mm, nsub, ratio=1.0, quadrant=None):
    """!
    @brief Steady reference peak of a spec.
    @param spec A boards.Spec.
    @param p The Problem of the spec.
    @param dx_mm Cell size in mm.
    @param nsub Sub-slabs per gap.
    @param ratio Grading of the sub-slabs.
    @param quadrant See setup().
    @return dict with max (face, K), mean (face, over the source cells), max_centre (top slab centre), unknowns, balance (heat out / heat in).
    """
    s = setup(spec, p, dx_mm, nsub, ratio, quadrant)
    nz, ny, nx = s["shape"]
    T = spla.spsolve(s["K"], s["q"].ravel(), permc_spec="MMD_AT_PLUS_A").reshape(nz, ny, nx)
    A, dz0 = s["dx"] ** 2, s["dz"][0]
    kz0 = s["sl"][0]["kz"]
    h_top = s["nb"]["h_top"]
    qin = np.where(s["mask"], s["q"][0], 0.0)
    surf = (T[0] + qin * dz0 / (2 * kz0 * A)) / (1 + h_top * dz0 / (2 * kz0))
    out = float((s["gt"] * T[0]).sum() + (s["gb"] * T[-1]).sum())
    return {"max": float(surf[s["mask"]].max()), "mean": float(surf[s["mask"]].mean()), "max_centre": float(T[0][s["mask"]].max()), "unknowns": int(T.size),
            "balance": out / s["power"], "T": T, "mask": s["mask"], "surf": surf}


def transient_spec(spec, p, dx_mm, nsub, times, ratio=1.0, quadrant=None, scheme=0.5, substeps=8):
    """!
    @brief Step response of the reference: the board at rest, the power switched on at t = 0, the face peak and the mean of the source cells at the given times.
    @param spec A boards.Spec.
    @param p The Problem.
    @param dx_mm Cell size in mm.
    @param nsub Sub-slabs per gap.
    @param times Increasing times in s (the first step starts at 0; steps between the times are taken as 4 equal sub-steps of the theta method).
    @param ratio Grading.
    @param quadrant See setup().
    @param scheme Theta of the theta method (0.5 Crank-Nicolson, 1 implicit Euler).
    @param substeps Steps of the theta method between two times (the first interval, for scheme < 1, is taken by 8 implicit Euler steps).
    @return dict with times, peak (K, node value of the top slab; the face correction is the steady one and is left out), mean.
    """
    s = setup(spec, p, dx_mm, nsub, ratio, quadrant)
    K, C, q = s["K"], s["C"], s["q"].ravel()
    x = np.zeros(q.size)
    out_peak, out_mean, t = [], [], 0.0
    cache = {}
    nz, ny, nx = s["shape"]
    for i, tt in enumerate(times):
        # Rannacher start-up: a step input excites the stiff modes, which Crank-Nicolson only damps in sign; the first interval is taken by implicit Euler in small steps
        th, nst = (1.0, 8) if (i == 0 and scheme < 1.0) else (scheme, substeps)
        dt = (tt - t) / nst
        for _ in range(nst):
            key = (round(dt, 12), th)
            if key not in cache:
                cache[key] = (spla.splu((sp.diags(C / dt) + th * K).tocsc()), (sp.diags(C / dt) - (1 - th) * K).tocsr())
            lu, B = cache[key]
            x = lu.solve(B @ x + q)
        t = tt
        top = x.reshape(nz, ny, nx)[0]
        out_peak.append(float(top[s["mask"]].max()))
        out_mean.append(float(top[s["mask"]].mean()))
    return {"times": list(times), "peak": out_peak, "mean": out_mean}


def richardson(values, r=2.0):
    """!
    @brief Extrapolation of a sequence of values on grids refined by the factor r (coarse to fine, three or more), with the observed order and the grid convergence index of the finest.
    @param values List of at least three values f1 (coarse), f2, f3 (fine).
    @param r Refinement ratio between consecutive grids.
    @return dict with limit, order p, gci_fine (fraction of the fine value, safety factor 1.25), monotone (bool).
    """
    f1, f2, f3 = values[-3:]
    d21, d32 = f2 - f1, f3 - f2
    mono = d21 * d32 > 0
    p = float(np.log(abs(d21 / d32)) / np.log(r)) if mono and d32 != 0 else float("nan")
    lim = f3 + d32 / (r ** p - 1.0) if mono and np.isfinite(p) else float("nan")
    gci = 1.25 * abs(d32 / f3) / (r ** p - 1.0) if mono and np.isfinite(p) else float("nan")
    return {"limit": lim, "order": p, "gci_fine": gci, "monotone": bool(mono)}


def converged(spec, p, dxs=(0.5, 0.25, 0.125), nsubs=(4, 8, 16), ratio=1.0):
    """!
    @brief The reference of a spec on a sequence of grids (cell and sub-slabs refined together), its Richardson limit in the plane, and the distance of the finest from it.
    @param spec A boards.Spec.
    @param p The Problem.
    @param dxs Cell sizes in mm, coarse to fine (each half the previous).
    @param nsubs Sub-slabs per gap, same length.
    @param ratio Grading.
    @return dict with values (face max of every grid), limit, order, gci_fine, unknowns.
    """
    runs = [solve_spec(spec, p, dx, n, ratio) for dx, n in zip(dxs, nsubs)]
    v = [r["max"] for r in runs]
    out = richardson(v)
    out.update(values=v, unknowns=[r["unknowns"] for r in runs])
    return out


def converged_split(spec, p, deep=False):
    """!
    @brief The distance of the production reference (0.25 mm cell, 8 sub-slabs per gap) from its limit, the cell and the sub-slabs separated (the joint sequence of `converged` is too heavy for many layers).
    @details Cell sequence at 8 sub-slabs: 0.5, 0.25, 0.125 mm (boards with 4 or more layers: at 4 sub-slabs, the production value is then replaced by the 0.25 mm value of that sequence for the cell correction). Sub-slab sequence at 0.25 mm: 4, 8, 16
             (4 or more layers: 2, 4, 8). Each sequence goes through `richardson`; the correction of a sequence is its limit over the production value minus one, and the total is their product.
    @param spec A boards.Spec.
    @param p The Problem.
    @param deep True for the boards with 4 or more layers (the coarser sequences above).
    @return dict with production (K), dx and nsub values, limits, orders, GCIs, corr_dx, corr_nz, corr_total (fractions of the production value).
    """
    dxs = (0.5, 0.25, 0.125)
    nzs = (2, 4, 8) if deep else (4, 8, 16)
    vx = [solve_spec(spec, p, d, 4 if deep else 8)["max"] for d in dxs]
    vz = [solve_spec(spec, p, 0.25, n)["max"] for n in nzs]
    prod = solve_spec(spec, p, 0.25, 8)["max"]
    rx, rz = richardson(vx), richardson(vz)
    cx = rx["limit"] / vx[1] - 1.0               # relative to the 0.25 mm cell of the same sub-slab count
    cz = rz["limit"] / prod - 1.0
    return {"production": prod, "dx_values": vx, "nz_values": vz, "dx_rich": rx, "nz_rich": rz, "corr_dx": cx, "corr_nz": cz, "corr_total": (1 + cx) * (1 + cz) - 1.0}
