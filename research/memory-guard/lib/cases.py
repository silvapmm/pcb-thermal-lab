#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The ladder of boards of the memory study: a board family and a size make a case spec, the spec makes a Problem, and the unknown count of a case is read without solving.
@details A spec is a plain dict (it travels to the child process as JSON): family, layers, size_mm, cell_mm, model, order. The families cover every class of the memory model:
         plain (copper everywhere), vias (plain with an array of vias), partial (copper on part of each layer, so the laminate nodes of the rule exist), outline (an L-shaped outline),
         block (a 3 mm aluminium block on the top), stripes (ten copper stripes per layer, bare laminate spread over the board), viashs (vias and a heatsink coefficient, the Analytic correction case).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcbthermal import fdm, fvm, solid3d      # noqa: E402
from pcbthermal.model import Problem          # noqa: E402

FAMILIES = ("plain", "vias", "partial", "outline", "block", "viashs", "stripes")
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
    p = Problem.new(s, s, layers=layers, name=f"mem_{fam}_{layers}L_{s:g}")
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    if fam == "partial":
        # Copper on the left 60 % of every layer and a different strip on the inner layers: bare laminate next to the copper, as on a real board
        for k in range(1, layers + 1):
            x0, x1 = (0.0, 0.6 * s) if k % 2 else (0.3 * s, s)
            p.add_zone(k, rect=(x0, 0.0, x1, s))
    elif fam == "stripes":
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
