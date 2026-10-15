"""!
@file legacy_comparison.py
@brief Runs the legacy core/ solvers and the new pcbthermal models on one example board.

@details The legacy solvers import wxPython and matplotlib at module level, so both are replaced
by stubs: only the numerical code is exercised. The example board is described once as a native
Problem, and a legacy json_config (canvas pixels, 1 px = 1 mm) is generated from it.

Usage: python examples/legacy_comparison.py [--markdown docs/legacy_vs_new.md]
"""

import argparse
import contextlib
import io
import logging
import os
import sys
import time
from unittest.mock import MagicMock

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _stub_gui():
    """!
    @brief Replace wx and matplotlib with stubs so the legacy solver modules can be imported.
    """
    class _Dialog:
        def __init__(self, *a, **k):
            pass

    wx = MagicMock()
    wx.Dialog = _Dialog
    sys.modules["wx"] = wx
    sys.modules["wx.adv"] = wx.adv
    for name in ("matplotlib", "matplotlib.pyplot", "matplotlib.ticker", "matplotlib.animation"):
        sys.modules[name] = MagicMock()


def example_problem():
    """!
    @brief The example board: 100 x 80 mm, 4 layers, two heaters, via array, partial copper, sink.
    @return A native Problem.
    """
    from pcbthermal.model import problem_from_dict

    def rect(x0, y0, x1, y1):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    return problem_from_dict({
        "name": "example-4layer",
        "board": {"width_mm": 100, "height_mm": 80, "thickness_mm": 1.6, "layers": 4,
                  "copper_thickness_mm": 0.035, "ambient_c": 25, "h_top": 10, "h_bottom": 15,
                  "h_side": 10},
        # Top layer: copper only around the components; inner and bottom layers: full planes
        "zones": [{"layer": 1, "polygon_mm": rect(15, 15, 85, 65)}] +
                 [{"layer": l, "polygon_mm": rect(0, 0, 100, 80)} for l in (2, 3, 4)],
        "heaters": [{"layer": 1, "power_w": 4.0, "polygon_mm": rect(30, 35, 40, 45)},
                    {"layer": 1, "power_w": 1.5, "polygon_mm": rect(65, 38, 71, 44)}],
        "vias": [{"x_mm": 31.5 + 3.5 * i, "y_mm": 36.5 + 3.5 * j, "diameter_mm": 0.3}
                 for i in range(3) for j in range(3)],
        "sinks": [{"layer": 4, "polygon_mm": rect(25, 30, 45, 50), "h_extra": 30.0}],
    })


def to_legacy(problem, dx_mm, tol=0.01, omega=1.5, max_iter=50000, mode="Basic"):
    """!
    @brief Build the legacy editor json_config from a Problem.
    @param problem Native Problem.
    @param dx_mm FDM grid spacing in mm.
    @param tol Legacy SOR tolerance (K).
    @param omega Legacy SOR relaxation factor.
    @param max_iter Legacy iteration limit.
    @param mode "Basic" or "Advanced" (Analytic and Lumped).
    @return Dict in the legacy format.
    """
    b = problem.board
    W, H = b.width * 1000, b.height * 1000

    def px(poly):
        # Canvas pixel = millimetre, y axis pointing down
        return [[x * 1000, H - y * 1000] for x, y in poly]

    els, n = [], 0
    for z in problem.zones:
        n += 1
        els.append({"type": "Zone", "id": n, "layer": z.layer + 1, "points": px(z.polygon)})
    for h in problem.heaters:
        n += 1
        els.append({"type": "Heater", "id": n, "layer": h.layer + 1, "power": h.power, "points": px(h.polygon)})
    for v in problem.vias:
        n += 1
        els.append({"type": "Via", "id": n, "diameter": v.diameter * 1000, "points": px([[v.x, v.y]])})
    for s in problem.sinks:
        n += 1
        els.append({"type": "Sink", "id": n, "layer": s.layer + 1, "htc_extra": s.h_extra, "points": px(s.polygon)})
    return {
        "solver_mode": "fdm",
        "pcb_params": {
            "width": W, "height": H, "thickness": b.thickness * 1000, "layers": b.layers,
            "copper_thickness": b.copper_thickness[0] * 1000, "copper_conductivity": b.materials.k_copper,
            "fr4_conductivity": b.materials.k_fr4_through, "ambient_temp_global": b.ambient,
            "convection_h_global": b.h_side, "convection_h_top": b.h_top, "convection_h_bottom": b.h_bottom,
            "grid_dx": dx_mm, "grid_dy": dx_mm, "tolerance": tol, "max_iterations": max_iter,
            "over_relaxation_factor": omega, "model_mode": mode, "boundary_mode": "Convective",
            "pcb_corners": [[0, 0], [W, H]], "hotspot_threshold": 1000.0,
        },
        "elements": els,
    }


def _quiet(fn, *a, **k):
    """!
    @brief Call a legacy function while silencing its print() output.
    @return The function result.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def run_all():
    """!
    @brief Execute every model and collect comparable numbers.
    @return Tuple (problem, rows) where each row is a dict.
    """
    _stub_gui()
    logging.disable(logging.CRITICAL)
    from core.analytic_solver import AnalyticSolver
    from core.lumped_solver import LumpedSolver
    from core.fdm_solver import FDMSolver
    from pcbthermal import analytic, fvm, lumped

    p = example_problem()
    amb = p.board.ambient
    P = p.total_power()
    rows = []

    def add(group, name, tmax, tmean, power, seconds, balance=None, note=""):
        rows.append(dict(group=group, name=name, tmax=tmax, tmean=tmean, power=power,
                         seconds=seconds, balance=balance, note=note))

    # --- New models
    for cell in (2.0, 1.0, 0.5):
        t0 = time.time()
        r = fvm.solve_steady(p, cell_mm=cell)
        add("new", f"FVM, cell {cell:g} mm", r.t_max, r.t_mean, r.power_in, time.time() - t0, r.balance_error)
    t0 = time.time(); r = lumped.solve_steady(p)
    add("new", "Lumped (rings)", r.t_max, r.t_mean, r.power_in, time.time() - t0, r.balance_error)
    t0 = time.time(); r = analytic.solve_steady(p)
    add("new", "Analytic (modal)", r.t_max, r.t_mean, r.power_in, time.time() - t0, r.balance_error)

    # --- Legacy models
    for mode in ("Basic", "Advanced"):
        t0 = time.time(); r = _quiet(AnalyticSolver.simulate, to_legacy(p, 2, mode=mode))
        add("legacy", f"Analytic, {mode}", r["max_temp"]["value"], r["avg_temp"]["value"], r["total_power"]["value"], time.time() - t0)
        t0 = time.time(); r = _quiet(LumpedSolver.simulate, to_legacy(p, 2, mode=mode))
        add("legacy", f"Lumped, {mode}", r["max_temp"]["value"], r["avg_temp"]["value"], r["total_power"]["value"], time.time() - t0)
    for dx, tol, om, label in ((10, 0.01, 1.5, "app defaults"), (2, 0.01, 1.5, "defaults tol/omega"),
                               (1, 0.01, 1.5, "defaults tol/omega"), (1, 1e-4, 1.9, "tight tol, omega 1.9")):
        t0 = time.time(); r = _quiet(FDMSolver.simulate, to_legacy(p, dx, tol=tol, omega=om))
        add("legacy", f"FDM, dx {dx} mm ({label})", r["max_temp"]["value"], r["avg_temp"]["value"],
            r["total_power"]["value"], time.time() - t0, note=f"{r['iterations']} it, converged={r['converged']}")
    return p, rows


def to_markdown(p, rows):
    """!
    @brief Render the results as Markdown tables.
    @param p The Problem.
    @param rows Rows from run_all().
    @return Markdown string.
    """
    amb, P = p.board.ambient, p.total_power()
    ref = next(r for r in rows if r["name"] == "FVM, cell 0.5 mm")
    d_ref = ref["tmax"] - amb
    out = []
    out.append(f"Reference = FVM at 0.5 mm: Tmax {ref['tmax']:.2f} degC (dT {d_ref:.2f} K). "
               f"Requested power {P:.2f} W, ambient {amb:g} degC.\n")
    out.append("| Group | Model | Tmax [°C] | dT error vs ref | Tmean [°C] | Power used [W] | Energy balance | Time [s] | Note |")
    out.append("| :-- | :-- | --: | --: | --: | --: | --: | --: | :-- |")
    for r in rows:
        err = (r["tmax"] - amb) / d_ref - 1.0
        bal = f"{r['balance']:+.0e}" if r["balance"] is not None else "not computed"
        out.append(f"| {r['group']} | {r['name']} | {r['tmax']:.2f} | {err * 100:+.1f} % | {r['tmean']:.2f} | "
                   f"{r['power']:.2f} | {bal} | {r['seconds']:.2f} | {r['note']} |")
    return "\n".join(out) + "\n"


def ablation():
    """!
    @brief Remove features of the example one by one and compare the new simplified models
           with the FVM (cell 1 mm), to see which feature causes the error.
    @return Markdown table string.
    """
    import copy
    from pcbthermal import analytic, fvm, lumped
    from pcbthermal.model import problem_from_dict, problem_to_dict

    base = problem_to_dict(example_problem())
    full_top = [[0, 0], [100, 0], [100, 80], [0, 80]]

    def only_a(d):
        d["heaters"] = d["heaters"][:1]

    cases = [
        ("full example", lambda d: None),
        ("no sink", lambda d: d.update(sinks=[])),
        ("no vias", lambda d: d.update(vias=[])),
        ("no sink, no vias", lambda d: d.update(sinks=[], vias=[])),
        ("top copper over the full board", lambda d: d["zones"][0].update(polygon_mm=full_top)),
        ("no sink/vias, full top copper", lambda d: (d.update(sinks=[], vias=[]), d["zones"][0].update(polygon_mm=full_top))),
        ("only heater A", only_a),
        ("only A, no sink/vias, full copper", lambda d: (only_a(d), d.update(sinks=[], vias=[]), d["zones"][0].update(polygon_mm=full_top))),
    ]
    out = ["| Case | FVM Tmax [°C] | Lumped Tmax [°C] | Lumped dT error | Analytic Tmax [°C] | Analytic dT error |",
           "| :-- | --: | --: | --: | --: | --: |"]
    for name, edit in cases:
        d = copy.deepcopy(base)
        edit(d)
        p = problem_from_dict(d)
        f = fvm.solve_steady(p, cell_mm=1.0)
        l = lumped.solve_steady(p)
        a = analytic.solve_steady(p)
        out.append(f"| {name} | {f.t_max:.2f} | {l.t_max:.2f} | {100 * (l.delta_t / f.delta_t - 1):+.1f} % | "
                   f"{a.t_max:.2f} | {100 * (a.delta_t / f.delta_t - 1):+.1f} % |")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", help="also write the table to this file")
    ap.add_argument("--ablation", action="store_true", help="print the feature ablation table instead")
    a = ap.parse_args()
    if a.ablation:
        _stub_gui()
        print(ablation())
        sys.exit(0)
    prob, res = run_all()
    md = to_markdown(prob, res)
    print(md)
    if a.markdown:
        with open(a.markdown, "w", encoding="utf-8") as fh:
            fh.write(md)
