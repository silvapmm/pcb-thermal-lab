#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lumped_patch.py
@brief In-memory copy of the Lumped model with a constriction resistance in series with every via (the program's `lumped.py` is never edited).
@details `pcbthermal.lumped._heater_network` is read with `inspect.getsource`, three blocks are replaced and the function is compiled again inside the module of the program:
         1. after the ring sums, the vertical coupling of every ring is rebuilt as a dictionary `GZ[(l, m)]` (array over the rings): the dielectric part of `net.gz` joins
            neighbouring sheets as before; the barrel part of the vias is split from it and, for each ring that holds vias, replaced by the Kron reduction of the star
            [sheet l -- well R_c(l) -- barrel node l -- barrel conductance -- barrel node l+1 ...] (`constriction.kron_barrel`), times the number of vias of the ring;
         2. the loop that couples the sheets in `solve` uses `GZ`;
         3. the effective loss under the footprint (the interior factors of the disc solution) sums the same couplings.
         The well of sheet l in ring k is `R_c = c_shape(R_cell / r_t) / (2 pi S_lk)`; options (all in `OPTIONS`):
         * `mode`      "off" (the program: no constriction, must reproduce the program bit by bit), "krogh" (exact cell formula), "log" (ln(R_cell / r_t) - c3),
                       "bessel" (the cell with the loss of the sheet, `constriction.cell_with_loss`, the loss taken from the ring's own vertical conductances);
         * `eta`       r_t / r_v (the radius of the equivalent sink; exp(-1/4) in the layered idealisation);
         * `c3`        the constant of the "log" mode (0.75);
         * `cell`      "ring" (R_cell = sqrt(A_ring / (pi N_vias)) -- the Wigner-Seitz radius of the vias of the ring) or "cap" (the same capped by `cap_lambda` times the
                       fin length of the sheet).
@note Vias that carry no conductance (open, thin plating) still give a well; only rings with at least one via are touched. Blocks: left alone (the block layers are not joined by vias).
"""

import contextlib
import inspect
import os
import re
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import constriction as cr                                                   # noqa: E402

OPTIONS = {"mode": "off", "eta": cr.ETA, "c3": 0.75, "cell": "ring", "cap_lambda": 1.0, "cluster": False, "scale": 1.0, "macro_scale": 1.0, "peak": False, "macro_cap": 0.0}
ACL0 = [0.0]                                                                # area covered by the cells of the vias of ring 0
GZVIA = {}                                                                  # barrel-only couplings of the last network built, for the peak term
PROBLEM = {"p": None}                                                       # the Problem being solved (the network does not keep the vias)


_SETUP = '''
    # ---- research patch: vertical couplings with the constriction of the vias (research/lumped-analytic-vias/lib/lumped_patch.py)
    GZ = _via_couplings(net, cov, idx, R, cnt, ring_sum, S, g_top, g_bot, gz, nb)
'''


def _via_couplings(net, cov, idx, R, cnt, ring_sum, S, g_top, g_bot, gz, nb):
    """!
    @brief Vertical couplings between the sheets of every ring, with the constriction resistance of the vias.
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
    prob = PROBLEM["p"]
    b = prob.board
    L1 = nb - 1
    GZ = {(l, l + 1): gz[l].astype(float).copy() for l in range(L1)}
    GZVIA.clear()
    ACL0[0] = 0.0
    if OPTIONS["mode"] == "off" or not prob.vias or L1 < 1:
        return GZ
    d = b.gap_thicknesses()
    pts = np.array([(v.x, v.y) for v in prob.vias])
    nv = len(pts)
    # Nearest-neighbour distance of every via and the groups (single linkage: two vias are joined if their distance is at most twice the larger nearest-neighbour distance)
    if nv > 1:
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        d_nn = tree.query(pts, k=2)[0][:, 1]
        pairs = tree.query_pairs(float(2.0 * d_nn.max()), output_type="ndarray") if len(pts) < 2000 else np.zeros((0, 2), int)
        keep = [(i, j) for i, j in pairs if np.hypot(*(pts[i] - pts[j])) <= 2.0 * max(d_nn[i], d_nn[j])]
        if keep:
            ii, jj = np.array(keep).T
            _, group = connected_components(coo_matrix((np.ones(len(ii)), (ii, jj)), shape=(nv, nv)), directed=False)
        else:
            group = np.arange(nv)
    else:
        d_nn = np.full(nv, np.inf)
        group = np.zeros(nv, int)
    ring_of = np.full(nv, -1)
    for iv, v in enumerate(prob.vias):
        i, j = cell_index_of_point(v.x, v.y, net.nx, net.ny, net.dx, net.dy)
        ring_of[iv] = int(idx[i, j])
    cell = net.dx * net.dy
    n_ring = np.bincount(ring_of[ring_of >= 0], minlength=R)             # vias in every ring
    gv_ring = np.zeros((L1, R))                                           # barrel conductance of all the vias of every ring and gap
    for iv, v in enumerate(prob.vias):
        if ring_of[iv] >= 0:
            gv_ring[:, ring_of[iv]] += b.materials.k_copper * v.thermal_area(b.via_plating, b.materials.k_copper) / d
    mode, eta = OPTIONS["mode"], OPTIONS["eta"]
    for g in np.unique(group):
        members = np.flatnonzero((group == g) & (ring_of >= 0))
        if len(members) == 0:
            continue
        n_g = len(members)
        rings_g = np.unique(ring_of[members])
        a_touched = float(sum(cnt[k] * cell for k in rings_g))              # area of the rings that the group touches
        r_cell_g = float(np.mean(d_nn[members])) / np.sqrt(np.pi)           # Wigner-Seitz radius from the spacing of the group (inf for a lone via)
        for k in rings_g:
            mem = members[ring_of[members] == k]
            n = len(mem)
            gv = np.array([b.materials.k_copper * prob.vias[i].thermal_area(b.via_plating, b.materials.k_copper) / d for i in mem]).sum(axis=0)
            a = eta * float(np.mean([prob.vias[i].diameter / 2.0 for i in mem]))
            r_ring = float(np.sqrt(cnt[k] * cell / (np.pi * n_ring[k])))     # Wigner-Seitz radius from the ring: its area per via
            r_cell = min(r_ring, r_cell_g) if OPTIONS["cell"] == "nn" else r_ring
            r_cl = float(np.sqrt(n_g)) * r_cell                             # radius of the disc that the group covers
            if k == 0:
                ACL0[0] += n * np.pi * r_cell ** 2                  # area that the vias of the footprint cover (their cells)
            r_macro = float(np.sqrt(a_touched / np.pi))                     # radius of the disc of the rings it touches
            g_gap = gv / n                                                  # barrel conductance per via and gap
            g_well = np.full(nb, np.inf)
            for l in range(nb):
                s_l = S[l, k]
                if s_l <= 0:
                    g_well[l] = 0.0
                    continue
                # Loss of the sheet per area: films plus the dielectric couplings to the neighbours; the fin length of the sheet caps the cells
                area_k = cnt[k] * cell
                g_loss = (g_top[l, k] + g_bot[l, k]) / area_k
                for m in (l - 1, l + 1):
                    if 0 <= m < nb:
                        g_loss += max(gz[min(l, m), k] - gv_ring[min(l, m), k], 0.0) / area_k
                rc_cell, rc_macro = r_cell, r_macro
                if OPTIONS["cell"] == "cap" and g_loss > 0:
                    lam_cap = OPTIONS["cap_lambda"] * float(np.sqrt(s_l / g_loss))
                    rc_cell = min(r_cell, lam_cap)
                    rc_macro = min(r_macro, lam_cap)
                if OPTIONS["macro_cap"] > 0 and g_loss > 0:
                    rc_macro = min(rc_macro, OPTIONS["macro_cap"] * float(np.sqrt(s_l / g_loss)))   # the cluster draws heat only from within a few fin lengths of the sheet
                if mode == "log":
                    rc = max(np.log(rc_cell / a) - OPTIONS["c3"], 0.0) / (2.0 * np.pi * s_l) if rc_cell > a else 0.0
                elif mode == "bessel" and g_loss > 0 and rc_cell > a:
                    rc = cr.cell_with_loss(s_l, g_loss, a, rc_cell, 1.0)["R_c"]
                else:
                    rc = cr.krogh(s_l, rc_cell, a)
                if OPTIONS["cluster"] and n_g > 1 and rc_macro > r_cl:
                    rc += OPTIONS["macro_scale"] * n_g * cr.krogh(s_l, rc_macro, r_cl)               # the group as one disc: its n_g vias in parallel share the resistance
                rc *= OPTIONS["scale"]                                      # study knob: scale of the constriction (1 = as derived)
                g_well[l] = np.inf if rc <= 0 else 1.0 / rc
            G = cr.kron_barrel(g_gap, g_well) * n                          # couplings between the sheets, the n vias of this group in this ring in parallel
            for l in range(nb):
                for m in range(l + 1, nb):
                    if (l, m) not in GZ:
                        GZ[(l, m)] = np.zeros(R)
                    GZVIA.setdefault((l, m), np.zeros(R))[k] += G[l, m]
                    if m == l + 1:
                        GZ[(l, m)][k] += G[l, m] - gv[l]                   # the barrel conductance already inside gz is replaced by the reduced star
                    else:
                        GZ[(l, m)][k] += G[l, m]
    return GZ


def _lat_via(th, layer, a_foot):
    """!
    @brief Heat that the source layer sends into the barrels of the vias under the footprint (ring 0), which converges laterally in that layer and heats its rim.
    @param th (L, R) temperatures of the network.
    @param layer Source layer.
    @param a_foot Area of the footprint in m2.
    @return float Heat in W (never negative), weighted by 1 - (area covered by the cells of the vias) / (area of the footprint).
    """
    tot = 0.0
    for (l_a, l_b), g in GZVIA.items():
        if l_a == layer:
            tot += g[0] * (th[layer, 0] - th[l_b, 0])
        elif l_b == layer:
            tot += g[0] * (th[layer, 0] - th[l_a, 0])
    # A sink spread over a disc that covers a share rho2 of the footprint raises the rim of the footprint above its mean by (1 - rho2) times the value of a point sink
    return max(tot, 0.0) * max(1.0 - ACL0[0] / a_foot, 0.0)


_OLD_LOOP = '''            if l < nb - 1:
                for k in range(R):
                    couple(l * R + k, (l + 1) * R + k, gz[l, k])
'''
_NEW_LOOP = '''if False:
    pass
'''
_OLD_LINKS = "        for a, b, g in links:\n            for k in range(R):\n                if g[k] > 0:\n"
_NEW_LINKS = (
    "        for (l_a, l_b), g_ab in GZ.items():\n"
    "            for k in range(R):\n"
    "                if g_ab[k] != 0.0:\n"
    "                    couple(l_a * R + k, l_b * R + k, g_ab[k])\n") + _OLD_LINKS
_OLD_LOSS = '''            if l < nb - 1:
                loss += gz[l, 0] * (th[l, 0] - th[l + 1, 0])
            if l > 0 and l < nb:
                loss += gz[l - 1, 0] * (th[l, 0] - th[l - 1, 0])
'''
_NEW_LOSS = '''            for (l_a, l_b), g_ab in GZ.items():
                if l_a == l:
                    loss += g_ab[0] * (th[l, 0] - th[l_b, 0])
                elif l_b == l:
                    loss += g_ab[0] * (th[l, 0] - th[l_a, 0])
'''


def _compile_heater_network():
    """!
    @brief Compile the copy of `lumped._heater_network` with the three replacements.
    @return The new function.
    @throws RuntimeError If a block to replace is not found (the program changed).
    """
    from pcbthermal import lumped
    src = textwrap.dedent(inspect.getsource(lumped._heater_network))
    # The solve closure indents the loop block by 8 spaces after dedent of the function: normalise by locating the old text with its real indentation
    def swap(src, old, new, indent_old):
        pad = " " * indent_old
        old_i = "".join(pad + ln if ln.strip() else ln for ln in textwrap.dedent(old).splitlines(True))
        if old_i not in src:
            raise RuntimeError("block not found in lumped._heater_network: " + old.strip().splitlines()[0])
        new_i = "".join(pad + ln if ln.strip() else ln for ln in textwrap.dedent(new).splitlines(True))
        return src.replace(old_i, new_i, 1)

    src = swap(src, _OLD_LOOP, _NEW_LOOP, 12)
    if _OLD_LINKS not in src:
        raise RuntimeError("links loop not found")
    src = src.replace(_OLD_LINKS, _NEW_LINKS, 1)
    src = swap(src, _OLD_LOSS, _NEW_LOSS, 12)
    anchor = "    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)\n"
    if anchor not in src:
        raise RuntimeError("anchor not found")
    src = src.replace(anchor, _SETUP.lstrip("\n") + anchor, 1)
    if OPTIONS["peak"]:
        lat_line = "    lat = (th[layer, 0] - th[layer, 1]) / link_resistance(layer, 0) if R > 1 else 0.0\n"
        if lat_line not in src:
            raise RuntimeError("lateral flow line not found")
        src = src.replace(lat_line, lat_line + "    lat = lat + _lat_via(th, layer, A_foot)\n", 1)
    ns = {}
    exec(compile(src, "<patched lumped._heater_network>", "exec"), lumped.__dict__, ns)
    lumped._via_couplings = _via_couplings
    lumped._lat_via = _lat_via
    return ns["_heater_network"]


@contextlib.contextmanager
def patched(mode="krogh", eta=cr.ETA, c3=0.75, cell="ring", cap_lambda=1.0, cluster=False, scale=1.0, macro_scale=1.0, peak=False, macro_cap=0.0):
    """!
    @brief Install the Lumped model with the constriction of the vias; restore the original on exit.
    @param mode "off", "krogh", "log" or "bessel" (see the module header).
    @param eta r_t / r_v.
    @param c3 Constant of the "log" mode.
    @param cell "ring" or "cap".
    @param cap_lambda Cap of the cell radius in fin lengths ("cap" and "nn").
    @param macro_cap Cap of the macro radius in fin lengths of the sheet (0 = none).
    @param peak True: add to the lateral heat of the peak term the heat that the source layer sends into the barrels under the footprint.
    @param macro_scale Factor on the cluster (macro) constriction only (study knob).
    @param scale Factor on every constriction resistance (study knob).
    @param cluster True: add the constriction of the cluster of vias of a ring as one disc (macro level).
    @return Context manager. The Problem must be registered with `set_problem` before `lumped.solve_steady` is called (`run` does both).
    """
    from pcbthermal import lumped
    old_net = lumped._heater_network
    old_solve = lumped.solve_steady
    old_opts = dict(OPTIONS)
    OPTIONS.update(mode=mode, eta=eta, c3=c3, cell=cell, cap_lambda=cap_lambda, cluster=cluster, scale=scale, macro_scale=macro_scale, peak=peak, macro_cap=macro_cap)
    try:
        lumped._heater_network = _compile_heater_network()

        def solve_steady(problem, rings=10, cell_mm=1.0):
            PROBLEM["p"] = problem
            return old_solve(problem, rings, cell_mm)
        lumped.solve_steady = solve_steady
        yield
    finally:
        lumped._heater_network = old_net
        lumped.solve_steady = old_solve
        OPTIONS.clear()
        OPTIONS.update(old_opts)
        PROBLEM["p"] = None
        for name in ("_via_couplings", "_lat_via"):
            if hasattr(lumped, name):
                delattr(lumped, name)
