#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The test boards of the bare-spot investigation: a square board, full copper except a copper-free window in some layers, a square part of given power on the top, in the program (Problem) and in the resolved reference.
@details A Case holds the geometry in mm. `problem()` builds the program's Problem (copper zones as rectangles around the window, a heater on the top layer), `reference()` solves the
         same board in lib/resolved3d.py on a quadrant (or half) of the board when the symmetry allows it (insulated sides, so the symmetry planes are exact). Stack-ups: a simple
         one (equal gaps, 35 um copper) or the shipped typical 4 and 6 layer stack-ups of the program (copper 35 / 15.2 ... / 35 um, gaps as the template).
         The numbers of the board (copper thickness, gaps, laminate conductivities, films) are read from the Problem object so that both sides use the same data.
"""

import os
import sys
from dataclasses import dataclass, field

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)                                                  # the program

import resolved3d as r3                                                       # noqa: E402
from pcbthermal import Problem                                                # noqa: E402
from pcbthermal import model as pmodel                                        # noqa: E402
from pcbthermal.model import Dielectric, Materials                            # noqa: E402


@dataclass
class Case:
    """!
    @brief One board of the sweep (all lengths in mm).
    """
    name: str
    layers: int = 2
    stack: str = "simple"                 # "simple" (equal gaps) or "template" (the typical stack-up of the program for this layer count)
    thickness: float = 1.6                # total thickness of a simple stack-up in mm
    size: float = 30.0                    # board side
    part: float = 6.0                     # side of the square part, centred
    power: float = 1.0                    # W
    window: tuple = None                  # (x0, y0, x1, y1) of the copper-free window in mm, board coordinates; None = full copper
    window_layers: tuple = (0,)           # 0-based layers that have the window
    h_top: float = 10.0
    h_bottom: float = 10.0
    k_inplane: float = 0.9                # laminate in-plane conductivity W/mK
    k_through: float = 0.3                # laminate through conductivity W/mK
    notes: str = ""
    extra: dict = field(default_factory=dict)


def centred_window(size_mm, board=30.0):
    """!
    @brief A square window centred on the board.
    @param size_mm Side in mm.
    @param board Board side in mm.
    @return (x0, y0, x1, y1) in mm.
    """
    c = board / 2
    return (c - size_mm / 2, c - size_mm / 2, c + size_mm / 2, c + size_mm / 2)


def problem(case):
    """!
    @brief The program's Problem of a case.
    @param case A Case.
    @return Problem.
    """
    mats = Materials(k_fr4_through=case.k_through, k_fr4_inplane=case.k_inplane)
    thick = case.thickness
    if case.stack == "template" and case.layers > 1:
        t = pmodel.stackup_template(case.layers)
        thick = t["total_thickness_um"] / 1000.0
    p = Problem.new(case.size, case.size, case.layers, thick, 35.0, h_top=case.h_top, h_bottom=case.h_bottom, h_side=None, materials=mats)
    if case.stack == "template" and case.layers > 1:
        b = p.board
        b.copper_thickness = [c * 1e-6 for c in t["copper_um"]]
        b.dielectrics = [Dielectric(thickness=d["thickness_um"] * 1e-6, name=d["material"], k_through=case.k_through, k_inplane=case.k_inplane) for d in t["dielectrics"]]
        b.thickness = b.total_thickness()
    w = case.size
    for layer in range(1, case.layers + 1):
        if case.window is not None and (layer - 1) in case.window_layers:
            x0, y0, x1, y1 = case.window
            # Four rectangles around the window (edges on the same lines, so the union has no seam)
            for r in ((0, 0, w, y0), (0, y1, w, w), (0, y0, x0, y1), (x1, y0, w, y1)):
                if r[2] > r[0] and r[3] > r[1]:
                    p.add_zone(layer, rect=r)
        else:
            p.add_zone(layer, rect=(0, 0, w, w))
    c = w / 2
    p.add_heater(1, case.power, rect=(c - case.part / 2, c - case.part / 2, c + case.part / 2, c + case.part / 2))
    return p


def board_numbers(p):
    """!
    @brief The numbers of the board that the resolved reference needs, read from the Problem.
    @param p A Problem.
    @return dict with t_cu, gaps, k_gap_z, k_gap_xy, k_cu, h_top, h_bottom, layers.
    """
    b = p.board
    kz, kxy, _ = b.gap_properties()
    return {"t_cu": [float(x) for x in b.copper_thickness], "gaps": [float(x) for x in b.gap_thicknesses()], "k_gap_z": [float(x) for x in kz],
            "k_gap_xy": [float(x) for x in kxy], "k_cu": float(b.materials.k_copper), "h_top": float(b.h_top), "h_bottom": float(b.h_bottom), "layers": b.layers}


def reference(case, dx_mm=0.25, nsub=8, p=None):
    """!
    @brief Peak and mean rise under the part in the resolved 3D solver.
    @details The board is symmetric about the vertical mid-line y = size / 2 always and about x = size / 2 when the window is centred in x, so a half or a quadrant is solved with
             the sides insulated (the board sides are insulated, so the symmetry planes are exact). The window is a layer-wise copper-free rectangle (laminate of the gap above, or
             below for the top layer).
    @param case A Case.
    @param dx_mm Cell size in the plane in mm (the geometry must lie on its lines).
    @param nsub Sub-slabs per dielectric gap.
    @param p The Problem (built when None).
    @return dict with max, mean (K above ambient), nunknowns, balance.
    """
    p = p or problem(case)
    nb = board_numbers(p)
    dx = dx_mm * 1e-3
    c = case.size / 2
    sym_x = case.window is None or abs((case.window[0] + case.window[2]) / 2 - c) < 1e-9
    # Domain: x from x_lo to size, y from c to size (upper half in y); the source and window are shifted to the domain origin
    x_lo = c if sym_x else 0.0
    nx, ny = int(round((case.size - x_lo) / dx_mm)), int(round((case.size - c) / dx_mm))
    src = (max(c - case.part / 2, x_lo) - x_lo, 0.0, (c + case.part / 2) - x_lo, case.part / 2)
    # The heated part of the domain carries the share of the power that falls in it
    frac = ((src[2] - src[0]) * (src[3] - src[1])) / (case.part ** 2)
    win = None
    if case.window is not None:
        x0, y0, x1, y1 = case.window
        win = (max(x0 - x_lo, 0.0), max(y0 - c, 0.0), x1 - x_lo, y1 - c)
        win = tuple(v * 1e-3 for v in win)
    masks = r3.window_masks(nx, ny, dx, case.layers, win, case.window_layers)
    slabs = r3.build_slabs(case.layers, masks, nb["k_cu"], nb["gaps"], nb["t_cu"], nsub, nb["k_gap_xy"], nb["k_gap_z"])
    res = r3.solve(dx, nx, ny, slabs, tuple(v * 1e-3 for v in src), case.power * frac, nb["h_top"], nb["h_bottom"])
    return {"max": res["max"], "mean": res["mean"], "nunknowns": res["T"].size, "balance": res["balance"]}


def program_peak(case, model, cell_mm, p=None):
    """!
    @brief Peak rise over the ambient in one model of the program (unchanged).
    @param case A Case.
    @param model Model key (fvm, fdm, lumped, analytic, solid3d).
    @param cell_mm Cell size in mm.
    @param p The Problem (built when None).
    @return float Peak rise in K.
    """
    from pcbthermal import SolverOptions, simulate
    p = p or problem(case)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results
    return float(res[model].t_max - p.board.ambient)


__all__ = ["Case", "centred_window", "problem", "board_numbers", "reference", "program_peak", "np"]
