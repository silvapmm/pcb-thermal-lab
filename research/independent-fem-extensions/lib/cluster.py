#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cluster.py
@brief The board of study 2: a part (6 x 6 or 4 x 4 mm) over a 4 x 4 cluster of hollow resin-filled vias (0.3 mm drill, 0.8 mm pitch) on a 20 x 20 mm four-layer board,
       with a 1 mm aluminium plate under it through a 0.1 mm interface, as a quarter-domain finite-element `stack_ext.Stack`.
@details Variant 'A' is the problem the program receives: the part is a uniform volumetric source in the top copper over its footprint and the top face convects under it.
         Variant 'B' resolves the part: a 0.2 mm copper tab with the source in its volume over 0.1 mm of solder (k 50 W/mK); no film on the board under the tab, films on
         the tab top and sides. The board is the quarter [0, 10] x [0, 10] mm of the 20 mm board (x, y = 0 are the symmetry planes), so the cluster centres are at 0.4 and 1.2 mm.
         `rim=True` ends the copper of layer 2 on the line x = 1.2 mm through the column of vias (the copper exists for x > 1.2 mm only).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import board                                                            # noqa: E402
import cases                                                            # noqa: E402
import mesh2d                                                           # noqa: E402
import stack_ext                                                        # noqa: E402

MM = 1e-3
K_CU, K_XY, K_Z = 385.0, 0.9, 0.3
RC_CU, RC_FR4, RC_AL, RC_SOLDER = 8960 * 385.0, 1850 * 900.0, 2.44e6, 7400 * 220.0
VIAS = [(0.4, 0.4), (1.2, 0.4), (0.4, 1.2), (1.2, 1.2)]               # quarter of the 4 x 4 cluster at 0.8 mm pitch (mm)


def plan_mesh(hf, tab_mm=6.0, hmax=0.5, growth=1.3, n_side=8, half_win=0.4, radii_mm=(0.125, 0.1333333, 0.1416667, 0.15)):
    """!
    @brief The quarter plan: graded tensor axes with the tab edges as mesh lines and an O-grid patch (rings across the 25 um wall) at every via of the quarter cluster.
    @param hf Fine plan size in mm.
    @param tab_mm Part side in mm (6 or 4).
    @param hmax Largest plan size in mm.
    @param growth Size growth with the distance from a fine zone.
    @param n_side Intervals per via window side.
    @param half_win Half side of the via window in mm.
    @param radii_mm Circle levels of the barrel in mm.
    @return Quad2D.
    """
    t = tab_mm / 2.0
    br = sorted({3.0, 2.0, t})
    zones = [(0.0, 1.9), (t - 0.4, t + 0.4)]
    xn = cases.axis(10.0, br, zones, hf, growth, hmax)
    for x0 in (0.0, 0.8):
        xn = mesh2d.uniform_window(xn, x0 * MM, (x0 + 0.8) * MM, n_side)
    plan = mesh2d.tensor(xn, xn)
    radii = [r * MM for r in radii_mm]
    s0 = 0.55 * radii[0] / np.sqrt(2.0)
    for cx, cy in VIAS:
        plan = mesh2d.embed_ogrid(plan, cx * MM, cy * MM, half_win * MM, n_side, radii, s0=s0, n_blend=0, n_inner=1)
    return plan


def build(variant="A", tab_mm=6.0, hf=0.2, rim=False, k_solder=50.0, power=1.0, h=10.0, plate=True, n_wall=3, n_gap=6, plan=None, no_via=False, solder_mm=0.1, tab_mm_thick=0.2, **kw):
    """!
    @brief The finite-element stack of study 2.
    @param variant 'A' (the program's problem) or 'B' (tab and solder resolved).
    @param tab_mm Part side in mm.
    @param hf Fine plan size in mm.
    @param rim True: layer 2 copper only for x > 1.2 mm.
    @param k_solder Solder conductivity, W/mK.
    @param power Part power of the whole board in W (the quarter carries a quarter).
    @param h Film on top, plate bottom, board and plate walls, W/m2K.
    @param plate False: no interface and plate (the board bottom then has the film h).
    @param n_wall Unused (kept for the wall-ring study: pass `radii_mm` through `plan` instead).
    @param n_gap Elements per laminate gap.
    @param plan Prebuilt plan mesh (default `plan_mesh(hf, tab_mm)`).
    @param solder_mm Solder thickness in mm.
    @param tab_mm_thick Tab thickness in mm.
    @param no_via True: the same mesh with the via copper and the resin cores replaced by laminate (the baseline of the via effect).
    @param kw Unused.
    @return Tuple (Stack, dict of handles: footprint mask function, slab indices).
    """
    if plan is None:
        plan = plan_mesh(hf, tab_mm)
    t = tab_mm / 2.0 * MM
    inside = lambda c: (c[:, 0] < t) & (c[:, 1] < t)                     # noqa: E731  the quarter of the part (the quad centroid decides; the edge is a mesh line)
    r_d, r_in = 0.15 * MM, 0.125 * MM
    in_core = np.zeros(plan.centroids().shape[0], bool)
    in_wall = np.zeros_like(in_core)
    cc = plan.centroids()
    for cx, cy in VIAS:
        r = np.hypot(cc[:, 0] - cx * MM, cc[:, 1] - cy * MM)
        in_wall |= (r >= r_in) & (r < r_d)
        in_core |= r < r_in
    if no_via:
        in_wall[:] = False
        in_core[:] = False

    def board_k(copper_mask):
        """!
        @brief kfun of a board slab (copper layer) with the via barrel and core.
        @param copper_mask Callable(centroids) -> bool of the layer's copper.
        @return callable.
        """
        def f(c, idx):
            """!
            @brief Conductivities per quad.
            @param c Centroids.
            @param idx Quad indices.
            @return (kx, kz).
            """
            cu = copper_mask(c) | in_wall
            kx = np.where(cu, K_CU, K_XY)
            kz = np.where(cu, K_CU, K_Z)
            kx = np.where(in_core, 0.3, kx)
            kz = np.where(in_core, 0.3, kz)
            return kx, kz
        return f

    def gap_k(c, idx):
        """!
        @brief Laminate gap with the barrel and core through it.
        @param c Centroids.
        @param idx Quad indices.
        @return (kx, kz).
        """
        kx = np.where(in_wall, K_CU, np.where(in_core, 0.3, K_XY))
        kz = np.where(in_wall, K_CU, np.where(in_core, 0.3, K_Z))
        return kx, kz
    slabs = []
    q_part = power / 4.0
    if variant == "B":
        slabs.append(stack_ext.slab("tab", np.full(2, tab_mm_thick * MM / 2), (K_CU, K_CU), region=inside, h_up=h, h_wall=h, power=q_part, rho_c=RC_CU))
        slabs.append(stack_ext.slab("solder", np.full(2, solder_mm * MM / 2), (k_solder, k_solder), region=inside, h_wall=h, rho_c=RC_SOLDER))
    gap_t = (1.6 * MM - 4 * 35e-6) / 3
    gaps = board.graded_gap(gap_t, n_gap, 1.4)
    for lay in range(4):
        cm = (lambda c: c[:, 0] > 1.2 * MM) if (rim and lay == 1) else (lambda c: np.ones(c.shape[0], bool))
        s = stack_ext.slab(f"cu{lay + 1}", [35e-6], board_k(cm), h_up=h if lay == 0 else 0.0, h_down=(0.0 if plate else h) if lay == 3 else 0.0, h_wall=h, rho_c=RC_CU)
        if lay == 0 and variant == "A":
            s["power"], s["source_region"] = q_part, (lambda c: inside(c) & ~in_core)    # no heat in the resin plug: the program spreads the power over the copper of the footprint
        slabs.append(s)
        if lay < 3:
            slabs.append(stack_ext.slab(f"gap{lay + 1}", gaps, gap_k, h_wall=h, rho_c=RC_FR4))
    if plate:
        slabs.append(stack_ext.slab("interface", np.full(2, 0.05 * MM), (3.0, 3.0), rho_c=0.0))
        slabs.append(stack_ext.slab("plate", board.graded_gap(1.0 * MM, 4, 1.0), (204.0, 204.0), h_down=h, h_wall=h, rho_c=RC_AL))
    st = stack_ext.Stack(plan, slabs, symmetry=[("x", 0.0), ("y", 0.0)])
    names = [s["name"] for s in slabs]
    return st, {"inside": inside, "names": names, "variant": variant}


def readout(st, res, handles, tab_mm):
    """!
    @brief Footprint mean and hottest rise of the part (the top of the tab for B, the top copper over the footprint for A), the plate mean and the board hottest node.
    @param st Stack.
    @param res Result of `Stack.solve`.
    @param handles Handles of `build`.
    @param tab_mm Part side in mm.
    @return dict (K, over the 0 K ambient).
    """
    m, info = res["model"], res["info"]
    T = res["T"]
    c = info["c"]
    qs = np.nonzero(handles["inside"](c))[0]
    first = handles["names"][0]
    faces = st.level_nodes(info, 0, qs)
    tot, area = m.face_integral(T, faces)
    out = {"part_mean": tot / area, "part_max": float(np.nanmax(T[faces])), "balance": res["balance"], "n": res["n"], "solver": res["solver"], "peak_gb": res["peak_gb"]}
    cu1 = handles["names"].index("cu1")
    allq = np.arange(c.shape[0])
    f1 = st.level_nodes(info, cu1, allq)
    out["board_top_max"] = float(np.nanmax(T[f1]))
    if "plate" in handles["names"]:
        pi = handles["names"].index("plate")
        sel = np.nonzero(np.isin(info["sub"][info["s_idx"]], [np.nonzero(info["sub"] == pi)[0]]))[0] if False else np.nonzero(np.isin(info["s_idx"], np.nonzero(info["sub"] == pi)[0]))[0]
        tot, vol = m.volume_integral(T, sel)
        out["plate_mean"] = tot / vol
    return out
