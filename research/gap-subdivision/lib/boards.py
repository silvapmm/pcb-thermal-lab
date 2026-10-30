#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief The designed boards of the gap-subdivision investigation (a uniform stack with a centred square source, or the same with a copper pad), in the program and in the independent references.
@details A `Board` is plain data in mm. `problem()` builds the program's Problem (copper zones, a heater on the top layer); `exact_peak()` gives the exact answer of a board without patterned
         copper (lib/series.py, no mesh); `resolved_peak()` solves a board with pads in the independent 3D finite volumes of research/bare-spot-under-source/lib/resolved3d.py (imports
         nothing from the program), on a quadrant, with the gaps cut into sub-slabs and the peak read as the mean of the cell under the source that the program's own cell would give.
         Every number of the board that the references need is read from the Problem (copper conductivity and thickness, gaps, laminate conductivities), so that both sides use the same data.
         The two stack-up modes of the program are both available: `stack="simple"` (the program's simple stack-up: equal gaps, slab = thickness / layers) and `stack="advanced"`
         (the same equal gaps as explicit dielectrics, copper plus half of each adjacent gap).
"""

import os
import sys
from dataclasses import dataclass, field

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BARE = os.path.join(ROOT, "research", "bare-spot-under-source", "lib")
for _p in (ROOT, BARE, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import resolved3d as r3                                                       # noqa: E402  (independent 3D solver, bare-spot-under-source)
import series                                                                 # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate                       # noqa: E402
from pcbthermal.model import Materials                                        # noqa: E402


@dataclass
class Board:
    """!
    @brief One designed board (lengths in mm, copper in um).
    @details `pad`: side of a square copper pad on the top layer (None: full copper on every layer); `pad_layers`: 0-based layers that carry only the pad (the others are full copper
             unless in `empty_layers`); `empty_layers`: layers with no copper at all (a bare bottom).
    """
    name: str
    layers: int = 2
    gap: float = 1.6                      # thickness of every dielectric gap, mm
    copper: float = 35.0                  # copper thickness of every layer, um
    size: float = 30.0                    # square board side, mm
    source: float = 6.0                   # side of the centred square source, mm
    power: float = 1.0                    # W
    h_top: float = 10.0
    h_bottom: float = 10.0
    stack: str = "advanced"               # "simple" or "advanced" (equal gaps either way)
    k_through: float = 0.3                # laminate through conductivity, W/mK
    k_inplane: float = 0.9                # laminate in-plane conductivity, W/mK
    pad: float = None                     # square pad side, mm (None: no pad)
    pad_layers: tuple = (0,)
    empty_layers: tuple = ()
    note: str = ""
    extra: dict = field(default_factory=dict)


def problem(bd):
    """!
    @brief The program's Problem of a board.
    @param bd A Board.
    @return Problem.
    """
    mats = Materials(k_fr4_through=bd.k_through, k_fr4_inplane=bd.k_inplane)
    thick = bd.layers * bd.copper * 1e-3 + (bd.layers - 1) * bd.gap
    p = Problem.new(bd.size, bd.size, bd.layers, thick, bd.copper, h_top=bd.h_top, h_bottom=bd.h_bottom, h_side=None, materials=mats)
    if bd.stack == "advanced" and bd.layers > 1:
        p.board.make_advanced()
    w, c = bd.size, bd.size / 2
    for layer in range(1, bd.layers + 1):
        if (layer - 1) in bd.empty_layers:
            continue
        if bd.pad is not None and (layer - 1) in bd.pad_layers:
            p.add_zone(layer, rect=(c - bd.pad / 2, c - bd.pad / 2, c + bd.pad / 2, c + bd.pad / 2))
        else:
            p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, bd.power, rect=(c - bd.source / 2, c - bd.source / 2, c + bd.source / 2, c + bd.source / 2))
    return p


def numbers(p):
    """!
    @brief The numbers of the board that the references need, read from the Problem.
    @param p A Problem.
    @return dict with k_cu, t_cu, gaps, k_gap_z, k_gap_xy, h_top, h_bottom, layers.
    """
    b = p.board
    kz, kxy, _ = b.gap_properties()
    return {"k_cu": float(b.materials.k_copper), "t_cu": [float(x) for x in b.copper_thickness], "gaps": [float(x) for x in b.gap_thicknesses()],
            "k_gap_z": [float(x) for x in kz], "k_gap_xy": [float(x) for x in kxy], "h_top": float(b.h_top), "h_bottom": float(b.h_bottom), "layers": b.layers}


def exact_peak(bd, cell_mm, p=None):
    """!
    @brief Exact peak rise (mean over the hottest cell of the given size) of a board with no patterned copper, from the series solution.
    @param bd A Board with no pad and no empty layer.
    @param cell_mm Cell size in mm of the model it will be compared with (the peak of a model is a cell mean).
    @param p The Problem (built when None).
    @return Rise in K.
    @throws ValueError If the board has a pad or an empty layer.
    """
    if bd.pad is not None or bd.empty_layers:
        raise ValueError("exact_peak is for uniform boards")
    nb = numbers(p or problem(bd))
    stack = []
    for l in range(nb["layers"]):
        stack.append((nb["t_cu"][l], nb["k_cu"], nb["k_cu"]))
        if l < nb["layers"] - 1:
            stack.append((nb["gaps"][l], nb["k_gap_xy"][l], nb["k_gap_z"][l]))
    a, c, s, dx = bd.size * 1e-3, bd.size / 2 * 1e-3, bd.source * 1e-3, cell_mm * 1e-3
    # The hottest cell touches the centre: its centre is half a cell from it on each axis when the grid has an even number of cells across the board
    off = dx / 2 if int(round(bd.size / cell_mm)) % 2 == 0 else 0.0
    return float(series.source_rise(a, a, stack, nb["h_top"], nb["h_bottom"], bd.power, (c, s), (c, s), window=(dx, dx), points=((c + off, c + off),))[0])


def resolved_peak(bd, cell_mm, dx_mm=0.25, nsub=8, p=None):
    """!
    @brief Peak rise of a board with pads in the independent resolved 3D solver, read as the mean over the cells of the program's grid (`cell_mm`).
    @param bd A Board (pads and empty layers allowed; the pad and the source are centred, so a quadrant is solved).
    @param cell_mm Cell size in mm of the model it will be compared with (a multiple of dx_mm).
    @param dx_mm Cell size of the reference in mm.
    @param nsub Sub-slabs per dielectric gap.
    @param p The Problem (built when None).
    @return dict with peak (K, hottest block of the model's cell size over the source), mean (K, mean over the source), balance (energy), unknowns.
    """
    nb = numbers(p or problem(bd))
    dx = dx_mm * 1e-3
    c = bd.size / 2
    n = int(round(c / dx_mm))
    masks = []
    xs = (np.arange(n) + 0.5) * dx_mm
    for l in range(bd.layers):
        m = np.ones((n, n), dtype=float)
        if l in bd.empty_layers:
            m[:] = 0.0
        elif bd.pad is not None and l in bd.pad_layers:
            # Quadrant: x and y from the centre outward, the pad reaches pad / 2
            inside = xs < bd.pad / 2
            m = (inside[None, :] & inside[:, None]).astype(float)
        masks.append(m)
    slabs = r3.build_slabs(bd.layers, masks, nb["k_cu"], nb["gaps"], nb["t_cu"], nsub, nb["k_gap_xy"], nb["k_gap_z"])
    src = (0.0, 0.0, bd.source / 2 * 1e-3, bd.source / 2 * 1e-3)
    res = r3.solve(dx, n, n, slabs, src, bd.power / 4.0, nb["h_top"], nb["h_bottom"])
    surf, mask = res["surf"], res["mask"]
    r = int(round(cell_mm / dx_mm))
    # The model's cell grid has a cell edge at the centre of the board only when the board has an even number of its cells: average blocks of r x r fine cells from the centre outward
    best = 0.0
    nb_src = int(round(bd.source / 2 / cell_mm))
    for i in range(max(nb_src, 1)):
        for j in range(max(nb_src, 1)):
            blk = surf[i * r:(i + 1) * r, j * r:(j + 1) * r]
            best = max(best, float(blk.mean()))
    return {"peak": best, "mean": res["mean"], "balance": res["balance"], "unknowns": int(res["T"].size)}


def program_peak(bd, model, cell_mm, p=None):
    """!
    @brief Peak rise over the ambient in one model of the program, unchanged.
    @param bd A Board.
    @param model Model key (fvm, fdm, lumped, analytic, solid3d).
    @param cell_mm Cell size in mm.
    @param p The Problem (built when None).
    @return float Peak rise in K.
    """
    p = p or problem(bd)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results
    return float(res[model].t_max - p.board.ambient)


MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def all_models(bd, cell_mm, p=None, models=MODELS):
    """!
    @brief Peak rise and energy-balance error of the program's models on a board (unchanged program).
    @param bd A Board.
    @param cell_mm Cell size in mm.
    @param p The Problem (built when None).
    @param models Model keys to run.
    @return dict {model: (peak rise in K, balance error)}; (nan, nan) for a model the program refuses (the 3D solid above its size limit).
    """
    p = p or problem(bd)
    out = {}
    for m in models:
        try:
            res = simulate(p, SolverOptions(models=(m,), cell_mm=cell_mm)).results[m]
            out[m] = (float(res.t_max - p.board.ambient), float(res.balance_error))
        except ValueError:
            # The 3D solid refuses a board above MAX_CELLS unknowns
            out[m] = (float("nan"), float("nan"))
    return out


# A lighter grid of lib/graded_pad3d.py for boards of four layers or more (about 5 times fewer unknowns; fitted limit within 0.03 % of the exact series on a uniform board and equal to the fine grid's on pad10-full, README 2.3)
MEDIUM = dict(hf=0.06e-3, hmax=1.0e-3, g=0.35, hz=10e-6, dzmax=200e-6)


def graded_peak(bd, cell_mm, scales=(2.0, 1.414, 1.0), p=None, preset="fine"):
    """!
    @brief Converged peak rise of a board (pads allowed) from the graded 3D solver: three grids, the limit fitted v0 + C s^p.
    @param bd A Board (square board, centred square source and pads).
    @param cell_mm Cell size in mm of the model it will be compared with (even number of cells across the board).
    @param scales Grid scales, decreasing.
    @param p The Problem (built when None).
    @param preset "fine" (the defaults of graded_pad3d.solve) or "medium" (MEDIUM).
    @return dict with peak (extrapolated K), finest (K at the finest grid), order (fitted p), balance (energy, finest grid), unknowns (finest grid), spread (percent between the finest value and the limit).
    """
    import graded_pad3d as gp
    nb = numbers(p or problem(bd))
    pads = []
    for l in range(bd.layers):
        if l in bd.empty_layers:
            pads.append(0)
        elif bd.pad is not None and l in bd.pad_layers:
            pads.append(bd.pad * 1e-3)
        else:
            pads.append(None)
    vals, last = [], None
    for sc in scales:
        last = gp.solve(bd.layers, nb["t_cu"], nb["gaps"], bd.size * 1e-3, bd.source * 1e-3, pads, cell_mm * 1e-3, bd.power, nb["h_top"], nb["h_bottom"], nb["k_cu"],
                        nb["k_gap_xy"][0], nb["k_gap_z"][0], scale=sc, **(MEDIUM if preset == "medium" else {}))
        vals.append(last["peak"])
    v0, order = gp.extrapolate(list(scales), vals)
    return {"peak": float(v0), "finest": float(vals[-1]), "order": float(order), "balance": last["balance"], "unknowns": last["unknowns"], "spread": 100.0 * (vals[-1] - v0) / v0}


def samecell_peak(bd, cell_mm, nsub=32, p=None):
    """!
    @brief Peak rise of the independent resolved 3D solver on the SAME in-plane grid as the model (cell = dx) with the gaps cut into many sub-slabs.
    @details The difference between a layered model and this number is the through-thickness discretisation alone; the difference between this number and the converged graded solver
             is the in-plane discretisation of that cell size alone.
    @param bd A Board.
    @param cell_mm Cell size in mm (the in-plane cell of both the 3D solver and the model).
    @param nsub Sub-slabs per gap (32 is converged to 0.01 %).
    @param p The Problem (built when None).
    @return Peak rise in K.
    """
    return resolved_peak(bd, cell_mm, cell_mm, nsub, p)["peak"]
