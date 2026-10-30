#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lumped_groups.py
@brief Variants of the via group (macro) term of the Lumped model, as in-memory copies on top of `research/lumped-analytic-vias/lib/lumped_patch.py` (the program is never edited).
@details `lumped_patch` replaces the vertical coupling of every ring by a Kron-reduced star (well, barrel, well, ...). Its macro term adds, for a group of N vias in a ring,
         the constriction of the whole group as one disc of radius r_cl inside the area of the rings it touches (radius R_macro), `krogh(S, R_macro, r_cl)`, in every plane.
         This module replaces `lumped_patch._via_couplings` by a copy with these extra choices (`OPTIONS`):
         * `macro`   "all" (the patch: every group), "none" (micro well only), "out" (the macro term only for the vias that lie OUTSIDE the footprint, ring k >= 1: the hypothesis that
                     the rings already carry the lateral spreading inside the footprint, so that the term would count it twice), "in" (only the vias of the footprint),
                     "loss" (the macro term from the lossy cell of `constriction.cell_with_loss`, the loss being the one of the plane under the group), "loss_out";
         * `macro_scale` factor on the macro resistance (the oracle scans of the study);
         * `micro`   "nn" (cell = Wigner-Seitz disc of the nearest neighbour, capped by the ring) or "ring" (the ring's area per via);
         * `eff`     if > 0, the dense group is smeared: a group whose pitch is below `eff` fin lengths of the sheet loses its micro well in the planes where it is dense (study knob).
         Every group seen is recorded in `SEEN` (n_g, r_cl, R_macro, the fin length of each plane) so that the studies can relate the best macro factor to the geometry.
@note The `lumped_patch` context manager does the rest (it compiles the copy of `_heater_network`); `patched` here installs this function first.
"""

import contextlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "lumped-analytic-vias", "lib"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import constriction as cr                                                   # noqa: E402
import lumped_patch as lp                                                   # noqa: E402

OPTIONS = {"macro": "all", "macro_scale": 1.0, "micro": "nn", "loss_scale": 1.0}
SEEN = []                                                                    # groups seen by the last network built (diagnostics)


def _groups(pts):
    """!
    @brief Nearest-neighbour distances and single-linkage groups of the vias (two vias joined if their distance is at most twice the larger nearest-neighbour distance).
    @param pts (n, 2) positions in m.
    @return tuple (d_nn, group) arrays of length n.
    """
    nv = len(pts)
    if nv < 2:
        return np.full(nv, np.inf), np.zeros(nv, int)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    tree = cKDTree(pts)
    d_nn = tree.query(pts, k=2)[0][:, 1]
    pairs = tree.query_pairs(float(2.0 * d_nn.max()), output_type="ndarray") if nv < 2000 else np.zeros((0, 2), int)
    keep = [(i, j) for i, j in pairs if np.hypot(*(pts[i] - pts[j])) <= 2.0 * max(d_nn[i], d_nn[j])]
    if keep:
        ii, jj = np.array(keep).T
        _, group = connected_components(coo_matrix((np.ones(len(ii)), (ii, jj)), shape=(nv, nv)), directed=False)
    else:
        group = np.arange(nv)
    return d_nn, group


def via_couplings(net, cov, idx, R, cnt, ring_sum, S, g_top, g_bot, gz, nb):
    """!
    @brief Vertical couplings between the sheets of every ring with the wells of the vias; copy of `lumped_patch._via_couplings` with the choices of `OPTIONS`.
    @param net Network of the problem.
    @param cov Footprint coverage (unused, kept for the signature of the hook).
    @param idx (ny, nx) ring index of every cell.
    @param R Number of rings.
    @param cnt Cells per ring.
    @param ring_sum Function that sums a per-cell array over the rings.
    @param S (L, R) mean sheet conductance of every ring.
    @param g_top (L, R) conductance to the ambient through the top face per ring.
    @param g_bot (L, R) the same through the bottom face.
    @param gz (nb-1, R) total vertical conductance per gap and ring (dielectric + barrels).
    @param nb Number of board layers.
    @return dict {(l, m): array (R,)} of conductances between sheet l and sheet m (l < m) of every ring.
    """
    from pcbthermal.geometry import cell_index_of_point
    prob = lp.PROBLEM["p"]
    L1 = nb - 1
    GZ = {(l, l + 1): gz[l].astype(float).copy() for l in range(L1)}
    lp.GZVIA.clear()
    lp.ACL0[0] = 0.0
    SEEN.clear()
    if prob is None or not prob.vias or L1 < 1:
        return GZ
    b = prob.board
    d = b.gap_thicknesses()
    pts = np.array([(v.x, v.y) for v in prob.vias])
    nv = len(pts)
    d_nn, group = _groups(pts)
    ring_of = np.full(nv, -1)
    for iv, v in enumerate(prob.vias):
        i, j = cell_index_of_point(v.x, v.y, net.nx, net.ny, net.dx, net.dy)
        ring_of[iv] = int(idx[i, j])
    cell = net.dx * net.dy
    n_ring = np.bincount(ring_of[ring_of >= 0], minlength=R)
    gv_ring = np.zeros((L1, R))
    for iv, v in enumerate(prob.vias):
        if ring_of[iv] >= 0:
            gv_ring[:, ring_of[iv]] += b.materials.k_copper * v.thermal_area(b.via_plating, b.materials.k_copper) / d
    eta = cr.ETA
    mode = OPTIONS["macro"]
    for g in np.unique(group):
        members = np.flatnonzero((group == g) & (ring_of >= 0))
        if len(members) == 0:
            continue
        n_g = len(members)
        rings_g = np.unique(ring_of[members])
        a_touched = float(sum(cnt[k] * cell for k in rings_g))
        r_cell_g = float(np.mean(d_nn[members])) / np.sqrt(np.pi)
        for k in rings_g:
            mem = members[ring_of[members] == k]
            n = len(mem)
            gv = np.array([b.materials.k_copper * prob.vias[i].thermal_area(b.via_plating, b.materials.k_copper) / d for i in mem]).sum(axis=0)
            a = eta * float(np.mean([prob.vias[i].diameter / 2.0 for i in mem]))
            r_ring = float(np.sqrt(cnt[k] * cell / (np.pi * n_ring[k])))
            r_cell = min(r_ring, r_cell_g) if OPTIONS["micro"] == "nn" else r_ring
            r_cl = float(np.sqrt(n_g)) * r_cell
            if k == 0:
                lp.ACL0[0] += n * np.pi * r_cell ** 2
            r_macro = float(np.sqrt(a_touched / np.pi))
            g_gap = gv / n
            g_well = np.full(nb, np.inf)
            lam = np.zeros(nb)
            for l in range(nb):
                s_l = S[l, k]
                if s_l <= 0:
                    g_well[l] = 0.0
                    continue
                area_k = cnt[k] * cell
                g_loss = (g_top[l, k] + g_bot[l, k]) / area_k
                for m in (l - 1, l + 1):
                    if 0 <= m < nb:
                        g_loss += max(gz[min(l, m), k] - gv_ring[min(l, m), k], 0.0) / area_k
                lam[l] = float(np.sqrt(s_l / g_loss)) if g_loss > 0 else np.inf
                rc = cr.krogh(s_l, r_cell, a)
                use_macro = n_g > 1 and r_macro > r_cl and mode != "none"
                skip = OPTIONS.get("skip_rings", (0,) if mode in ("out", "loss_out") else ())
                if k in skip:
                    use_macro = False
                if mode == "in" and k != 0:
                    use_macro = False
                if use_macro:
                    if mode in ("loss", "loss_out") and g_loss > 0:
                        macro = cr.cell_with_loss(s_l, OPTIONS["loss_scale"] * g_loss, r_cl, r_macro, 1.0)["R_c"]
                    else:
                        macro = cr.krogh(s_l, r_macro, r_cl)
                    rc += OPTIONS["macro_scale"] * n_g * macro
                g_well[l] = np.inf if rc <= 0 else 1.0 / rc
            SEEN.append({"ring": int(k), "n_g": int(n_g), "n": int(n), "r_cell": r_cell, "r_cl": r_cl, "r_macro": r_macro, "lam": lam.tolist(), "S": S[:, k].tolist()})
            G = cr.kron_barrel(g_gap, g_well) * n
            for l in range(nb):
                for m in range(l + 1, nb):
                    if (l, m) not in GZ:
                        GZ[(l, m)] = np.zeros(R)
                    lp.GZVIA.setdefault((l, m), np.zeros(R))[k] += G[l, m]
                    if m == l + 1:
                        GZ[(l, m)][k] += G[l, m] - gv[l]
                    else:
                        GZ[(l, m)][k] += G[l, m]
    return GZ


@contextlib.contextmanager
def patched(macro="all", macro_scale=1.0, micro="nn", loss_scale=1.0):
    """!
    @brief Install the Lumped model with the constriction wells and the chosen group term; restore everything on exit.
    @param macro "all", "none", "out", "in", "loss" or "loss_out" (see the module header).
    @param macro_scale Factor on the macro resistance.
    @param micro "nn" or "ring".
    @param loss_scale Factor on the vertical loss used by the lossy macro cell.
    @return Context manager.
    """
    old_fn = lp._via_couplings
    old_opts = dict(OPTIONS)
    OPTIONS.update(macro=macro, macro_scale=macro_scale, micro=micro, loss_scale=loss_scale)
    lp._via_couplings = via_couplings
    try:
        with lp.patched("krogh", cell="nn" if micro == "nn" else "ring", cluster=False):
            yield
    finally:
        lp._via_couplings = old_fn
        OPTIONS.clear()
        OPTIONS.update(old_opts)
