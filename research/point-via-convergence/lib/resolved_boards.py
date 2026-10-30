#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file resolved_boards.py
@brief The test boards of the studies solved by the independent fine-grid layered solver (`sheets2d`), with the vias drawn at their real size, and by the 3D solver `layered3d`.
@details The input is the dictionary of numbers of `program_cases.layer_parameters` (sheet conductances, dielectric conductance per area, films, barrel conductances), so this
         module imports nothing from the program. Boards are uniform (full copper on every layer, insulated edges) and symmetric, so only the quadrant that holds the
         symmetry corner is solved; a via on a symmetry line is cut by it (its disc is clipped to the quadrant and its barrel conductance is the disc area inside).
         * `array_quadrant`: the 3 x 3 array board of research/via-fill (a source of 10 x 10 mm, power per quadrant);
         * `unit_cell`: the p x p periodic cell, a source over the whole top, the via at the centre.
"""

import math
import os
import sys

import numpy as np

import sheets2d

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "solid3d-verification", "lib"))
import layered3d                                                            # noqa: E402  (independent 3D solver, imports nothing from the program)

K_AIR = 0.026                                                                # conductivity of the air in an open bore, W/mK


def _arrays(par, n, dx, vias, rv, origin, quadrant_centre):
    """!
    @brief Sheet, vertical and film arrays of a uniform board with the barrels distributed over their discs.
    @param par Dictionary of layer_parameters.
    @param n Cells per side of the solved quadrant.
    @param dx Cell size in m.
    @param vias List of (x, y, index of the via in par['gv']) with the coordinates in the frame of the quadrant.
    @param rv Via radius in m.
    @param origin Lower edge of cell 0 in m (0).
    @param quadrant_centre Unused marker for documentation.
    @return tuple (S, gz, g_amb).
    """
    L = len(par["S"])
    S = np.broadcast_to(np.asarray(par["S"])[:, None, None], (L, n, n)).copy()
    gz = np.broadcast_to((np.asarray(par["gz_area"]) * dx * dx)[:, None, None], (L - 1, n, n)).copy()
    g_amb = np.zeros((L, n, n))
    g_amb[0] = par["h_top"] * dx * dx
    g_amb[L - 1] += par["h_bottom"] * dx * dx
    for (x, y, k) in vias:
        f = sheets2d.disc_fraction(x, y, rv, dx, n, n, sub=12, origin=origin)
        # The barrel conductance of the whole disc times the share of the disc area that is in the cell (the clipped part of a cut via is simply missing)
        share = f * dx * dx / (math.pi * rv * rv)
        for l in range(L - 1):
            gz[l] += par["gv"][k][l] * share
    return S, gz, g_amb


def array_quadrant(par, dx, power, source_half, extra_vias=None):
    """!
    @brief Maximum rise of the via-array board of research/via-fill by the fine-grid layered solver (quadrant of the symmetric board).
    @param par layer_parameters of the program board (its vias are the 3 x 3 array).
    @param dx Cell size in m (must divide half the width and the half-width of the source).
    @param power Total power of the source in W.
    @param source_half Half side of the square source in m.
    @param extra_vias Unused.
    @return float Maximum rise over the ambient in K (top layer).
    """
    half = par["width"] / 2
    n = int(round(half / dx))
    cx = half
    vias = []
    for k, (x, y) in enumerate(par["xy"]):
        if x <= cx + 1e-9 and y <= cx + 1e-9:
            vias.append((x, y, k))                                     # the vias of the quadrant, some on the symmetry lines (clipped by the grid)
    # A via on a symmetry line counts only once for the half that is in the quadrant: the clipped disc gives it
    S, gz, g_amb = _arrays(par, n, dx, vias, par["r_via"][0], 0.0, None)
    L = len(par["S"])
    Q = np.zeros((L, n, n))
    j0 = int(round((cx - source_half) / dx))
    Q[0, j0:, j0:] = power / 4 / ((n - j0) ** 2)
    T = sheets2d.solve(S, gz, g_amb, Q, dx)
    return float(T.max())


def unit_cell(par, dx, power, quarter=True):
    """!
    @brief Maximum rise of the periodic unit cell (source over the whole top, via at the centre) by the fine-grid layered solver (quadrant).
    @param par layer_parameters of the program unit-cell board (one via at its centre).
    @param dx Cell size in m (must divide half the pitch).
    @param power Total power in W.
    @param quarter True: solve the quadrant [0, p/2]^2 with the via at the corner.
    @return float Maximum rise in K.
    """
    half = par["width"] / 2
    n = int(round(half / dx))
    S, gz, g_amb = _arrays(par, n, dx, [(half, half, 0)], par["r_via"][0], 0.0, None)
    L = len(par["S"])
    Q = np.zeros((L, n, n))
    Q[0] = power / 4 / (n * n)
    T = sheets2d.solve(S, gz, g_amb, Q, dx)
    return float(T.max())


def barrel_fractions(vias, par, dx, n, sub=20):
    """!
    @brief Area fractions of copper (the plated ring) and of the core of every via in every cell of a quadrant, for the 3D solver (the barrel drawn at its real size).
    @param vias List of (x, y, k) in the frame of the quadrant (k indexes par['r_via'], par['fill_k']).
    @param par layer_parameters.
    @param dx Cell size in m.
    @param n Cells per side.
    @param sub Samples per cell side.
    @return tuple (f_ring, f_core) arrays (n, n) of the share of each cell that is copper of the barrel / its core, with the exact areas conserved per via.
    """
    f_ring, f_core = np.zeros((n, n)), np.zeros((n, n))
    s = (np.arange(sub) + 0.5) / sub
    xs = ((np.arange(n)[:, None] + s[None, :]) * dx).ravel()
    X, Y = np.meshgrid(xs, xs)
    for (x, y, k) in vias:
        r_o = par["r_via"][k]
        r_i = r_o - par["plating"]
        rr = np.hypot(X - x, Y - y)
        ring = ((rr <= r_o) & (rr > r_i)).reshape(n, sub, n, sub).mean(axis=(1, 3))
        core = (rr <= r_i).reshape(n, sub, n, sub).mean(axis=(1, 3))
        # Clip at the symmetry lines: the share of the via inside the quadrant is whatever the grid holds; no renormalisation (the cut part is simply missing)
        f_ring += ring
        f_core += core
    return f_ring, f_core


def board_3d(par, dx, vias, quadrant_n, power_rect, power, n_sub=4, h_top=None):
    """!
    @brief Maximum top rise of a uniform board solved in 3D with the barrels drawn at their real size (quadrant, insulated sides).
    @param par layer_parameters (holds the gap thickness, conductivities, films, fill conductivity).
    @param dx Cell size in m.
    @param vias List of (x, y, k) in the frame of the quadrant.
    @param quadrant_n Cells per side of the quadrant.
    @param power_rect Source rectangle (x0, y0, x1, y1) in m in the frame of the quadrant.
    @param power Heat flowing into the rectangle in W (the share in the quadrant).
    @param n_sub Sub-slabs per dielectric gap.
    @param h_top Top film coefficient in W/m2K (default: the one in par).
    @return float Maximum rise of the top layer in K.
    """
    n = quadrant_n
    f_ring, f_core = barrel_fractions(vias, par, dx, n)
    fill = par["fill_k"][0]
    k_core = fill if fill > 0 else K_AIR
    k_gap = f_ring * par["k_cu"] + f_core * k_core + (1 - f_ring - f_core) * par["k_gap"]
    plane = np.full((n, n), par["k_cu"])                                       # the plane is whole, as in the program
    slabs = []
    L = len(par["S"])
    for layer in range(L):
        slabs.append((par["t_cu"], plane, 1))
        if layer < L - 1:
            slabs.append((float(par["d"][layer]), k_gap, n_sub))
    res = layered3d.solve(dx, n, n, slabs, power_rect, power, par["h_top"] if h_top is None else h_top, par["h_bottom"], film_under_source=True)
    return float(res["T"][0].max())


def unit_cell_3d(par, dx, power, n_sub=4):
    """!
    @brief The periodic unit cell in 3D (quadrant, via at the corner, source over the whole top).
    @param par layer_parameters of the unit-cell board.
    @param dx Cell size in m (must divide half the pitch).
    @param power Total power in W.
    @param n_sub Sub-slabs per gap.
    @return float Maximum rise in K.
    """
    half = par["width"] / 2
    n = int(round(half / dx))
    return board_3d(par, dx, [(half, half, 0)], n, (0, 0, half, half), power / 4, n_sub)


def array_3d(par, dx, power, source_half, n_sub=4):
    """!
    @brief The 3 x 3 array board in 3D (quadrant).
    @param par layer_parameters of the array board.
    @param dx Cell size in m.
    @param power Total power in W.
    @param source_half Half side of the square source in m.
    @param n_sub Sub-slabs per gap.
    @return float Maximum rise in K.
    """
    half = par["width"] / 2
    n = int(round(half / dx))
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"]) if x <= half + 1e-9 and y <= half + 1e-9]
    return board_3d(par, dx, vias, n, (half - source_half, half - source_half, half, half), power / 4, n_sub)


def full_board_2d(par, dx, vias, power, rect=None):
    """!
    @brief Maximum rise of a whole uniform board (insulated edges) by the fine-grid layered solver, source uniform over a rectangle of the top (default: the whole top).
    @param par layer_parameters.
    @param dx Cell size in m (must divide the width and height).
    @param vias List of (x, y, k).
    @param power Total power in W.
    @param rect Source rectangle (x0, y0, x1, y1) in m (default the whole board).
    @return float Maximum rise in K.
    """
    nx, ny = int(round(par["width"] / dx)), int(round(par["height"] / dx))
    assert nx == ny, "square boards only"
    S, gz, g_amb = _arrays(par, nx, dx, vias, par["r_via"][0], 0.0, None)
    L = len(par["S"])
    Q = np.zeros((L, ny, nx))
    x0, y0, x1, y1 = rect if rect is not None else (0.0, 0.0, par["width"], par["height"])
    j0, j1, i0, i1 = int(round(x0 / dx)), int(round(x1 / dx)), int(round(y0 / dx)), int(round(y1 / dx))
    Q[0, i0:i1, j0:j1] = power / ((i1 - i0) * (j1 - j0))
    return float(sheets2d.solve(S, gz, g_amb, Q, dx).max())


def full_board_3d(par, dx, vias, power, rect=None, n_sub=4):
    """!
    @brief The same board in 3D with the barrels drawn at their real size.
    @param par layer_parameters.
    @param dx Cell size in m.
    @param vias List of (x, y, k).
    @param power Total power in W.
    @param rect Source rectangle in m (default the whole top).
    @param n_sub Sub-slabs per gap.
    @return float Maximum rise in K.
    """
    n = int(round(par["width"] / dx))
    r = rect if rect is not None else (0.0, 0.0, par["width"], par["height"])
    return board_3d(par, dx, vias, n, r, power, n_sub)
