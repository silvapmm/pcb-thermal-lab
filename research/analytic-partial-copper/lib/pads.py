#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file pads.py
@brief The designed boards of the analytic-partial-copper investigation (one or two copper layers, a centred square copper pad on the top layer, a centred square source), in the program and in an independent resolved 3D solver.

@details A `Pad` is plain data in mm. `problem()` builds the program's Problem (a pad zone on the top layer, full copper or nothing on the second layer, a heater of the source
         size); `reference()` solves the same board in the independent resolved 3D finite volumes of research/bare-spot-under-source/lib/resolved3d.py (it imports nothing from the
         program) on a quadrant, the laminate cut into sub-slabs, and returns the rise of the hottest cell of the program's grid (the mean of the fine cells it contains).
         Every number of the board that the reference needs (copper, laminate conductivities, thicknesses, films) is read from the Problem so that both sides use the same data.
         The copper slab of a bare cell is laminate (isotropic as the gap), the convention of the other bare-spot studies.
"""

import os
import sys
from dataclasses import dataclass, replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in (ROOT, os.path.join(ROOT, "research", "bare-spot-under-source", "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import resolved3d as r3                                                       # noqa: E402  (independent 3D solver)
from pcbthermal import Problem, SolverOptions, simulate                       # noqa: E402
from pcbthermal.model import Materials                                        # noqa: E402


@dataclass
class Pad:
    """!
    @brief One designed board (lengths in mm, copper in um).
    @details `pad`: side of the square copper pad on the top layer (None: full copper on the top layer); `second`: what the second layer of a 2-layer board carries ("full" or "empty");
             a one-layer board has only the top layer. `thickness` is the total board thickness (copper included).
    """
    name: str = "pad"
    layers: int = 1
    thickness: float = 1.6
    copper: float = 35.0
    size: float = 60.0
    source: float = 6.0
    power: float = 1.0
    h_top: float = 10.0
    h_bottom: float = 15.0
    pad: float = None
    second: str = "full"
    k_through: float = 0.3
    k_inplane: float = 0.9


def with_pad(bd, pad):
    """!
    @brief The same board with another pad side.
    @param bd A Pad.
    @param pad Pad side in mm (None: full copper).
    @return A new Pad.
    """
    return replace(bd, pad=pad, name=f"{bd.name}-pad{pad:g}" if pad else f"{bd.name}-full")


def problem(bd):
    """!
    @brief The program's Problem of a board (simple stack-up, no edge loss, no vias).
    @param bd A Pad.
    @return Problem.
    """
    mats = Materials(k_fr4_through=bd.k_through, k_fr4_inplane=bd.k_inplane)
    p = Problem.new(bd.size, bd.size, bd.layers, bd.thickness, bd.copper, h_top=bd.h_top, h_bottom=bd.h_bottom, h_side=None, materials=mats)
    if bd.layers > 1:
        p.board.make_advanced()                                               # equal gaps as explicit dielectrics: slab = copper + half of each adjacent gap
    c, w = bd.size / 2, bd.size
    if bd.pad is None:
        p.add_zone(1, rect=(0, 0, w, w))
    else:
        p.add_zone(1, rect=(c - bd.pad / 2, c - bd.pad / 2, c + bd.pad / 2, c + bd.pad / 2))
    if bd.layers > 1 and bd.second == "full":
        p.add_zone(2, rect=(0, 0, w, w))
    p.add_heater(1, bd.power, rect=(c - bd.source / 2, c - bd.source / 2, c + bd.source / 2, c + bd.source / 2))
    return p


def program_rise(bd, model, cell_mm=0.5, p=None):
    """!
    @brief Peak rise of a model of the program, unchanged.
    @param bd A Pad.
    @param model Model key.
    @param cell_mm Cell size in mm.
    @param p The Problem (built when None).
    @return Rise over the ambient in K.
    """
    p = p or problem(bd)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
    return float(res.t_max - p.board.ambient)


def reference(bd, cell_mm=0.5, dx_mm=0.25, nsub=8, p=None):
    """!
    @brief Peak rise of a board in the independent resolved 3D solver, read as the program's cell would read it.
    @param bd A Pad (the pad and the source are centred, so a quadrant is solved).
    @param cell_mm Cell size of the model it is compared with, in mm (a multiple of dx_mm).
    @param dx_mm Cell size of the reference in mm.
    @param nsub Sub-slabs per laminate gap.
    @param p The Problem (built when None).
    @return dict with peak (K, hottest block of cell_mm cells), balance (energy balance: heat out over power), unknowns.
    """
    p = p or problem(bd)
    b = p.board
    kcu = float(b.materials.k_copper)
    tcu = [float(x) for x in b.copper_thickness]
    kz_lam, kxy_lam = float(bd.k_through), float(bd.k_inplane)
    n = int(round(bd.size / 2 / dx_mm))
    xs = (np.arange(n) + 0.5) * dx_mm
    inside = np.ones(n, dtype=bool) if bd.pad is None else xs < bd.pad / 2
    f1 = (inside[None, :] & inside[:, None]).astype(float)
    dx = dx_mm * 1e-3
    def mix(f):
        return kxy_lam + f * (kcu - kxy_lam), kz_lam + f * (kcu - kz_lam)
    slabs = []
    kxy, kz = mix(f1)
    slabs.append((tcu[0], kxy, kz, 1))
    if bd.layers == 1:
        slabs.append((bd.thickness * 1e-3 - tcu[0], kxy_lam, kz_lam, nsub))
    else:
        gap = (bd.thickness * 1e-3 - sum(tcu)) / (bd.layers - 1)
        slabs.append((gap, kxy_lam, kz_lam, nsub))
        f2 = np.ones((n, n)) if bd.second == "full" else np.zeros((n, n))
        kxy2, kz2 = mix(f2)
        slabs.append((tcu[1], kxy2, kz2, 1))
    src = (0.0, 0.0, bd.source / 2 * 1e-3, bd.source / 2 * 1e-3)
    res = r3.solve(dx, n, n, slabs, src, bd.power / 4.0, b.h_top, b.h_bottom)
    surf = res["surf"]
    r = int(round(cell_mm / dx_mm))
    nb_src = max(int(round(bd.source / 2 / cell_mm)), 1)
    best = max(float(surf[i * r:(i + 1) * r, j * r:(j + 1) * r].mean()) for i in range(nb_src) for j in range(nb_src))
    return {"peak": best, "balance": res["balance"], "unknowns": int(res["T"].size)}
