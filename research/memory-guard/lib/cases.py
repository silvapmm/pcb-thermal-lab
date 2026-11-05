#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The ladder of boards of the memory study: a board family and a size make a case spec, the spec makes a Problem, and the unknown count of a case is read without solving.
@details A spec is a plain dict (it travels to the child process as JSON): family, layers, size_mm, cell_mm, model, order. The families cover every class of the memory model:
         plain (copper everywhere), vias (plain with an array of vias), partial (copper on part of each layer, so the laminate nodes of the rule exist), outline (an L-shaped outline),
         block (a 3 mm aluminium block on the top), stripes (ten copper stripes per layer, bare laminate spread over the board), viashs (vias and a heatsink coefficient, the Analytic correction case).
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcbthermal import fdm, fvm, solid3d      # noqa: E402
from pcbthermal.model import Problem          # noqa: E402

FAMILIES = ("plain", "vias", "partial", "outline", "block", "viashs", "stripes", "viagrid", "co60")
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def build(spec):
    """!
    @brief Build the Problem of a case spec.
    @param spec Dict with family, layers and size_mm (the board is square, size_mm on a side).
    @return Problem.
    @throws ValueError If the family is unknown.
    """
    fam, layers, s = spec["family"], int(spec["layers"]), float(spec["size_mm"])
    if fam not in FAMILIES:
        raise ValueError(f"unknown family {fam}")
    if fam == "co60":
        return _co60(spec)
    p = Problem.new(s, s, layers=layers, name=f"mem_{fam}_{layers}L_{s:g}")
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    if fam == "partial":
        # Copper on the left 60 % of every layer and a different strip on the inner layers: bare laminate next to the copper, as on a real board
        for k in range(1, layers + 1):
            x0, x1 = (0.0, 0.6 * s) if k % 2 else (0.3 * s, s)
            p.add_zone(k, rect=(x0, 0.0, x1, s))
    elif fam == "stripes" or spec.get("pattern") == "stripes":
        # Ten copper stripes per layer, the stripes of the next layer shifted by half a period: bare laminate everywhere next to copper (the laminate nodes of the rule are spread
        # over the whole board, as on a densely routed board; the reviewer of fix/laminate-nodes had a board like this, with a longer solve than the half-board family)
        for k in range(1, layers + 1):
            for j in range(10):
                x0 = (j + (0.5 if k % 2 == 0 else 0.0)) * s / 10.0
                p.add_zone(k, rect=(x0, 0.0, min(s, x0 + 0.5 * s / 10.0), s))
    else:
        p.add_full_copper()
    c, h = 0.5 * s, 0.1 * s
    p.add_heater(1, 2.0, rect=(c - h / 2, c - h / 2, c + h / 2, c + h / 2), name="U1")
    if fam in ("vias", "viashs"):
        p.add_via_array((c - h, c - h, c + h, c + h), 8, 8, diameter=0.3)
    if fam == "viagrid":
        # A regular n x n array (spec "nvias" per side, 0.3 mm drills) in a square of "array_mm" on a side (default 60 % of the board) at the centre: the via count and the pitch
        # are the variables of the via term of the memory law
        n = int(spec.get("nvias", 0))
        if n > 0:
            a = float(spec.get("array_mm", 0.6 * s)) / 2.0
            p.add_via_array((c - a, c - a, c + a, c + a), n, n, diameter=float(spec.get("via_mm", 0.3)))
    if fam == "viashs":
        p.add_heatsink(1, 40.0, rect=(0.7 * s, 0.1 * s, 0.9 * s, 0.3 * s))
    if fam == "outline":
        p.set_outline([(0, 0), (s, 0), (s, 0.4 * s), (0.4 * s, 0.4 * s), (0.4 * s, s), (0, s)])
    if fam == "block":
        p.add_heatsink(1, 20.0, rect=(c - 3 * h, c - 3 * h, c + 3 * h, c + 3 * h), thickness_mm=3.0)
    return p


def count(spec):
    """!
    @brief Unknowns of a case for its model, counted without solving; also the slab count for the 3D solid.
    @param spec Case spec (model and cell_mm included).
    @return Tuple (unknowns, slabs); slabs is 0 for the models other than the 3D solid.
    """
    p = build(spec)
    m, c = spec["model"], float(spec["cell_mm"])
    if m == "solid3d":
        n, ns, _, _ = solid3d.unknowns(p, c)
        return n, ns
    if m == "fdm":
        return fdm.unknowns(p, c)[0], 0
    # fvm, and the grid of lumped and analytic (they do not factor a sparse matrix; the study records what they take)
    return fvm.unknowns(p, c)[0], 0


def _co60(spec):
    """!
    @brief The CO60 board (285 x 95 mm, two layers, plated holes of the drill file as vias, copper everywhere) or a square window of it, for the via term of the memory law.
    @details The data folder is the environment variable PCBT_REAL_BOARDS (downloads that are ignored by version control, never copied into the repository). size_mm = 0 takes the
             whole board; otherwise a window of size_mm on a side centred on the board centre, with the holes inside it. Copper is full, so only the vias change the matrix.
    @param spec Case spec (size_mm, cell_mm).
    @return Problem.
    @throws RuntimeError If PCBT_REAL_BOARDS is not set.
    """
    from pcbthermal.gerber import excellon
    folder = os.environ.get("PCBT_REAL_BOARDS")
    if not folder:
        raise RuntimeError("PCBT_REAL_BOARDS is not set")
    dr = excellon.read_drill_file(os.path.join(folder, "co60", "drill.drl"))
    bx0, by0, bx1, by1 = -0.16235, -0.1425, 285.13765, 95.25750
    s = float(spec["size_mm"])
    cx, cy = 0.5 * (bx0 + bx1), 0.5 * (by0 + by1)
    if s <= 0:
        x0, y0, w, h = bx0, by0, bx1 - bx0, by1 - by0
    else:
        x0, y0, w, h = cx - s / 2, cy - s / 2, s, s
    p = Problem.new(w, h, layers=2, name="mem_co60")
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    if spec.get("pattern") == "stripes":
        # Stripes along the long side, shifted by half a period on the second layer: bare laminate next to copper everywhere, so the laminate nodes of the rule (five node
        # layers per cell, as an imported board with patterned copper) make the graph thick, which is the situation of the reviewer's 541 500-unknown run
        for k in (1, 2):
            for j in range(10):
                y_lo = (j + (0.5 if k == 2 else 0.0)) * h / 10.0
                p.add_zone(k, rect=(0.0, y_lo, w, min(h, y_lo + 0.5 * h / 10.0)))
    else:
        p.add_full_copper()
    p.add_heater(1, 2.0, rect=(0.45 * w, 0.45 * h, 0.55 * w, 0.55 * h), name="U1")
    for ho in dr.holes:
        if spec.get("novias") or ho.is_slot or not (x0 <= ho.x <= x0 + w and y0 <= ho.y <= y0 + h):
            continue
        p.add_via(ho.x - x0, ho.y - y0, diameter=ho.diameter)
    return p
