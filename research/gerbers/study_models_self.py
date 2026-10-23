"""!
@file study_models_self.py
@brief The mapping in every model of the program, each against itself: the same model run on the fine mask (0.1 mm cells, the truth of that model) and on 1 mm cells with a cell conductance mapped from the mask.
@details The models of the program differ in physics (the FDM is node-centred, the 3D solid has real slabs, the Lumped and Analytic are reduced models), so they cannot all be compared with one reference.
         Each model is its own truth: the fill field of the fine run is the mask itself (one rectangle zone per run of copper pixels, fill 1, cells of 0.1 mm), the coarse runs use one zone per 1 mm cell whose fill gives the
         cell conductance of the mapping (arithmetic, geometric, lambda 0.5 mean, flow-based mean). The error is that of the mean rise over the 6 x 6 mm heater of the coarse run against the fine run of the same model.
         The program must add the coverage of abutting zones instead of taking their maximum (the program's union rule distorts a field made of many small zones; see README 4.27), so this study is run
         against a copy of the program with that one change (np.minimum(fill + coverage, 1) in fvm, fdm, solid3d, analytic); set PYTHONPATH to that copy.
         Run: PYTHONPATH=<patched copy>:. python study_models_self.py (about 20 minutes).
"""

import sys
import time

import numpy as np

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.analysis import heater_stats

import conduction as cd
import study_lumped_analytic as sl
import windows

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
BOARDS_USED = (0, 6, 12, 24)                 # window indices: storm, chibi, easyeda, pcad


def fine_problem(mask):
    """!
    @brief The problem whose zones are the copper pixels of the mask (row runs as rectangles).
    @param mask Boolean copper mask (rows from the top) at 0.1 mm.
    @return Problem.
    """
    p = sl.make_problem()
    m = mask[::-1]                                              # rows from the bottom, as the program's y
    for i in range(m.shape[0]):
        row = m[i]
        edges = np.flatnonzero(np.diff(np.concatenate([[0], row.astype(int), [0]])))
        for a, b in zip(edges[::2], edges[1::2]):
            p.add_zone(1, rect=(a * 0.1, i * 0.1, b * 0.1, (i + 1) * 0.1), fill=1.0)
    return p


def run_model(p, model, cell):
    """!
    @brief Mean heater rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell size (mm).
    @return Mean rise (K) of the heater.
    """
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell))
    return heater_stats(sim.results[model], p)[0]["t_mean"] - p.board.ambient


def main():
    """!
    @brief Run the windows and print the errors per model and mapping.
    @return None.
    """
    masks, meta = windows.load()
    res = {}
    for k in BOARDS_USED:
        mask = masks[k]
        p0 = sl.make_problem()
        a, b = sl.phases(p0)
        S = np.where(mask[::-1], a, b)
        cells = sl.cell_values(S, 10)
        pf = fine_problem(mask)
        for model in MODELS:
            t = time.time()
            try:
                truth = run_model(pf, model, 0.1)
            except Exception as e:                                # a model that cannot take the fine grid (memory, size) is reported
                print(f"window {meta[k][0]} {model}: fine run failed ({type(e).__name__}: {str(e)[:60]})", file=sys.stderr)
                continue
            for name, sc in cells.items():
                p = sl.make_problem()
                feff = np.clip((sc - b) / (a - b), 0.0, 1.0)
                for i in range(feff.shape[0]):
                    for j in range(feff.shape[1]):
                        if feff[i, j] > 1e-6:
                            p.add_zone(1, rect=(j * 1.0, i * 1.0, (j + 1) * 1.0, (i + 1) * 1.0), fill=float(feff[i, j]))
                res.setdefault((model, name), []).append(100 * (run_model(p, model, 1.0) / truth - 1))
            print(f"window {meta[k][0]} {model}: truth {truth:.1f} K, {time.time() - t:.0f} s", file=sys.stderr)
    print(f"{len(BOARDS_USED)} real windows, each model against itself on the fine mask; error of the mean rise over the heater, MAE % (bias)")
    names = list(dict.fromkeys(n for _, n in res))
    print(f"{'cell conductance':24s}" + "".join(f"{m:>18s}" for m in MODELS))
    for n in names:
        row = f"{n:24s}"
        for m in MODELS:
            e = np.array(res.get((m, n), [np.nan]))
            row += f"{np.nanmean(np.abs(e)):9.1f} ({np.nanmean(e):+6.1f})"
        print(row)


if __name__ == "__main__":
    main()
