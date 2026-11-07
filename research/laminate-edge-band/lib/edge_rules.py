#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file edge_rules.py
@brief Prototypes of the rules that give the laminate its share of the edge film in the FVM and FDM, applied to a copy of two functions of `pcbthermal.laminate` for the duration of a run.
@details **The defect (A16).** On a cell with copper in every layer the rule makes no laminate nodes, so the whole slab of the node (copper plus half of each adjacent gap) puts its edge film
         `h_side x slab x edge` on the copper node, at the copper temperature. The laminate at the edge is cooler than the copper (it is fed through `k_z`), so the film is overstated and the
         board reads cold. Two remedies are written here.

         * **band**: the cells within `width x d` of the board edge (the cells the outline crosses, grown) get the interior nodes of the gap even where the copper is full
           (`laminate.plan_gaps` replaced by one that ORs the band into `flagged`). Costs unknowns, converges as 1 / n.
         * **eta**: the laminate share of the edge conductance of an unflagged cell is multiplied by the efficiency of a laminate half-gap of thickness d / 2 held at the copper temperature on one
           face (symmetric about the middle of the gap) and losing heat through a film h_s on its edge: separation of variables, modes sin(lambda_n z), lambda_n = (2n-1) pi / d, decay
           mu_n = lambda_n sqrt(k_z / k_xy), eta = sum_n 8 / ((2n-1)^2 pi^2) * a_n / (h_s + a_n), a_n = k_xy mu_n = (2n-1) pi sqrt(k_z k_xy) / d. No unknowns, no grid number.
         Both leave a board without an edge coefficient bit for bit as it is.
"""

import contextlib
import math

import numpy as np
from pcbthermal import laminate
from scipy import ndimage

_ORIG = {"plan_gaps": laminate.plan_gaps, "build": laminate.build}


def eta_laminate(h_side, d, kxy, kz, terms=400):
    """!
    @brief Efficiency of the laminate of a gap in carrying the edge film, against a film on the whole edge at the copper temperature.
    @param h_side Edge coefficient in W/m2K.
    @param d Gap thickness in m (the half-gap d / 2 is analysed; the middle of the gap is a symmetry plane).
    @param kxy In-plane conductivity of the laminate in W/mK.
    @param kz Through conductivity of the laminate in W/mK.
    @param terms Terms of the series.
    @return float between 0 and 1 (1 when h_side is 0).
    """
    if h_side <= 0.0:
        return 1.0
    n = np.arange(1, terms + 1)
    a = (2 * n - 1) * math.pi * math.sqrt(kz * kxy) / d
    w = 8.0 / ((2 * n - 1) ** 2 * math.pi ** 2)
    return float(np.sum(w * a / (h_side + a)))


def edge_ring(board, active, nx, ny):
    """!
    @brief The cells that touch the board edge (the raster border, or the cells an outline crosses).
    @param board A Board.
    @param active Boolean (ny, nx) of the cells on the board.
    @param nx Cells along x.
    @param ny Cells along y.
    @return Boolean (ny, nx).
    """
    if board.has_outline():
        from pcbthermal.geometry import edge_length_on_board
        return (edge_length_on_board(board.outline, nx, ny, board.width / nx, board.height / ny, active) > 0) & active
    ring = np.zeros((ny, nx), dtype=bool)
    ring[0, :] = ring[-1, :] = True
    ring[:, 0] = ring[:, -1] = True
    return ring


def band_mask(board, active, dx, d, width):
    """!
    @brief Cells within a distance of the board edge.
    @param board A Board.
    @param active Boolean (ny, nx) of the cells on the board.
    @param dx Cell size in m.
    @param d Gap thickness in m.
    @param width Band width in units of d (distance between cell centres from the border cell, so 0 is the ring alone), or the string "margin" for laminate.margin_cells(d, dx) cells.
    @return Boolean (ny, nx).
    """
    ny, nx = active.shape
    ring = edge_ring(board, active, nx, ny)
    if width is None:
        return ring
    if width == "margin":                                   # the program's own margin: ceil(d / dx) + 1 cells beyond the border cell
        reach = laminate.margin_cells(d, dx) + 1e-9
    elif width <= 0.0:
        return ring
    else:
        reach = width * d / dx + 1e-9
    dist = ndimage.distance_transform_edt(~ring)
    return (dist <= reach) & active


def make_plan_gaps(band_width, only_when_edge=True):
    """!
    @brief Replacement of laminate.plan_gaps that adds the edge band to the flagged cells of every gap that is cut.
    @param band_width Band width in units of d (None: no band).
    @param only_when_edge True: no band when the board has no edge coefficient.
    @return Function with the signature of laminate.plan_gaps.
    """

    def plan(board, fill, dx, active, s_max=None, n_max=None):
        """!
        @brief laminate.plan_gaps plus the band.
        @param board A Board.
        @param fill Copper fill (L, ny, nx).
        @param dx Cell size in m.
        @param active Boolean (ny, nx).
        @param s_max Longest sub-gap.
        @param n_max Most sub-gaps.
        @return List of GapPlan.
        """
        plans = _ORIG["plan_gaps"](board, fill, dx, active, s_max, n_max)
        if band_width is None or (only_when_edge and not (board.h_side or 0.0) > 0.0):
            return plans
        ps, pn = laminate.parameters()
        s_max, n_max = ps if s_max is None else s_max, pn if n_max is None else n_max
        for p in plans:
            n0 = laminate.n_for_gap(p.d, s_max, n_max)
            if n0 > 1:
                p.n = n0
                p.flagged = p.flagged | band_mask(board, active, dx, p.d, band_width)
        return plans

    return plan


def make_build(eta_mode, eta_scale=1.0, halfcell=False):
    """!
    @brief Replacement of laminate.build that scales the laminate share of the edge conductance of the cells without interior nodes.
    @param eta_mode None (no change), "exact" (eta_laminate of the gap) or "const" (eta_scale for every gap).
    @param eta_scale Constant eta of the mode "const".
    @param halfcell True: the edge film of the laminate nodes of the flagged cells is put in series with the conduction of half a cell (k_xy), g' = g / (1 + h_s dx / (2 k_xy)).
    @return Function with the signature of laminate.build.
    """

    def build(board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans):
        """!
        @brief laminate.build followed by the efficiency on the edge conductance of the unflagged cells.
        @param board A Board.
        @param fill Copper fill.
        @param cell Cell area.
        @param cover Board share.
        @param active Cells on the board.
        @param edge Edge length per cell.
        @param S Lateral conductance.
        @param C Capacity.
        @param gz Vertical links.
        @param g_bottom Bottom conductance.
        @param g_side Edge conductance.
        @param plans Plans.
        @return LadderBuild.
        """
        res = _ORIG["build"](board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans)
        hs = float(board.h_side or 0.0)
        if hs <= 0.0 or board.layers < 2:
            return res
        if halfcell:
            dxc = math.sqrt(float(np.median(cell[cell > 0])))
            kz_h, kxy_h, _ = board.gap_properties()
            for g, p in enumerate(plans):
                if p.n <= 1:
                    continue
                f = 1.0 / (1.0 + hs * dxc / (2.0 * float(kxy_h[g])))          # series half-cell on the laminate film
                # interior nodes of this gap: their layers follow the copper layers, gap by gap (n - 1 each)
                first = board.layers + sum(q.n - 1 for q in plans[:g])
                for j in range(first, first + p.n - 1):
                    res.layers[j - board.layers]["g_side"] = res.layers[j - board.layers]["g_side"] * f
                lam = p.d / (2.0 * p.n)                                           # laminate left in each adjacent copper node
                for l in (g, g + 1):
                    res.g_side[l] = np.where(p.flagged, res.g_side[l] - (1.0 - f) * hs * lam * edge, res.g_side[l])
        if eta_mode is None:
            return res
        L = board.layers
        kz_g, kxy_g, _ = board.gap_properties()
        d_all = board.gap_thicknesses()
        slab = np.asarray(board.slab_thicknesses(), dtype=float)
        t_cu = np.asarray(board.copper_thickness, dtype=float)
        for l in range(L):
            gaps = [g for g in (l - 1, l) if 0 <= g < L - 1]
            held = slab[l] - t_cu[l]                                  # laminate held by the node (m)
            for g in gaps:
                eta = eta_laminate(hs, float(d_all[g]), float(kxy_g[g]), float(kz_g[g])) if eta_mode == "exact" else eta_scale
                share = held / len(gaps)                              # each adjacent gap gives half of what the node holds
                p = plans[g]
                open_ = ~p.flagged                                    # only the cells whose gap is one link keep the film on the copper node
                res.g_side[l] = np.where(open_, res.g_side[l] - (1.0 - eta) * hs * share * edge, res.g_side[l])
        return res

    return build


@contextlib.contextmanager
def rule(band_width=None, eta_mode=None, eta_scale=1.0, halfcell=False):
    """!
    @brief Run with an edge rule (replaces laminate.plan_gaps and laminate.build in this process for the duration of the block).
    @param band_width Band width in units of d, or None.
    @param eta_mode None, "exact" or "const".
    @param eta_scale Constant eta of the mode "const".
    @param halfcell See make_build.
    @return Context manager.
    """
    laminate.plan_gaps = make_plan_gaps(band_width)
    laminate.build = make_build(eta_mode, eta_scale, halfcell)
    try:
        yield
    finally:
        laminate.plan_gaps, laminate.build = _ORIG["plan_gaps"], _ORIG["build"]
