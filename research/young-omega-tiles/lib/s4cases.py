#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file s4cases.py
@brief Boards, independent references and runners of the study S4 (tile rule of the Analytic via correction, Krogh well of the Lumped model).
@details Boards are the uniform-copper boards of `research/lumped-analytic-vias/lib/cases.py` (unit cell of a via lattice, lone via, row, arrays, pads) plus large arrays of 4 to 576
         vias. Every board has full copper on every layer, so the fine-grid layered solver of `research/point-via-convergence/lib/resolved_boards.py` (the layered model of the program with
         every barrel drawn at its real size; nothing of the program imported) is the independent reference of the via effect E = T_max(no via) - T_max(with vias). The closed form of
         the cell of one via with a loss (`constriction.cell_with_loss`, insulated rim, Wigner-Seitz disc of the lattice) is the reference of the simplest case.
"""

import math
import os
import sys
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(RESEARCH)
for p in (ROOT, HERE, os.path.join(RESEARCH, "lumped-analytic-vias", "lib"), os.path.join(RESEARCH, "point-via-convergence", "lib"), os.path.join(RESEARCH, "solid3d-verification", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)

import cases                                                                 # noqa: E402
import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
from pcbthermal import SolverOptions, simulate                              # noqa: E402

_REF = {}


def load_libraries():
    """!
    @brief Load the program's shipped libraries.
    @return None.
    """
    pc.load_libraries()


def unit_cell(pitch_mm, layers=2, diameter_mm=0.3, fill_k=385.0):
    """!
    @brief Periodic cell of a via lattice (a board of the size of the pitch, source over the whole top copper, one via at the centre).
    @param pitch_mm Pitch in mm.
    @param layers Copper layers.
    @param diameter_mm Drill in mm.
    @param fill_k Fill conductivity (0 open, 385 copper).
    @return Problem.
    """
    return cases.unit_cell(pitch_mm, diameter_mm, fill_k, layers=layers)


def big_array(n, pitch_mm, layers=4, diameter_mm=0.3, fill_k=385.0, margin_mm=8.0):
    """!
    @brief A square n x n array under a source that covers it, on a board with a margin of copper around.
    @param n Vias per side.
    @param pitch_mm Pitch in mm.
    @param layers Copper layers.
    @param diameter_mm Drill in mm.
    @param fill_k Fill conductivity.
    @param margin_mm Margin between the array and the board edge, in mm.
    @return Problem.
    """
    ext = (n - 1) * pitch_mm
    src = ext + 2.0
    side = math.ceil(src + 2 * margin_mm)
    return cases.array(layers, n, pitch_mm, diameter_mm, fill_k, side_mm=float(side), source_mm=src, power=2.0 + 0.02 * n * n)


def reference_e(problem, dx_mm=1.0 / 16, key=None):
    """!
    @brief The via effect of a uniform board by the fine-grid layered solver (cached by key).
    @param problem Problem (uniform copper, one heater on layer 1).
    @param dx_mm Cell of the solver in mm; it must divide the side, the source and the via coordinates.
    @param key Cache key (None: no cache).
    @return float E in K.
    """
    if key is not None and key in _REF:
        return _REF[key]
    e = hz.reference_uniform(problem, dx_mm)[0]
    if key is not None:
        _REF[key] = e
    return float(e)


def rise(problem, model, cell_mm=0.5, modes=300, rings=10):
    """!
    @brief Maximum rise of one model of the program (or of the patch installed at the moment).
    @param problem Problem.
    @param model "lumped" or "analytic".
    @param cell_mm Cell in mm.
    @param modes Cosine modes of the Analytic series.
    @param rings Rings of the Lumped model.
    @return float K.
    """
    r = simulate(problem, SolverOptions(models=(model,), cell_mm=cell_mm, lumped_rings=rings, analytic_modes=modes)).results[model]
    return float(r.t_max - problem.board.ambient)


def effect(problem, model, cell_mm=0.5, modes=300, rings=10, p_without=None):
    """!
    @brief Via effect E of a model (inside the patch installed by the caller).
    @param problem Problem with vias.
    @param model "lumped" or "analytic".
    @param cell_mm Cell in mm.
    @param modes Modes of the Analytic series.
    @param rings Rings of the Lumped model.
    @param p_without The problem without vias (made if None).
    @return float E in K.
    """
    q0 = p_without if p_without is not None else hz.no_vias(problem)
    return rise(q0, model, cell_mm, modes, rings) - rise(problem, model, cell_mm, modes, rings)


def timed_effect(problem, model, cell_mm=0.5, modes=300, rings=10, p_without=None):
    """!
    @brief Via effect with the wall time and the peak Python memory of the run WITH vias (the one that builds the dense system).
    @param problem Problem with vias.
    @param model "lumped" or "analytic".
    @param cell_mm Cell in mm.
    @param modes Modes of the Analytic series.
    @param rings Rings of the Lumped model.
    @param p_without The problem without vias.
    @return Tuple (E, seconds, peak_mb).
    """
    q0 = p_without if p_without is not None else hz.no_vias(problem)
    r0 = rise(q0, model, cell_mm, modes, rings)
    tracemalloc.start()
    t0 = time.perf_counter()
    r1 = rise(problem, model, cell_mm, modes, rings)
    dt = time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    return r0 - r1, dt, peak


def corpus(name="simple"):
    """!
    @brief Named sets of boards with their tags; each entry is a dict(label, problem, dx (mm of the reference), kind, pitch (mm or None), layers, fill).
    @details "simple": unit cells of pitch 0.8 to 8 mm (2 layers, copper fill) and two 4-layer open ones, a lone via at 2 and 4 mm from a source, a row of 5, 3 x 3 arrays at 3.5 and 1.0 mm,
             the 5 x 5 thermal pad at 1.2 mm. "dense": pitch 0.45 to 1.0 with the 0.3 mm drill (unit cells and 5 x 5 pads) and drills of 0.2 to 0.8 mm at pitch 1.5, where the rule can break.
    @param name "simple" or "dense".
    @return list of dicts.
    """
    out = []

    def add(label, prob, kind, pitch, dx=1.0 / 16, layers=None, fill=385.0):
        out.append({"label": label, "problem": prob, "dx": dx, "kind": kind, "pitch": pitch, "layers": prob.board.layers if layers is None else layers, "fill": fill})
    if name == "simple":
        for p in (0.8, 1.0, 1.5, 2.0, 3.5, 5.0, 8.0):
            add(f"unit cell {p} mm, 2 layers, Cu", unit_cell(p, 2), "unit", p, dx=0.05 if p in (0.8, 1.0) else 1.0 / 16)
        add("unit cell 1.5 mm, 4 layers, open", unit_cell(1.5, 4, fill_k=0.0), "unit", 1.5, fill=0.0)
        add("unit cell 3.5 mm, 4 layers, open", unit_cell(3.5, 4, fill_k=0.0), "unit", 3.5, fill=0.0)
        add("lone via 2 mm from the source, Cu", cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, 2.0), "lone", None)
        add("lone via 4 mm from the source, Cu", cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, 4.0), "lone", None)
        add("row of 5, pitch 1.5, Cu", cases.row(5, 1.5, 0.3, 385.0), "row", 1.5)
        add("3 x 3 array pitch 3.5, Cu", cases.array(4, 3, 3.5, 0.3, 385.0), "array", 3.5)
        add("3 x 3 array pitch 1.0, Cu", cases.array(4, 3, 1.0, 0.3, 385.0), "array", 1.0)
        add("3 x 3 array pitch 3.5, open", cases.array(4, 3, 3.5, 0.3, 0.0), "array", 3.5, fill=0.0)
        add("pad 5 x 5 pitch 1.2, Cu", cases.pad(4, 5, 1.2, 0.3, 385.0), "pad", 1.2)
    elif name == "dense":
        for p in (0.45, 0.6, 0.8, 1.0):
            add(f"unit cell {p} mm, 0.3 drill, 2 layers", unit_cell(p, 2), "unit", p, dx=0.05 if p in (0.6, 0.8, 1.0) else 0.05 * 0.9)
        for p in (0.6, 0.8, 1.0):
            add(f"pad 5 x 5 pitch {p} mm, 0.3 drill", cases.pad(4, 5, p, 0.3, 385.0, side_mm=30.0, source_mm=6.0), "pad", p, dx=0.05)
        for d in (0.2, 0.3, 0.5, 0.8):
            add(f"unit cell 1.5 mm, drill {d}", unit_cell(1.5, 2, diameter_mm=d), "unit", 1.5)
    else:
        raise ValueError(name)
    return out


def nn_info(problem):
    """!
    @brief Median nearest-neighbour distance in mm and the target radius in mm of a problem (for tables).
    @param problem Problem.
    @return Tuple (d_nn_mm, a_mm); d_nn is inf for a lone via.
    """
    import tilerule as tr
    return tr.nn_median(problem) * 1e3, tr.via_target_radius(problem) * 1e3
