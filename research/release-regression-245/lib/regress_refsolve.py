#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file regress_refsolve.py
@brief Independent references for the four reference-capable boards: the layered 3D conduction solver of `research/solid3d-verification/lib/layered3d.py` (it imports nothing from the program), and the error of each model against it.
@details The reference does not depend on the revision of the program, so it is computed once (`out/references.json`) and used for the result set of every revision. A board is described
         by `regress_boards.REFERENCE_SPECS` (a plain dictionary, the same data the program's board is built from): square plate, laminate of one conductivity, copper of one conductivity,
         insulated sides, a convection coefficient on each face, one square source on the top copper. The gap between two copper layers is cut into 8 slabs and a copper layer that is
         patterned is a slab whose conductivity is copper inside the pad and laminate outside (the copper thickness is then laminate), which is what `tests/test_layered_vs_3d.py` does.
         The compared number is the rise of the hottest top-copper cell under the source, `cell_max_source`, against `t_max - ambient` of each model on the same cell size.
@note The reference is solved on the same cell size as the model (as the test does), so the difference is the model, not the heated area. A finer solve of the reference (cell 0.5 mm) is
      slow (the research folders measured about 85 s for 100 x 100 cells and 10 slabs); `reference_cells` chooses.
"""

import importlib.util
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
LAYERED = REPO / "research" / "solid3d-verification" / "lib" / "layered3d.py"


def _load_solver():
    """!
    @brief Import layered3d.py by its path (not through sys.path, so that no other module of that name can be picked up).
    @return The module.
    """
    spec = importlib.util.spec_from_file_location("layered3d_reference", LAYERED)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reference_rise(spec, cell_mm, solver=None):
    """!
    @brief Rise of the hottest cell under the source of a reference board.
    @param spec One entry of regress_boards.REFERENCE_SPECS.
    @param cell_mm Cell size in mm (the source and pad edges must lie on multiples of it; the solver checks the source).
    @param solver The layered3d module (loaded when None).
    @return Rise in K above the ambient.
    @throws ValueError If the source or the pad edges are not on cell edges.
    """
    L = solver or _load_solver()
    dx = cell_mm * 1e-3
    n = int(round(spec["size"] / cell_mm))
    if abs(n * cell_mm - spec["size"]) > 1e-9:
        raise ValueError(f"the cell {cell_mm} mm does not divide the board {spec['size']} mm")
    t = spec["cu_um"] * 1e-6
    if spec["pad"] is None:
        k_cu = spec["k_cu"]
    else:
        for e in spec["pad"]:
            if abs(e / cell_mm - round(e / cell_mm)) > 1e-9:
                raise ValueError(f"the pad edge {e} mm is between cell edges ({cell_mm} mm)")
        xs = (np.arange(n) + 0.5) * cell_mm
        x0, y0, x1, y1 = spec["pad"]
        inside = (xs[None, :] > x0) & (xs[None, :] < x1) & (xs[:, None] > y0) & (xs[:, None] < y1)
        k_cu = np.where(inside, spec["k_cu"], spec["k_lam"])                  # copper inside the window, laminate in the copper slab outside
    total = spec["thickness"] * 1e-3
    if spec["layers"] == 1:
        slabs = [(t, k_cu, 1), (total - t, spec["k_lam"], 8)]
    elif spec["layers"] == 2:
        slabs = [(t, k_cu, 1), (total - 2 * t, spec["k_lam"], 8), (t, k_cu, 1)]
    else:
        raise ValueError("the reference boards have one or two layers")
    x0, y0, x1, y1 = (v * 1e-3 for v in spec["src"])
    res = L.solve(dx, n, n, slabs, (x0, y0, x1, y1), spec["power"], spec["h_top"], spec["h_bottom"], film_under_source=True)
    return float(res["cell_max_source"])


def compute_references(specs, cells, path, log=print):
    """!
    @brief Solve every reference board at every cell size and store the rises (kept between runs; a pair already in the file is not solved again).
    @param specs Dict board name -> spec (regress_boards.REFERENCE_SPECS).
    @param cells Cell sizes in mm.
    @param path JSON file (written after each solve).
    @param log Function that takes one line of text.
    @return dict {board: {"<cell>": rise_K}}.
    """
    path = Path(path)
    ref = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    solver = _load_solver()
    for name, spec in specs.items():
        for cell in cells:
            key = f"{cell:g}"
            if key in ref.get(name, {}):
                continue
            t0 = time.perf_counter()
            ref.setdefault(name, {})[key] = reference_rise(spec, cell, solver)
            log(f"reference {name:16s} cell {cell:4.2f} mm: rise {ref[name][key]:.4f} K  ({time.perf_counter() - t0:.1f} s)")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(ref, indent=1), encoding="utf-8")
    return ref


def errors(result_set, references):
    """!
    @brief Error of each model against the independent reference, in the rise, for one result set.
    @param result_set A result set from regress_harness.run_suite.
    @param references Output of compute_references.
    @return List of dicts: board, model, cell_mm, rise, reference, error (relative, model/reference - 1).
    """
    rows = []
    for r in result_set["records"]:
        ref = references.get(r["board"], {}).get(f"{r['cell_mm']:g}")
        if ref is None or r["status"] != "ok":
            continue
        rise = r["t_max"] - r["ambient"]
        rows.append({"board": r["board"], "model": r["model"], "cell_mm": r["cell_mm"], "rise": rise, "reference": ref, "error": rise / ref - 1.0})
    return rows


def before_after_table(before, after, references):
    """!
    @brief Markdown table of the error of every model against the reference in two result sets side by side.
    @param before Result set of the earlier revision (v2.4.4).
    @param after Result set of the revision under test.
    @param references Output of compute_references.
    @return str, Markdown (error in percent of the rise; "n/a" where a run was skipped or missing).
    """
    b = {(e["board"], e["model"], e["cell_mm"]): e for e in errors(before, references)}
    a = {(e["board"], e["model"], e["cell_mm"]): e for e in errors(after, references)}
    keys = sorted(set(b) | set(a), key=lambda k: (k[0], k[2], k[1]))
    lines = [f"| Board | Cell [mm] | Model | Reference rise [K] | Error {before['label']} [%] | Error {after['label']} [%] | Change [points] |", "| :-- | --: | :-- | --: | --: | --: | --: |"]
    for k in keys:
        eb, ea = b.get(k), a.get(k)
        ref = (ea or eb)["reference"]
        sb = f"{eb['error'] * 100:+.2f}" if eb else "n/a"
        sa = f"{ea['error'] * 100:+.2f}" if ea else "n/a"
        ch = f"{(ea['error'] - eb['error']) * 100:+.2f}" if (ea and eb) else "n/a"
        lines.append(f"| {k[0]} | {k[2]:g} | {k[1]} | {ref:.4f} | {sb} | {sa} | {ch} |")
    return "\n".join(lines) + "\n"
