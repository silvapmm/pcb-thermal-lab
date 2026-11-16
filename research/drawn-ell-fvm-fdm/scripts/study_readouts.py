#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_readouts.py
@brief Question: why does the board maximum of the harness board `drawn_ell` read 99 K in the FVM and 67 K in the FDM while the heater means agree within 3 %?
@details Runs the program's models on the board at several cells and prints, per model and cell, every read-out side by side: board maximum (`t_max`, hottest node),
         its location, the heater mean and face maximum of `analysis.heater_stats`, the surface read-out, the energy balance.
         Run from the repository root, one solve at a time: `nice -n 10 .venv/bin/python research/drawn-ell-fvm-fdm/scripts/study_readouts.py [--cells 2,1,0.5] [--models fvm,fdm] [--fem]`.
"""
import argparse
import logging
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests" / "regression"))

from pcbthermal import api, analysis      # noqa: E402
import regress_boards as B                # noqa: E402

log = logging.getLogger("study_readouts")


def run_one(name, model, cell):
    """!
    @brief Solve one board with one model and collect the read-outs.
    @param name Harness board name.
    @param model Model key.
    @param cell Cell in mm.
    @return dict of read-outs (rise above ambient in K) or None when the model refused.
    """
    p = B.build(name)
    sim = api.simulate(p, api.SolverOptions(models=(model,), cell_mm=cell))
    r = sim.results.get(model)
    if r is None:
        return None
    amb = r.ambient
    row = {"warn": [w[:110] for w in r.warnings], "tmax": r.t_max - amb, "loc": r.t_max_location, "bal": r.balance_error if hasattr(r, "balance_error") else None}
    h = analysis.heater_stats(r, p)[0]
    row.update(h_mean=h["t_mean"] - amb, h_max=h["t_max"] - amb)
    if "t_max_surface" in h:
        row.update(h_max_surf=h["t_max_surface"] - amb, h_mean_surf=h["t_mean_surface"] - amb)
    if r.T is not None:
        row["top_max"] = float(np.max(r.T[0])) - amb
    return row


def main():
    """!
    @brief Print the table.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="drawn_ell")
    ap.add_argument("--cells", default="2,1,0.5")
    ap.add_argument("--models", default="fvm,fdm,solid3d")
    ap.add_argument("--fem", action="store_true")
    ap.add_argument("--warnings", action="store_true", help="print the warnings of every run")
    a = ap.parse_args()
    models = a.models.split(",") + (["fem"] if a.fem else [])
    for m in models:
        for c in [float(x) for x in a.cells.split(",")]:
            row = run_one(a.board, m, c)
            if row is None:
                print(f"{a.board} {m} {c} refused", flush=True)
                continue
            loc = row["loc"]
            locs = "(L%d, %.2f, %.2f mm)" % (loc[0], loc[1] * 1e3, loc[2] * 1e3) if loc else "-"
            print(f"{a.board:12s} {m:8s} cell {c:5.2f}  Tmax {row['tmax']:8.3f} at {locs:24s} heater mean {row['h_mean']:7.3f} face max {row['h_max']:8.3f} "
                  f"surf max {row.get('h_max_surf', float('nan')):8.3f} top-layer max {row.get('top_max', float('nan')):8.3f} bal {row['bal']:.1e}", flush=True)
            if a.warnings:
                for w in row["warn"]:
                    print("      warning:", w, flush=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
