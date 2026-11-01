#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rule_study.py
@brief The copper mappings of an import run through the program's network WITH the laminate rule of 2.4.5 (laminate.py), against the independent 3D reference of ref3d.py; synthetic boards with known copper patterns.
@details The earlier faces (research/gerber-models/lib/faces.py) were built with `ladder=False`: the face conductance of a copper node carries the whole laminate of its slab in the plane. The program of 2.4.5
         moves part of that laminate out of the copper node into interior laminate nodes in the cells with absent copper (plus a margin) and joins them to the copper nodes by the cut gap. A face mapping that
         enters the program therefore has to be built on the node's reduced sheet; this module does it and also keeps the naive form (the old faces on the new network) to show that it double counts.
         Variants (all on the program's `fvm.Network`, cell fill = binary-mask copper fraction in zones so that the rule sees the same cells it sees on a zone import):
         * `today_on`, `today_off`: the fill fraction (one zone per cell), rule on / off;
         * `flow_off`, `lambda_off`: the faces of the earlier study (rule off);
         * `flow_naive`: the earlier faces on the network with the rule on (the laminate is counted twice in the flagged cells);
         * `flow_on`, `lambda_on`: the faces built from the sheet of the copper node after the rule moved its laminate (ΔS per flagged cell removed from every pixel of the cell), on the network with the rule on.
         Reference: ref3d.solve on the same binary masks at the pixel. Rows of every field are from the bottom.
"""

import copy

import numpy as np

import faces as im
import conduction as cd
from pcbthermal import fvm
from pcbthermal.model import Problem

import boardrun
import ref3d

H_FACE = 10.0
T_CU = 35e-6
THICKNESS = 1.6e-3


def cell_fill(ib, kind="binary"):
    """!
    @brief Copper fraction of every cell of every layer.
    @param ib Imported board.
    @param kind Mask kind ("binary" or "coverage").
    @return list of arrays (ny, nx), rows from the bottom, top layer first.
    """
    n = int(round(ib.cell / ib.pix))
    return [cd.cell_blocks(ly[kind].astype(float)[::-1], n).mean(axis=(2, 3)) for ly in ib.layers]


def problem_with_zones(ib, problem, kind="binary"):
    """!
    @brief A copy of the problem with one zone per cell whose fill is the copper fraction of the cell (what the rule reads to find the cells with absent copper).
    @param ib Imported board.
    @param problem Problem made by boardrun.make_problem.
    @param kind Mask kind.
    @return pcbthermal.Problem.
    """
    p = copy.deepcopy(problem)
    for l, f in enumerate(cell_fill(ib, kind)):
        for i in range(f.shape[0]):
            for j in range(f.shape[1]):
                if f[i, j] > 1e-6:
                    p.add_zone(l + 1, rect=(j * ib.cell, i * ib.cell, (j + 1) * ib.cell, (i + 1) * ib.cell), fill=float(f[i, j]))
    return p


def moved_laminate(ib, problem, kind="binary"):
    """!
    @brief The sheet conductance that the rule takes out of every copper node (ΔS per cell and layer), and the number of flagged cells per gap.
    @param ib Imported board.
    @param problem Problem made by boardrun.make_problem.
    @param kind Mask kind.
    @return tuple (problem with zones, list of arrays ΔS (ny, nx) in W/K per copper layer, list of flagged-cell counts per gap).
    """
    pz = problem_with_zones(ib, problem, kind)
    ny, nx = int(round(ib.height / ib.cell)), int(round(ib.width / ib.cell))
    on = fvm.Network(pz, nx, ny, assemble=False, ladder=True)
    off = fvm.Network(pz, nx, ny, assemble=False, ladder=False)
    L = on.n_board
    dS = [np.maximum(off.S[l] - on.S[l], 0.0) for l in range(L)]
    flagged = [int(p.flagged.sum()) for p in on.ladder.plans]
    return pz, dS, flagged


def solve_variant(ib, problem, variant, kind="binary"):
    """!
    @brief The temperature rise field of one variant on the cells.
    @param ib Imported board.
    @param problem Problem made by boardrun.make_problem.
    @param variant One of "today_on", "today_off", "flow_off", "lambda_off", "flow_naive", "flow_on", "lambda_on".
    @param kind Mask kind.
    @return Array (layers, ny, nx) of the rise in K, rows from the bottom (copper layers first, the laminate nodes of the rule after them).
    @throws ValueError If the variant is not known.
    """
    if variant in ("today_on", "today_off"):
        return im.solve_today(ib, problem, kind, rule=(variant == "today_on"))
    sheets = im.layer_sheets(ib, problem, kind)
    if variant in ("flow_off", "lambda_off"):
        return im.solve_faces(ib, problem, im.layer_faces(sheets, ib, problem, variant.split("_")[0]))
    if variant not in ("flow_naive", "flow_on", "lambda_on"):
        raise ValueError(f"unknown variant {variant!r}")
    method = variant.split("_")[0]
    pz, dS, _ = moved_laminate(ib, problem, kind)
    n = int(round(ib.cell / ib.pix))
    if variant != "flow_naive":
        # take the laminate that the rule moved out of the node off every pixel of the cell (the sheet is per unit area, so the same ΔS applies to each pixel)
        sheets = [s - np.kron(d, np.ones((n, n))) for s, d in zip(sheets, dS)]
    faces = im.layer_faces(sheets, ib, problem, method)
    ny, nx = int(round(ib.height / ib.cell)), int(round(ib.width / ib.cell))
    net = im.FaceNetwork(pz, nx, ny, assemble=False, ladder=True)
    net.set_faces(faces)
    return net.solve_steady()[0]


def pixel_network(ib, problem, rule=True, n_max=None, s_max=None, kind="binary"):
    """!
    @brief The program's own layered network on the pixel grid (fill 0 or 1 per pixel), with or without the laminate rule: the limit that any copper mapping on the program's network can reach.
    @details Added by the review (README 10.5). The difference between a variant and this network is the error of the mapping alone; the difference between this network and the 3D
             reference is the error of the network (one node per copper layer, at most `n_max` sub-gaps), which no mapping can remove. The pixel fill is handed to `fvm.Network` by replacing
             `fvm.zone_fill` for the duration of the construction (one zone per pixel would cost minutes of polygon sampling); the program's code is not changed, only called.
             `n_max` and `s_max` replace the two constants of the rule (`laminate.N_MAX`, `laminate.S_MAX`) for this call only, to measure how the network converges in the sub-gaps.
    @param ib Imported board (any cell; the pixel is used).
    @param problem Problem made by boardrun.make_problem (no zones; the heater gives the power).
    @param rule True: the laminate rule of 2.4.5; False: the network of the earlier versions.
    @param n_max Optional most sub-gaps of the rule (None: the program's constant).
    @param s_max Optional longest sub-gap in m (None: the program's constant).
    @param kind Mask kind.
    @return Array (node layers, ny, nx) of the rise in K on the pixel grid, rows from the bottom.
    """
    from pcbthermal import laminate
    masks = np.stack([ly[kind].astype(float)[::-1] for ly in ib.layers])
    ny, nx = masks.shape[1:]
    saved = fvm.zone_fill, laminate.N_MAX, laminate.S_MAX
    fvm.zone_fill = lambda *args, **kw: masks.copy()           # the pixel fill instead of the (absent) zones
    if n_max is not None:
        laminate.N_MAX = int(n_max)
    if s_max is not None:
        laminate.S_MAX = float(s_max)
    try:
        net = fvm.Network(problem, nx, ny, ladder=rule)
    finally:
        fvm.zone_fill, laminate.N_MAX, laminate.S_MAX = saved    # restore the program's function and constants whatever happens
    return net.solve_steady()[0]


def reference(ib, centre, size_mm, n_sub, kind="binary", holes=False):
    """!
    @brief The independent 3D reference: heater mean and maximum of the top copper slab over the heater block.
    @param ib Imported board.
    @param centre (x, y) of the heater in board coordinates (mm).
    @param size_mm Heater side (mm).
    @param n_sub Sub-slabs of every gap.
    @param kind Mask kind.
    @param holes True: the plated holes are barrels of the reference too.
    @return tuple (mean K, max K, unknowns).
    """
    masks = [ly[kind].astype(bool)[::-1] for ly in ib.layers]
    L = len(masks)
    gap = (THICKNESS - L * T_CU) / (L - 1)
    vias = [(r["bx"] * 1e-3, r["by"] * 1e-3, max(r["d"], 0.1) * 1e-3) for r in ib.holes] if holes else None
    m = ref3d.build(masks, ib.pix * 1e-3, T_CU, [gap] * (L - 1), n_sub=n_sub, vias=vias, h_top=H_FACE, h_bottom=H_FACE)
    s = size_mm / 2.0
    hm = np.zeros(masks[0].shape, bool)
    xs, ys = (np.arange(hm.shape[1]) + 0.5) * ib.pix, (np.arange(hm.shape[0]) + 0.5) * ib.pix
    hm[:] = (xs[None, :] > centre[0] - s) & (xs[None, :] < centre[0] + s) & (ys[:, None] > centre[1] - s) & (ys[:, None] < centre[1] + s)
    res = ref3d.solve(m, hm, 1.0)
    top = res["top"]
    return float(top[hm].mean()), float(top[hm].max()), int(m["kxy"].size)


def run_case(ib, centre, size_mm, n_sub, variants, holes=False, kind="binary", ref=None):
    """!
    @brief One imported board (one window): the reference once, then every variant at the cell of the import.
    @param ib Imported board (pixel and cell set).
    @param centre Heater centre (mm, board coordinates).
    @param size_mm Heater side (mm).
    @param n_sub Sub-slabs of the gap in the reference.
    @param variants List of variant names.
    @param holes True: plated holes are vias in the program's problem and barrels in the reference.
    @param kind Mask kind.
    @param ref Optional tuple (mean, max, unknowns) of reference() already computed for this window (it does not depend on the cell).
    @return dict with ref_mean, ref_max, unknowns, and for every variant the heater mean (K) and the error in percent.
    """
    if not holes:
        ib = copy.copy(ib)
        ib.holes = []
    ref_mean, ref_max, unk = ref if ref is not None else reference(ib, centre, size_mm, n_sub, kind, holes)
    p = boardrun.make_problem(ib, centre, size_mm, 1.0, h_face=H_FACE)
    out = {"ref_mean": ref_mean, "ref_max": ref_max, "unknowns": unk, "mean": {}, "error": {}}
    for v in variants:
        f = solve_variant(ib, p, v, kind)
        mean, _ = boardrun.heater_stats(f, ib.cell, centre, size_mm)
        out["mean"][v] = mean
        out["error"][v] = boardrun.percent(mean, ref_mean)
    return out
