#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief The canonical edge boards of the investigation built for the finite-element solver `hexfem` (imports nothing of pcbthermal).
@details One generic builder `build` (plan mesh from break points and fine zones, copper layers and FR-4 gaps as bricks, film on the walls, optional copper-filled via by the area
         share of its disc in each brick) and four wrappers: `strong_edge` (10 x 10 mm, four copper layers, half domain, optional via, optional copper inset), `square`
         (20 mm square, two layers, quarter domain, copper to the wall or inset), `t_outline` (the T of the edge-film study, half domain, brick mask) and `slab_1d` (closed-form check).
         Lengths are mm in the arguments and metres inside the model. Physics as the finite-volume truths of the repository: copper 385 W/mK, 35 um; FR-4 0.3 W/mK (strong-edge
         board, both ways) or 0.9 in the plane and 0.3 through it (the edge-film boards); the film `h_side` acts on every wall slab, copper and laminate.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hexfem                                                                  # noqa: E402

K_CU, T_CU = 385.0, 35e-6


def disc_share(xc, yc, cx, cy, r, hx, hy, sub=16):
    """!
    @brief Area share of a disc in every plan brick (supersampled).
    @param xc Brick centres in x (m), 1D.
    @param yc Brick centres in y (m), 1D.
    @param cx Disc centre x (m).
    @param cy Disc centre y (m).
    @param r Disc radius (m).
    @param hx Brick sizes in x (m), 1D.
    @param hy Brick sizes in y (m), 1D.
    @param sub Supersampling per side.
    @return numpy.ndarray (ny, nx) of shares.
    """
    off = (np.arange(sub) + 0.5) / sub - 0.5
    share = np.zeros((yc.size, xc.size))
    for oy in off:
        for ox in off:
            x = xc[None, :] + ox * hx[None, :]
            y = yc[:, None] + oy * hy[:, None]
            share += ((x - cx) ** 2 + (y - cy) ** 2 <= r * r)
    return share / (sub * sub)


def build(xn, yn, layers, board_t, copper, heater, power, h_top, h_bottom, h_side, k_fr4_xy, k_fr4_z, n_gap, active=None, via=None, h_cut=0.0, gap_ratio=1.4):
    """!
    @brief Build the finite-element model of a PCB-like stack.
    @param xn Plan node coordinates in x (m).
    @param yn Plan node coordinates in y (m).
    @param layers Copper layers (at least 2).
    @param board_t Board thickness in m (copper layers included).
    @param copper Function (layer index, xc (m), yc (m) meshgrid arrays) -> boolean array of the copper on that layer.
    @param heater Rectangle (x0, y0, x1, y1) in m on the top copper layer; its edges must be nodes. Its heat is `power` over the part inside the domain.
    @param power Heat generated in the modelled domain in W.
    @param h_top Top film W/m2K.
    @param h_bottom Bottom film W/m2K.
    @param h_side Film of the four box sides (x-low, x-high, y-low, y-high), W/m2K; 0 for a symmetry plane.
    @param k_fr4_xy FR-4 conductivity in the plane.
    @param k_fr4_z FR-4 conductivity through the thickness.
    @param n_gap Bricks per laminate gap.
    @param active Optional boolean (ny, nx) mask of the plan bricks that belong to the board (an outline); the film `h_cut` acts on its walls.
    @param via Optional (cx, cy, r) in m, a solid copper cylinder through every layer (conductivity mixed by area share).
    @param h_cut Film on the walls of the mask inside the box, W/m2K.
    @param gap_ratio Brick growth ratio towards the middle of a gap.
    @return Tuple (Model, heater mask (nz, ny, nx), top-copper mask (nz, ny, nx)).
    """
    gap = (board_t - layers * T_CU) / (layers - 1)
    dz, kind = [], []
    for l in range(layers):
        dz.append(T_CU)
        kind.append(("cu", l))
        if l < layers - 1:
            for t in hexfem.graded_gap(gap, n_gap, gap_ratio):
                dz.append(t)
                kind.append(("gap", l))
    zn = np.concatenate([[0.0], np.cumsum(dz)])
    m = hexfem.Model(xn, yn, zn)
    xc, yc = 0.5 * (m.xn[1:] + m.xn[:-1]), 0.5 * (m.yn[1:] + m.yn[:-1])
    X, Y = np.meshgrid(xc, yc)
    hx, hy = np.diff(m.xn), np.diff(m.yn)
    share = disc_share(xc, yc, *via[:2], via[2], hx, hy) if via else None
    for z, kd in enumerate(kind):
        if kd[0] == "cu":
            cu = copper(kd[1], X, Y)
            m.kxy[z] = np.where(cu, K_CU, k_fr4_xy)
            m.kz[z] = np.where(cu, K_CU, k_fr4_z)
        else:
            m.kxy[z] = k_fr4_xy
            m.kz[z] = k_fr4_z
        if via:
            m.kxy[z] = share * K_CU + (1 - share) * m.kxy[z]
            m.kz[z] = share * K_CU + (1 - share) * m.kz[z]
    if active is not None:
        m.active[:] = active[None, :, :]
    m.h_top, m.h_bottom, m.h_wall, m.h_cut = h_top, h_bottom, tuple(h_side), h_cut
    hm = (X > heater[0]) & (X < heater[2]) & (Y > heater[1]) & (Y < heater[3])
    if active is not None:
        hm &= active
    hmask = np.zeros(m.active.shape, bool)
    hmask[0] = hm
    vol = (hx[None, :] * hy[:, None])[hm].sum() * dz[0]
    m.q[0][hm] = power / vol
    topcu = np.zeros(m.active.shape, bool)
    topcu[0] = m.kxy[0] >= 0.5 * K_CU
    return m, hmask, topcu


def _axes(wx, wy, bx, by, zx, zy, hf, growth, hmax):
    """!
    @brief Plan node coordinates (m) from break points and fine zones given in mm.
    @param wx Length in x, mm.
    @param wy Length in y, mm.
    @param bx Break points in x, mm.
    @param by Break points in y, mm.
    @param zx Fine zones in x, mm.
    @param zy Fine zones in y, mm.
    @param hf Fine size, mm.
    @param growth Growth of the size with the distance from a zone.
    @param hmax Largest size, mm.
    @return Tuple (xn, yn) in m.
    """
    xn = hexfem.grid1d(wx, bx, zx, hf, growth, hmax)
    yn = hexfem.grid1d(wy, by, zy, hf, growth, hmax)
    return xn * 1e-3, yn * 1e-3


def strong_edge(h_side, hf=0.1, n_gap=6, via_dist=None, inset=0.0, growth=1.3, hmax=0.5, via_r=0.15, power=0.5):
    """!
    @brief The strong-edge board of `research/strong-edge-laminate`: 10 x 10 mm, four full copper layers, gaps 0.487 mm, h_top 10, h_bottom 200, a 3 x 2 mm source at (1..4, 4..6) mm.
    @details Half domain y <= 5 mm (the plane y = 5 mm is insulated by symmetry); the walls x = 0, x = 10 and y = 0 carry `h_side` on every slab. The via, when given, is a copper cylinder
             of radius `via_r` mm at `via_dist` mm from the wall x = 10 on y = 5 mm.
    @param h_side Wall film, W/m2K.
    @param hf Fine plan size near the walls, the source and the via, mm.
    @param n_gap Bricks per gap.
    @param via_dist Distance of the via centre from the wall x = 10 mm, None for no via.
    @param inset Copper inset from the walls in mm.
    @param growth Growth of the size with the distance from a fine zone.
    @param hmax Largest plan size in mm.
    @param via_r Drill radius in mm.
    @param power Source power of the whole board in W.
    @return Tuple (Model, heater mask, top copper mask).
    """
    W = 10.0
    bx, by = [0, 1, 4, W], [0, 4, 5]
    zx = [(0, 0.6), (W - 0.6, W), (1, 4)]
    zy = [(0, 0.6), (3.4, 5)]
    via = None
    if via_dist is not None:
        cx = W - via_dist
        bx += [cx - via_r, cx, cx + via_r]
        by += [5 - via_r]
        zx.append((cx - 0.4, cx + 0.4))
        zy.append((5 - 0.4, 5))
        via = (cx * 1e-3, 5e-3, via_r * 1e-3)
    xn, yn = _axes(W, 5.0, bx, by, zx, zy, hf, growth, hmax)

    def copper(l, X, Y):
        """!
        @brief Copper of a layer.
        @param l Layer index.
        @param X Brick centres x.
        @param Y Brick centres y.
        @return bool array.
        """
        if inset <= 0:
            return np.ones_like(X, bool)
        return (X > inset * 1e-3) & (X < (W - inset) * 1e-3) & (Y > inset * 1e-3)
    return build(xn, yn, 4, 1.6e-3, copper, (1e-3, 4e-3, 4e-3, 6e-3), 0.5 * power, 10.0, 200.0, (h_side, h_side, h_side, 0.0), 0.3, 0.3, n_gap, via=via)


def square(h_side, inset=0.0, hf=0.2, n_gap=6, growth=1.3, hmax=0.8, layers=2, side=20.0, heater=4.0):
    """!
    @brief The 20 mm square of the edge-film study (two copper layers, 1 W in a 4 mm square at the centre of the top layer), quarter domain with the two symmetry planes insulated.
    @param h_side Wall film W/m2K.
    @param inset Copper inset from the wall in mm (0: copper to the wall).
    @param hf Fine plan size in mm.
    @param n_gap Bricks per gap.
    @param growth Growth of the size with the distance from a fine zone.
    @param hmax Largest plan size in mm.
    @param layers Copper layers.
    @param side Board side in mm.
    @param heater Heater side in mm.
    @return Tuple (Model, heater mask, top copper mask).
    """
    h = side / 2
    lim = h - inset
    bx = [heater / 2, lim, h]
    zx = [(0, heater / 2 + 0.4), (lim - 0.5, h)]
    xn, yn = _axes(h, h, bx, bx, zx, zx, hf, growth, hmax)

    def copper(l, X, Y):
        """!
        @brief Copper of a layer.
        @param l Layer index.
        @param X Brick centres x.
        @param Y Brick centres y.
        @return bool array.
        """
        return (X < lim * 1e-3) & (Y < lim * 1e-3)
    return build(xn, yn, layers, 1.6e-3, copper, (0.0, 0.0, heater / 2 * 1e-3, heater / 2 * 1e-3), 0.25, 10.0, 10.0, (0.0, h_side, 0.0, h_side), 0.9, 0.3, n_gap)


T_OUT = [[0, 20], [20, 20], [20, 14], [13.2, 14], [13.2, 0], [6.8, 0], [6.8, 14], [0, 14]]


def t_outline(h_side, hf=0.2, n_gap=6, growth=1.3, hmax=0.8):
    """!
    @brief The T outline with copper to the wall (`T_wall` of `research/imported-copper-edge-film`): bar 20 x 6 mm, stem 6.4 mm wide, 2 layers, heater 2.4 x 2.4 mm at (8.8..11.2, 16..18.4), 1 W.
    @details Half domain x >= 10 mm (the board and the heater are symmetric about x = 10 mm); the wall is every face between a brick of the T and one outside it, and the box sides x = 20 and y = 0 / 20.
    @param h_side Wall film W/m2K.
    @param hf Fine plan size in mm.
    @param n_gap Bricks per gap.
    @param growth Growth of the size with the distance from a fine zone.
    @param hmax Largest plan size in mm.
    @return Tuple (Model, heater mask, top copper mask).
    """
    bx = [10, 11.2, 13.2, 20]
    by = [0, 14, 16, 18.4, 20]
    zx = [(10, 11.6), (12.6, 14), (19.4, 20)]
    zy = [(0, 0.6), (13.4, 14.6), (15.6, 18.8), (19.4, 20)]
    xn, yn = hexfem.grid1d(10.0, [b - 10 for b in bx if b > 10], [(a - 10, b - 10) for a, b in zx], hf, growth, hmax), hexfem.grid1d(20.0, by, zy, hf, growth, hmax)
    xn, yn = (xn + 10.0) * 1e-3, yn * 1e-3
    xc, yc = 0.5 * (xn[1:] + xn[:-1]), 0.5 * (yn[1:] + yn[:-1])
    X, Y = np.meshgrid(xc * 1e3, yc * 1e3)
    active = ((Y > 14) | (X < 13.2)) & (Y < 20) & (X > 10)
    return build(xn, yn, 2, 1.6e-3, lambda l, X_, Y_: np.ones_like(X_, bool), (10e-3, 16e-3, 11.2e-3, 18.4e-3), 0.5, 10.0, 10.0, (0.0, h_side, h_side, h_side), 0.9, 0.3, n_gap,
                 active=active, h_cut=h_side)


def t_outline_full(h_side, hf=0.4, n_gap=4, growth=1.3, hmax=0.8):
    """!
    @brief The same T board on the whole domain (no symmetry plane): the test of the half-domain `t_outline`.
    @param h_side Wall film W/m2K.
    @param hf Fine plan size in mm.
    @param n_gap Bricks per gap.
    @param growth Growth of the size with the distance from a fine zone.
    @param hmax Largest plan size in mm.
    @return Tuple (Model, heater mask, top copper mask) with 1 W.
    """
    zx = [(0, 0.6), (6.2, 7.4), (8.2, 11.8), (12.6, 14), (19.4, 20)]
    zy = [(0, 0.6), (13.4, 14.6), (15.6, 18.8), (19.4, 20)]
    xn = hexfem.grid1d(20.0, [6.8, 8.8, 11.2, 13.2], zx, hf, growth, hmax) * 1e-3
    yn = hexfem.grid1d(20.0, [0, 14, 16, 18.4, 20], zy, hf, growth, hmax) * 1e-3
    X, Y = np.meshgrid(0.5 * (xn[1:] + xn[:-1]) * 1e3, 0.5 * (yn[1:] + yn[:-1]) * 1e3)
    active = (Y > 14) | ((X > 6.8) & (X < 13.2))
    return build(xn, yn, 2, 1.6e-3, lambda l, X_, Y_: np.ones_like(X_, bool), (8.8e-3, 16e-3, 11.2e-3, 18.4e-3), 1.0, 10.0, 10.0, (h_side,) * 4, 0.9, 0.3, n_gap, active=active, h_cut=h_side)


def read_out(m, hmask, topcu, res):
    """!
    @brief Heater mean rise, hottest top-copper rise and heat balance of a solve.
    @param m The Model.
    @param hmask Heater mask.
    @param topcu Top copper mask.
    @param res Result of `Model.solve`.
    @return dict with `mean`, `tmax`, `balance`, `n`, `peak_gb`.
    """
    T = res["T"]
    hx, hy, hz = (np.diff(a) for a in (m.xn, m.yn, m.zn))
    ez, ey, ex = np.nonzero(topcu & m.active)
    mean8 = sum(T[ez + dz, ey + dy, ex + dx] for dz in (0, 1) for dy in (0, 1) for dx in (0, 1)) / 8.0
    return {"mean": m.brick_mean(T, hmask), "tmax": float(np.nanmax(mean8)), "balance": res.get("balance"), "n": res["n"], "peak_gb": res["peak_gb"]}
