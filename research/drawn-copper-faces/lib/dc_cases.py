#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file dc_cases.py
@brief The synthetic boards of the drawn-copper study and the copy of a drawn board as an imported one (zones to coverage rasters), plus the runners of the FVM and FDM.
@details Every board is 20 mm square without an outline, 1.6 mm, two or four copper layers (35 um, 400 W/mK), laminate 0.9 / 0.3 W/mK, a 4 mm heater of 1 W at the centre on the top layer,
         `h_top = h_bottom = 10 W/m2K` and an edge film `h_side`. The copper is a list of rectangles per layer (millimetres, board frame), so that the same description feeds the program
         (zones), the imported copy (`zones_to_imported`) and the finite-element reference (`dc_fem.py`). Nothing here edits the program: the imported copy is a deep copy of the problem
         whose zones are replaced by coverage rasters, which is exactly what a Gerber import hands to the models.
"""
import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import Problem, copper, fvm, fdm, laminate                      # noqa: E402
from pcbthermal.geometry import exact_coverage                                  # noqa: E402

A = 20.0          # board side, mm
HEATER = 4.0      # heater side, mm


def rects_inset(inset):
    """!
    @brief One rectangle: the board shrunk by `inset` on every side.
    @param inset Distance of the copper edge from the board edge, mm.
    @return list of (x0, y0, x1, y1) in mm.
    """
    return [(inset, inset, A - inset, A - inset)]


def rects_stripes(inset=1.2, width=1.2, pitch=2.4, pad=7.2):
    """!
    @brief Horizontal stripes plus a square pad at the centre (the `sq_stripes` top layer of validation 40).
    @param inset Distance of the stripes from the board edge, mm.
    @param width Stripe width, mm.
    @param pitch Stripe pitch, mm.
    @param pad Pad side, mm.
    @return list of rectangles.
    """
    out, y = [], inset
    while y < A - inset - 1e-9:
        out.append((inset, y, A - inset, min(y + width, A - inset)))
        y += pitch
    c = A / 2
    out.append((c - pad / 2, c - pad / 2, c + pad / 2, c + pad / 2))
    return out


def rects_ell(inset=1.2, cut=8.0):
    """!
    @brief An L: the inset square with a square corner of side `cut` removed at the upper right.
    @param inset Distance from the board edge, mm.
    @param cut Side of the removed corner, mm.
    @return list of two rectangles.
    """
    lo, hi = inset, A - inset
    return [(lo, lo, hi, hi - cut), (lo, hi - cut, hi - cut, hi)]


def case(name, h_side=200.0, layers=2):
    """!
    @brief A named board of the study.
    @param name 'plain_inset', 'plain_wall', 'stripes', 'ell', 'hatch'.
    @param h_side Edge film in W/m2K.
    @param layers 2 or 4 copper layers (inner layers are plain copper 1.2 mm inside).
    @return dict with keys name, h_side, layers, copper (list per layer of rectangles), fill (hatching fill of every rectangle, 1 for solid).
    """
    top = {"plain_inset": rects_inset(1.2), "plain_wall": rects_inset(0.0), "stripes": rects_stripes(), "ell": rects_ell(), "hatch": rects_inset(1.2)}[name]
    other = rects_inset(0.0 if name == "plain_wall" else 1.2)
    fill = 0.5 if name == "hatch" else 1.0
    return {"name": name, "h_side": h_side, "layers": layers, "copper": [top] + [other] * (layers - 1), "fill": [fill] + [1.0] * (layers - 1)}


def problem(c):
    """!
    @brief The program's Problem of a case, copper drawn as zones.
    @param c Case from `case`.
    @return Problem.
    """
    p = Problem.new(A, A, c["layers"], h_side=c["h_side"])
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    h = A / 2
    p.add_heater(1, 1.0, polygon=[[h - HEATER / 2, h - HEATER / 2], [h + HEATER / 2, h - HEATER / 2], [h + HEATER / 2, h + HEATER / 2], [h - HEATER / 2, h + HEATER / 2]], name="U")
    for l, rs in enumerate(c["copper"]):
        for (x0, y0, x1, y1) in rs:
            p.add_zone(l + 1, polygon=[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], fill=c["fill"][l])
    return p


def zone_rasters(p, pix_mm, quantise=True, only=None):
    """!
    @brief Exact-coverage rasters of the zones of a problem, one per layer that has a zone (what an import of the same copper would hand to the models).
    @details The coverage of a pixel is the exact area share of the union of the zones of the layer: the sum of the exact shares of the zones times their fill, clipped to the
             largest fill seen (touching zones fill a pixel together; overlapping zones with different fills are approximated, which the study boards and the harness boards do not have).
             Stored as uint8 (0..255), so a hatch fill of 0.7 is read as 178 / 255 = 0.698.
    @param p Problem (zones in metres).
    @param pix_mm Pixel in mm; the raster covers the board box.
    @param quantise True: uint8 as a stored import; False: float 0..255, exact.
    @param only Layer indices to rasterise (None: every layer that has a zone).
    @return dict layer index (0 = top) -> array (rows from the top).
    """
    W, H = p.board.width * 1e3, p.board.height * 1e3
    nx, ny = int(round(W / pix_mm)), int(round(H / pix_mm))
    dx, dy = p.board.width / nx, p.board.height / ny
    out = {}
    for l in range(p.board.layers):
        mine = [z for z in p.zones if z.layer == l]
        if not mine or (only is not None and l not in only):
            continue
        cov = np.zeros((ny, nx))
        top = 0.0
        for z in mine:
            e = exact_coverage(np.asarray(z.polygon), nx, ny, dx, dy) * z.fill
            top = max(top, z.fill)
            cov = np.minimum(cov + e, top)
        out[l] = np.round(255 * cov[::-1]).astype(np.uint8) if quantise else (255.0 * cov[::-1]).astype(np.float32)    # rows from the top
    return out


def zones_to_imported(p, cell_mm, mapping="faces", pix_per_cell=10):
    """!
    @brief A deep copy of a drawn problem whose zones are replaced by exact-coverage rasters (what a Gerber import hands to the models).
    @param p Drawn Problem.
    @param cell_mm Cell of the run in mm.
    @param mapping 'faces' (flow-based), 'lambda' or 'fill' (harmonic of the cell fills).
    @param pix_per_cell Pixels per cell side, even.
    @return Problem with `imported` set and no zones.
    """
    q = copy.deepcopy(p)
    r = zone_rasters(p, cell_mm / pix_per_cell)
    layers = sorted(r)
    q.zones = []
    q.imported = copper.imported_from_rasters([r[l] for l in layers], cell_mm / pix_per_cell, mapping, indices=layers)
    return q


def heater_mean_fvm(p, cell_mm):
    """!
    @brief Mean rise of the heater footprint of the program's FVM (its own weights) and the heat-balance error.
    @param p Problem.
    @param cell_mm Cell in mm.
    @return Tuple (mean rise K, balance error).
    """
    nx = int(round(A / cell_mm))
    r = fvm.solve_steady(p, cell_mm=cell_mm)
    net = fvm.Network(p, nx, nx, assemble=False)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum()), float(r.balance_error)


def heater_mean_fdm(p, cell_mm):
    """!
    @brief Mean rise of the heater of the FDM at its nodes (the node weights of the part) and the heat-balance error.
    @param p Problem.
    @param cell_mm Cell in mm.
    @return Tuple (mean K, balance error).
    """
    net = fdm.Network(p, cell_mm)
    r = fdm.solve_steady(p, cell_mm=cell_mm)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum()), float(r.balance_error)
