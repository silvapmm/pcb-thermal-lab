#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file placement.py
@brief Tools of the zone-placement study: shifting a board on the raster, the geometry of the zone decision, and candidate core rules applied on a COPY (monkeypatches inside a context manager).
@details `pcbthermal/` is never edited. The boards and the readings (`viastudy.board`, `viastudy.run`) come from the sibling folder `research/lumped-dense-via-group/lib`.
         Candidate rules (`patched(rule=...)`):
         - `program`: nothing patched.
         - `true_core`: cells whose CENTRE is within CORE_R d_nn of a via POSITION (the cell that holds the via is not used).
         - `vote`: the footprint cell is core when at least half of its sub-grid (VOTE_MM, 0.1 mm) lies within CORE_R d_nn of a via position: an area-weighted cell share, not a cell-centre test.
         - `vote_exact_gate`: `vote` plus the coarse core gate of `_heater_network` replaced by the area-weighted core share computed on the sub-grid.
         The exact core share (`exact_share`) is the share of the footprint area within CORE_R d_nn of a via position, on a 0.025 mm sub-grid, with no Lumped raster in it.
"""

import contextlib
import os
import sys

import numpy as np
from scipy import spatial

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DENSE = os.path.join(ROOT, "research", "lumped-dense-via-group", "lib")
for _p in (ROOT, DENSE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import viastudy as v                                                          # noqa: E402,F401
from pcbthermal import lumped                                                 # noqa: E402

VOTE_MM = 0.1      # sub-grid cell of the area vote (mm)
MEMBER_TOL_M = 1e-6   # tolerance of the membership test of a via on the footprint boundary (m)
_OPT = {"member_tol": False}   # switches read by the helpers while a candidate is applied


def shifted(p, dx_mm, dy_mm):
    """!
    @brief Translate every part and every via of a problem by (dx, dy), the board stays where it is.
    @param p Problem (changed in place).
    @param dx_mm Translation along x in mm.
    @param dy_mm Translation along y in mm.
    @return Problem p.
    """
    for h in p.heaters:
        h.polygon = h.polygon + np.array([dx_mm, dy_mm]) * 1e-3
    for x in p.vias:
        x.x += dx_mm * 1e-3
        x.y += dy_mm * 1e-3
    return p


def _group_members(net, cov, vias, g, foot):
    """!
    @brief Members of group g whose cell is in the footprint (the program's rule) and the group's core radius.
    @param net Network or namespace (nx, ny, dx, dy).
    @param cov Footprint coverage.
    @param vias ViaSet or view.
    @param g Group label.
    @param foot Boolean footprint mask.
    @return (indices, radius in m) or (None, None) when fewer than two members.
    """
    mem = np.flatnonzero(vias.group == g)
    inside = []
    tol = MEMBER_TOL_M if _OPT["member_tol"] else 0.0
    for i in mem:
        # With the tolerance a via on the closed boundary of the footprint cells counts (the cell test alone flips with the last bit of a coordinate)
        for ox, oy in ((0.0, 0.0), (tol, 0.0), (-tol, 0.0), (0.0, tol), (0.0, -tol)) if tol else ((0.0, 0.0),):
            cj, ci = int((vias.x[i] + ox) // net.dx), int((vias.y[i] + oy) // net.dy)
            if 0 <= ci < net.ny and 0 <= cj < net.nx and foot[ci, cj]:
                inside.append(i)
                break
    if len(inside) < 2:
        return None, None
    return inside, lumped.CORE_R * float(np.mean([vias.d_nn[i] for i in inside]))


def _share_mask(net, cov, vias, sub_mm, threshold):
    """!
    @brief Cell mask: the share of each footprint cell's sub-grid within the core radius of a via position, thresholded.
    @param net Network or namespace.
    @param cov Footprint coverage (ny, nx).
    @param vias ViaSet or view.
    @param sub_mm Sub-grid cell in mm.
    @param threshold Share of the cell needed to call it core (None: return the share array instead of a mask).
    @return bool array (ny, nx), or float share array when threshold is None, or None when no group.
    """
    if vias is None or len(vias) < 2:
        return None
    foot = cov > 0
    k = max(int(round(net.dx * 1e3 / sub_mm)), 1)
    share = np.zeros(foot.shape)
    any_group = False
    ys, xs = np.nonzero(foot)
    # Sub-grid centres of every footprint cell
    off = (np.arange(k) + 0.5) / k
    for g in np.unique(vias.group):
        inside, r = _group_members(net, cov, vias, g, foot)
        if inside is None:
            continue
        any_group = True
        tree = spatial.cKDTree(np.column_stack([vias.x[inside], vias.y[inside]]))
        sx = ((xs[:, None, None] + off[None, :, None]) * net.dx) + 0 * off[None, None, :]
        sy = ((ys[:, None, None] + off[None, None, :]) * net.dy) + 0 * off[None, :, None]
        d, _ = tree.query(np.column_stack([sx.ravel(), sy.ravel()]))
        s = (d <= r + 1e-12).reshape(len(xs), k, k).mean(axis=(1, 2))
        share[ys, xs] = np.maximum(share[ys, xs], s)
    if not any_group:
        return None
    if threshold is None:
        return share
    core = (share >= threshold) & foot
    return core if core.any() else None


def _centre_mask(net, cov, vias):
    """!
    @brief Cells whose centre is within the core radius of a via position.
    @param net Network or namespace.
    @param cov Footprint coverage.
    @param vias ViaSet or view.
    @return bool array or None.
    """
    if vias is None or len(vias) < 2:
        return None
    foot = cov > 0
    xs = (np.arange(net.nx) + 0.5) * net.dx
    ys = (np.arange(net.ny) + 0.5) * net.dy
    gx, gy = np.meshgrid(xs, ys)
    core = np.zeros(foot.shape, bool)
    pts = np.column_stack([gx[foot], gy[foot]])
    idx = np.flatnonzero(foot.ravel())
    for g in np.unique(vias.group):
        inside, r = _group_members(net, cov, vias, g, foot)
        if inside is None:
            continue
        d, _ = spatial.cKDTree(np.column_stack([vias.x[inside], vias.y[inside]])).query(pts)
        core.ravel()[idx[d <= r + 1e-12]] = True
    return core if core.any() else None


def _vote(net, cov, vias):
    """!
    @brief `vote`: a cell is core when at least half of its 0.1 mm sub-grid is within the core radius of a via position.
    @param net Network or namespace.
    @param cov Footprint coverage.
    @param vias ViaSet or view.
    @return bool array or None.
    """
    return _share_mask(net, cov, vias, VOTE_MM, 0.5)


def exact_share(net, cov, vias, sub_mm=0.025):
    """!
    @brief Share of the footprint area (weighted by coverage) within the core radius of a via position, on a fine sub-grid: the raster-free value.
    @param net Network or namespace.
    @param cov Footprint coverage.
    @param vias ViaSet or view.
    @param sub_mm Sub-grid cell in mm.
    @return float share, 0 when there is no group.
    """
    s = _share_mask(net, cov, vias, sub_mm, None)
    return 0.0 if s is None else float((s * cov).sum() / cov.sum())


def _weighted_share(core, cov):
    """!
    @brief Share of the footprint covered by the core, weighted by the footprint coverage (a cell touched by a sliver of the part counts by its share, not whole).
    @param core bool array (ny, nx).
    @param cov Footprint coverage (ny, nx).
    @return float share in [0, 1].
    """
    return float((core * cov).sum() / cov.sum())


def _vote_fine_share(net, cov, vias):
    """!
    @brief Replacement of `lumped._fine_core_share`: the area-weighted share from the 0.1 mm vote on the coarse cells, with no raster in it other than the sub-grid.
    @param net Network or namespace.
    @param cov Footprint coverage.
    @param vias ViaSet.
    @return float share.
    """
    s = _share_mask(net, cov, vias, VOTE_MM, None)
    return 0.0 if s is None else float((s * cov).sum() / cov.sum())


@contextlib.contextmanager
def patched(mask="cell", member_tol=False, weighted_gate=False, fine="program", max_core=None, zone_cell=None):
    """!
    @brief Apply a candidate rule for the duration of a with block (restored on exit).
    @param mask 'cell' (the program: via moved to its cell), 'centre' (cell centre against via positions) or 'vote' (0.1 mm sub-grid vote against via positions).
    @param member_tol True: a via on the closed boundary of the footprint cells is a member (`MEMBER_TOL_M`).
    @param weighted_gate True: the grid gate of `_heater_network` (core cells against touched cells) is replaced by the coverage-weighted share.
    @param fine 'program' or 'vote': the fine share of `will_be_zoned` as the program, or the vote-based area share.
    @param max_core New MAX_CORE or None.
    @param zone_cell New ZONE_CELL_MM or None (the default argument of will_be_zoned is patched too).
    @return None (context manager).
    """
    import inspect
    saved = (lumped._core_mask, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped.will_be_zoned.__defaults__, lumped._fine_core_share, lumped._heater_network, dict(_OPT))
    try:
        _OPT["member_tol"] = member_tol
        if mask == "centre":
            lumped._core_mask = _centre_mask
        elif mask == "vote":
            lumped._core_mask = _vote
        elif mask != "cell":
            raise ValueError(mask)
        if member_tol and mask == "cell":
            raise ValueError("member_tol needs mask 'centre' or 'vote'")
        if fine == "vote":
            lumped._fine_core_share = _vote_fine_share
        if weighted_gate:
            src = inspect.getsource(saved[5])
            old = "if n_core < n_foot and n_core <= MAX_CORE * n_foot and"
            assert old in src
            src = src.replace(old, "if _wshare(core, cov) < 1.0 - 1e-9 and _wshare(core, cov) <= MAX_CORE and")
            lumped._wshare = _weighted_share
            ns = lumped.__dict__
            exec(compile(src, "<patched _heater_network>", "exec"), ns)
        if max_core is not None:
            lumped.MAX_CORE = max_core
        if zone_cell is not None:
            lumped.ZONE_CELL_MM = zone_cell
            d = list(saved[3])
            d[0] = zone_cell
            lumped.will_be_zoned.__defaults__ = tuple(d)
        yield
    finally:
        (lumped._core_mask, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped.will_be_zoned.__defaults__, lumped._fine_core_share, lumped._heater_network, opt) = saved
        _OPT.update(opt)
        lumped.__dict__.pop("_wshare", None)


def geometry(p, k=0, cell=0.5):
    """!
    @brief The geometry of the zone decision of heater k at one placement: counts on the Lumped raster, the fine share the program uses, the exact share, the decision.
    @param p Problem.
    @param k Heater index.
    @param cell Lumped raster in mm.
    @return dict n_foot, n_core, share_coarse, share_fine, share_exact, zoned (bool, will_be_zoned), mask (bool array), cov.
    """
    from pcbthermal import viaconstriction
    from pcbthermal.lumped import Network
    b = p.board
    nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    h = p.heaters[k]
    cov = lumped._footprint_coverage(net, h)
    vs = viaconstriction.ViaSet(p)
    core = lumped._core_mask(net, cov, vs)
    n_foot = int((cov > 0).sum())
    n_core = 0 if core is None else int(core.sum())
    return {"n_foot": n_foot, "n_core": n_core, "share_coarse": n_core / n_foot, "share_fine": lumped._fine_core_share(net, cov, vs),
            "share_exact": exact_share(net, cov, vs), "zoned": bool(lumped.will_be_zoned(p, h, vias=vs)), "mask": core, "cov": cov, "net": net}
