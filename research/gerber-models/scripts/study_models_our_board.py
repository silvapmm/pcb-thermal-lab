"""!
@file study_models_our_board.py
@brief Our own IC board (lib/our_board.py) in the five models of the program: each model against itself on the fine mask, the five fine results side by side, and the cell mappings in each.
@details The copper of the board (40 x 40 mm, one layer, 35 um, 1 W in a 6 x 6 mm block under the IC, 10 W/m2K on both faces, insulated edges; the plated holes are left out so that only the mapping of the copper is tested)
         is read from the Gerber by the independent reader at 0.1 mm. Truth of each model: that model run on the fine mask (one zone per run of copper pixels, cells of 0.1 mm). Coarse runs: 1 mm cells with the cell
         conductance of four mappings (the program's arithmetic fraction, geometric mean, lambda 0.5, mean of the flow-based faces), written as one zone per cell with the equivalent fill. The additive union of zones is
         needed (README 4.27): run against a copy of the program with that one change, set PYTHONPATH to it.
         Run: PYTHONPATH=<patched copy>:. .venv/bin/python research/gerber-models/scripts/study_models_our_board.py (from the repository root; minutes to an hour, the 3D solid may refuse the fine grid).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import sys
import time

import numpy as np

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.analysis import heater_stats

import conduction as cd
import faces as im
import our_board
import study_lumped_analytic as sl
from paths import OUT

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
SIZE = our_board.SIZE


def make_problem():
    """!
    @brief The board without copper: one layer, 40 x 40 mm, 35 um, 10 W/m2K on both faces, insulated edges, 1 W in a 6 x 6 mm block at the centre.
    @return Problem.
    """
    p = Problem.new(width_mm=SIZE, height_mm=SIZE, layers=1, thickness_mm=cd.T_LAM * 1000.0, copper_um=cd.T_CU * 1e6, h_top=cd.H_FACE, h_bottom=cd.H_FACE, h_side=None)
    p.add_heater(1, 1.0, rect=(SIZE / 2 - 3, SIZE / 2 - 3, SIZE / 2 + 3, SIZE / 2 + 3))
    return p


def fine_problem(mask):
    """!
    @brief The problem whose zones are the copper pixels of the mask (row runs as rectangles, 0.1 mm).
    @param mask Boolean copper mask (rows from the bottom).
    @return Problem.
    """
    p = make_problem()
    for i in range(mask.shape[0]):
        row = mask[i]
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
    @return float Mean rise (K) over the heater.
    """
    sim = simulate(p, SolverOptions(models=(model,), cell_mm=cell))
    return heater_stats(sim.results[model], p)[0]["t_mean"] - p.board.ambient


def main():
    """!
    @brief Run every model on the fine mask and on the coarse mappings; print the tables and save out/models_our_board.npz.
    @return None.
    """
    g, d = our_board.write(OUT / "our_board")
    ib = im.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=0.1, cell=1.0, box=(0.0, 0.0, SIZE, SIZE))
    mask = ib.layers[0]["binary"][::-1]                              # rows from the bottom
    a, b = sl.phases(make_problem())
    S = np.where(mask, a, b)
    cells = sl.cell_values(S, 10)
    truth, coarse = {}, {}
    pf = fine_problem(mask)
    print(f"fine problem: {len(pf.zones)} zones, copper {100 * mask.mean():.1f} % of the board", file=sys.stderr)
    for model in MODELS:
        t = time.time()
        try:
            truth[model] = run_model(pf, model, 0.1)
        except Exception as e:                                          # a model that cannot take the fine grid is reported, not hidden
            print(f"{model}: fine run failed ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
            continue
        print(f"{model}: fine {truth[model]:.1f} K, {time.time() - t:.0f} s", file=sys.stderr)
    for name, sc in cells.items():
        p = make_problem()
        feff = np.clip((sc - b) / (a - b), 0.0, 1.0)
        for i in range(feff.shape[0]):
            for j in range(feff.shape[1]):
                if feff[i, j] > 1e-6:
                    p.add_zone(1, rect=(j * 1.0, i * 1.0, (j + 1) * 1.0, (i + 1) * 1.0), fill=float(feff[i, j]))
        for model in MODELS:
            try:
                coarse[(name, model)] = run_model(p, model, 1.0)
            except Exception as e:
                print(f"{model} {name}: failed ({type(e).__name__}: {str(e)[:80]})", file=sys.stderr)
    print("our IC board, 1 W in a 6 x 6 mm block: mean rise over the heater (K)")
    print(f"{'':28s}" + "".join(f"{m:>12s}" for m in MODELS))
    print(f"{'fine mask (each its own truth)':28s}" + "".join(f"{truth.get(m, float('nan')):12.1f}" for m in MODELS))
    for name in cells:
        print(f"{name:28s}" + "".join(f"{coarse.get((name, m), float('nan')):12.1f}" for m in MODELS))
    print("error against the model's own fine run (%)")
    for name in cells:
        print(f"{name:28s}" + "".join(f"{100 * (coarse[(name, m)] / truth[m] - 1):12.1f}" if (name, m) in coarse and m in truth else f"{'-':>12s}" for m in MODELS))
    if "fvm" in truth:
        print("error against the FVM fine run (%): the models are different physics, not only a different grid")
        for m in MODELS:
            if m in truth:
                print(f"  {m:10s} fine {100 * (truth[m] / truth['fvm'] - 1):+6.1f} %")
    np.savez(OUT / "models_our_board.npz", models=np.array(MODELS), maps=np.array(list(cells)),
             truth=np.array([truth.get(m, np.nan) for m in MODELS]), coarse=np.array([[coarse.get((n, m), np.nan) for m in MODELS] for n in cells]))


if __name__ == "__main__":
    main()
