#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_profile.py
@brief Study 7: a square-wave power profile run with the zoned Lumped model against the FVM profile, on a board with a core under the part (the check the review left open).
@details The profile runner of the program (`lumped.run_profile`, `_LumpedAdapter`) puts the source on node 0 of the heater network; with zones that would drive A alone. The research library
         patches `_LumpedAdapter.advance` (the unit source vector split between A and C) and `lumped.step_responses` inside `zoned_lumped.patched()`; this study runs the three Lumped variants
         (`P245`, `Z_none`, `Z_cap`) and the FVM (0.5 mm, the layered model with the mean-potential via, the reference of the time behaviour as in study 2) on the same square wave
         (p_on = the board's power, duty 0.5, p_off = 0, resolved: the oscillation threshold is set to 0 so that every heater is resolved) at periods 0.1, 1 and 10 s, start from the steady state
         of the average power, until the cycle repeats. Quantities of the last window: the hottest temperature (peak), the lowest (valley) and the mean over the window, as rises over the ambient
         in K and the error against the FVM in percent of the FVM's average steady rise (the user reads the temperature, not the via effect). Boards: the three of study 2 (`simple`) and, with
         `--set all`, the 93 simple boards at the period of 1 s. Success criterion (fixed before running): the peak and the mean of the zones within 10 % of the average steady rise of the FVM on the
         three boards at every period, and not worse than the program's by more than 3 points of that rise on any board of the 93; the start from the steady state of the average power must
         leave the peak and valley within 0.5 K of the first window (the run converges in one or two windows when the oscillation is small).
         Not verified: a table profile with several heaters, a one-shot profile, an outline board, the cross-heating of two parts (one of them with a core).
Usage: python research/lumped-zones-adoption/scripts/study_profile.py [--set simple|all] [--procs N]   (from the repository root, with the program's .venv)
"""

import argparse
import contextlib
import multiprocessing as mp
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import fvm, lumped, profiles                                 # noqa: E402
from pcbthermal.model import SquareWave                                      # noqa: E402

BOARDS = [("5x5 @ 1.2 in 10 mm", dict(n=5, pitch=1.2, src=10.0, fill=385.0)),
          ("3x3 @ 3.0 in 12 mm", dict(n=3, pitch=3.0, src=12.0, fill=385.0)),
          ("5x5 @ 1.2 in 14 x 7 mm", dict(n=5, pitch=1.2, src=10.0, src_wh=(14.0, 7.0), fill=385.0))]
PERIODS = (0.1, 1.0, 10.0)
VARIANTS = ("P245", "Z_none", "Z_cap", "Z_unpatched")     # Z_unpatched: zones with the program's unmodified adapter (the whole power on node A), the control


def summarize(res, ambient):
    """!
    @brief Peak, valley and mean of the last window of a profile result, as rises.
    @param res ProfileResult.
    @param ambient Ambient in degC.
    @return dict with peak, valley, mean (K over the ambient), windows, steps, seconds.
    """
    t = np.asarray(res.t_max)
    return {"peak": float(t.max() - ambient), "valley": float(t.min() - ambient), "mean": float(t.mean() - ambient), "windows": int(res.windows), "steps": int(res.steps),
            "seconds": float(res.seconds), "avg_steady": float(res.steady_average_max - ambient)}


def run_board(spec, period, cell=0.5, rings=10):
    """!
    @brief The square-wave run of one board in the FVM and the Lumped variants.
    @param spec Spec dict of `refs.make_problem`.
    @param period Period of the wave in s.
    @param cell Raster of every model in mm.
    @param rings Rings of the Lumped model.
    @return dict variant -> summary.
    """
    zref.pc.load_libraries()
    p = zref.refs.make_problem(spec)
    h = p.heaters[0]
    h.profile = SquareWave(p_on=h.power / 0.5, period=period, duty=0.5, p_off=0.0)    # the average power stays the board's power
    opt = profiles.ProfileOptions(threshold_c=0.0, duration="stable", stable_c=0.05, theta=0.5)
    t, z, r = fvm.step_responses(p, cell_mm=cell)
    resp = profiles.StepResponse("fvm", t, z, r)
    dec = profiles.decide(p, resp, 0.0)
    out = {}
    t0 = time.time()
    out["FVM"] = summarize(profiles.run_fvm(p, dec, opt, cell), p.board.ambient)
    out["FVM"]["seconds"] = time.time() - t0
    for name in VARIANTS:
        with zref.VARIANTS["Z_none" if name == "Z_unpatched" else name]():
            if name == "Z_unpatched":
                patched_adv = lumped._LumpedAdapter.advance
                lumped._LumpedAdapter.advance = zl.advance_245          # the 2.4.5 step (the program splits the source since the adoption)
            t0 = time.time()
            zl.LAST.clear()
            try:
                res = lumped.run_profile(p, dec, opt, rings, cell)
            finally:
                if name == "Z_unpatched":
                    lumped._LumpedAdapter.advance = patched_adv
            out[name] = summarize(res, p.board.ambient)
            out[name]["seconds"] = time.time() - t0
            out[name]["nz"] = int(zl.LAST.get("nz", 1)) if name != "P245" else 1
    return out


def one(item):
    """!
    @brief Pool worker: one (label, spec, period).
    @param item tuple.
    @return dict.
    """
    label, spec, period = item
    r = run_board(spec, period)
    return {"label": label, "period": period, "res": r}


def report(rows):
    """!
    @brief Print the table of a set of runs: the rise of peak, valley and mean in K and the error against the FVM in percent of its average steady rise.
    @param rows list of dict.
    @return list of dict with the errors added.
    """
    print("\n| board | period s | steady avg K | FVM peak / valley / mean K | " + " | ".join(f"{v} peak / mean err % of rise" for v in VARIANTS) + " |")
    print("| :-- | --: | --: | :-- | " + " :-- |" * len(VARIANTS))
    for r in rows:
        f = r["res"]["FVM"]
        ref = f["avg_steady"]
        r["err"] = {v: {k: 100.0 * (r["res"][v][k] - f[k]) / ref for k in ("peak", "valley", "mean")} for v in VARIANTS}
        print(f"| {r['label']} | {r['period']:g} | {ref:.2f} | {f['peak']:.2f} / {f['valley']:.2f} / {f['mean']:.2f} | " +
              " | ".join(f"{r['err'][v]['peak']:+.1f} / {r['err'][v]['mean']:+.1f}" for v in VARIANTS) + " |", flush=True)
    return rows


def main():
    """!
    @brief Run the chosen set.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--set", default="simple", choices=("simple", "all"))
    ap.add_argument("--procs", type=int, default=1)
    args = ap.parse_args()
    if args.set == "simple":
        todo = [(lab, spec, per) for lab, spec in BOARDS for per in PERIODS]
    else:
        import warm_refs
        todo = [(lab, spec, 1.0) for lab, spec in warm_refs.all_specs()]
    t0 = time.time()
    if args.procs > 1:
        with mp.get_context("spawn").Pool(args.procs) as pool:
            rows = pool.map(one, todo, chunksize=1)
    else:
        rows = [one(x) for x in todo]
    rows = report(rows)
    for v in VARIANTS:
        for k in ("peak", "mean"):
            e = np.abs([r["err"][v][k] for r in rows])
            print(f"{v} {k}: mean abs {e.mean():.2f} % of the rise, max {e.max():.2f} %, boards within 10 %: {(e <= 10).sum()} of {len(e)}")
    print("elapsed", round(time.time() - t0), "s")
    print("written", zref.save_json(f"profile_{args.set}.json", rows))


if __name__ == "__main__":
    main()
