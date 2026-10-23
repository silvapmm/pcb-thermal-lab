"""!
@file study_models_rect_board.py
@brief The five models of the program on a board of squares and rectangles (lib/rect_board.py): the program's own zones, the fine mask and the cell mappings, with the copper on the cell edges and between them.
@details Same protocol as study_models_our_board.py (1 W in a 6 x 6 mm block, 35 um copper, 10 W/m2K on both faces, insulated edges). Three kinds of run in every model: the fine mask at 0.1 mm (the model's own truth), the program's native zones
         at 1 mm cells (exact rectangles, the program's coverage fraction) and the four cell mappings of the fine mask (arithmetic fraction, geometric, lambda 0.5, mean of the flow-based faces). Shift 0 puts the edges on the cells,
         shift 0.4 mm between them. Needs the additive union of zones (README 4.27): run against the patched copy of the program, set PYTHONPATH.
         Argument: the number of copper layers (1 or 2; with 2 the bottom layer is empty). The 3D solid has no laminate under a single copper layer, so only the 2-layer run is a fair check of it (README 4.35).
         Run: PYTHONPATH=<patched copy>:. .venv/bin/python research/gerbers/scripts/study_models_rect_board.py (from the repository root; a few minutes).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import sys

import numpy as np

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.analysis import heater_stats

import conduction as cd
import rect_board as rb
import study_lumped_analytic as sl
from paths import OUT

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


LAYERS = int(sys.argv[1]) if len(sys.argv) > 1 else 1                  # copper layers of the board; the copper is always on the top one


def make_problem(shift):
    """!
    @brief The board without copper and its heater.
    @param shift Offset of the features (mm).
    @return Problem.
    """
    p = Problem.new(width_mm=rb.W, height_mm=rb.H, layers=LAYERS, thickness_mm=cd.T_LAM * 1000.0, copper_um=cd.T_CU * 1e6, h_top=cd.H_FACE, h_bottom=cd.H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=rb.heater(shift))
    return p


def rise(p, model, cell):
    """!
    @brief Mean heater rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell (mm).
    @return float Rise (K).
    """
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell))
    return heater_stats(sim.results[model], p)[0]["t_mean"] - p.board.ambient


def main():
    """!
    @brief Run both shifts, print the tables and save out/models_rect_board.npz.
    @return None.
    """
    out = {}
    for shift in (0.0, 0.4):
        m = rb.mask(shift)
        p0 = make_problem(shift)
        a, b = sl.phases(p0)
        cells = sl.cell_values(np.where(m, a, b), 10)
        pf = make_problem(shift)
        for r in rb.rects(shift):
            pf.add_zone(1, rect=r, fill=1.0)
        truth = {}
        native = {}
        for model in MODELS:
            try:
                truth[model] = rise(pf, model, 0.1)
                native[model] = rise(pf, model, 1.0)                                # the same zones on 1 mm cells: the program's own fill
            except Exception as e:                                                  # reported, not hidden
                print(f"shift {shift} {model}: failed ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
        mapped = {}
        for name, sc in cells.items():
            p = make_problem(shift)
            feff = np.clip((sc - b) / (a - b), 0.0, 1.0)
            for i in range(feff.shape[0]):
                for j in range(feff.shape[1]):
                    if feff[i, j] > 1e-6:
                        p.add_zone(1, rect=(j, i, j + 1.0, i + 1.0), fill=float(feff[i, j]))
            for model in truth:
                mapped[(name, model)] = rise(p, model, 1.0)
        print(f"\n{LAYERS} copper layer(s), shift {shift} mm: mean rise over the heater (K); zones on 0.1 mm cells = each model's truth")
        print(f"{'':32s}" + "".join(f"{m_:>12s}" for m_ in MODELS))
        print(f"{'zones, 0.1 mm cells (truth)':32s}" + "".join(f"{truth.get(m_, np.nan):12.1f}" for m_ in MODELS))
        print(f"{'same zones, 1 mm cells':32s}" + "".join(f"{native.get(m_, np.nan):12.1f}" for m_ in MODELS))
        print(f"{'  error vs truth (%)':32s}" + "".join(f"{100 * (native[m_] / truth[m_] - 1):12.1f}" if m_ in truth else f"{'-':>12s}" for m_ in MODELS))
        for name in cells:
            print(f"{'mapping: ' + name + ' (%)':32s}" + "".join(f"{100 * (mapped[(name, m_)] / truth[m_] - 1):12.1f}" if m_ in truth else f"{'-':>12s}" for m_ in MODELS))
        print("each model against the FVM truth (%): " + ", ".join(f"{m_} {100 * (truth[m_] / truth['fvm'] - 1):+.1f}" for m_ in truth))
        out[shift] = (truth, native, mapped, list(cells))
    np.savez(OUT / f"models_rect_board_{LAYERS}l.npz", **{f"s{int(k * 10)}_{n}": np.array([v[i].get(m_, np.nan) if i < 2 else np.nan for m_ in MODELS]) for k, v in out.items() for i, n in enumerate(("truth", "native"))})


if __name__ == "__main__":
    main()
