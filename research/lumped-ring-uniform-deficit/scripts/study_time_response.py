#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_time_response.py
@brief Review: the step responses and the square-wave profile of the Lumped use the same ring_edges; what does the capped first ring do to them?
@details Four boards: a 1 mm part centred on 100 x 80 mm, a 3 mm part off centre on 200 x 150 mm, a 1 mm and a 10 mm part together on 200 x 150 mm (two heaters, superposition),
         and the example board (where the cap must change nothing). For each: the Lumped steady resistance of every heater (rth) and its time to 63 % from pcbthermal.api.step_response,
         and the peak of a square wave (3 times the power, 20 s period, duty 0.3, four cycles, every heater resolved) from simulate(), with the program and with the capped first
         ring (lib/patch_program.py). Reference: the FVM step response at 0.5 mm (profiles.step_response_fvm) for the simple boards. Writes out/time_response.json.
         Run from the repository root (about 1 minute, peak about 1.3 GB):
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_time_response.py
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "tests" / "regression"))

import patch_program as PP  # noqa: E402
import regress_boards as rb  # noqa: E402
from pcbthermal import Problem, SolverOptions, SquareWave, simulate, api, profiles  # noqa: E402
from pcbthermal import lumped as PROG  # noqa: E402
from pcbthermal.profiles import ProfileOptions  # noqa: E402
from pcbthermal.model import problem_from_dict, problem_to_dict  # noqa: E402

CAPPED = PP.load_patched()
OUT = HERE.parent / "out"


def simple(w, h, parts):
    """!
    @brief Two-layer full-copper board (35 um, 1.6 mm, films 10/15 W/m2K, edge 10 W/m2K) with square sources on the top layer.
    @param w Width in mm.
    @param h Height in mm.
    @param parts List of (side mm, x mm, y mm, power W).
    @return Problem.
    """
    p = Problem.new(w, h, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper(fill=1.0)
    for i, (s, x, y, pw) in enumerate(parts):
        p.add_heater(1, pw, rect=(x - s / 2, y - s / 2, x + s / 2, y + s / 2), name=f"U{i + 1}")
    return p


def t63(resp, i):
    """!
    @brief Time at which the step response of heater i reaches 63.2 % of its steady value.
    @param resp profiles.StepResponse.
    @param i Heater index.
    @return float s.
    """
    return float(np.interp(0.632 * resp.rth[i], np.asarray(resp.z)[i], resp.times))


def lumped_time(p, cell, mod):
    """!
    @brief Step responses and the square-wave peak of the Lumped with a module.
    @param p Problem (its heaters get a square wave here; a copy is used).
    @param cell Cell in mm.
    @param mod Lumped module.
    @return dict with rth, t63 and the profile peak of every heater.
    """
    api.lumped = mod
    try:
        sr = api.step_response(p, "lumped", SolverOptions(models=("lumped",), cell_mm=cell))
        q = problem_from_dict(problem_to_dict(p))                  # a copy: the square waves are not left on the caller's problem
        for h in q.heaters:
            h.set_profile(SquareWave(p_on=3.0 * h.power, period=20.0, duty=0.3))
        sim = simulate(q, SolverOptions(models=("lumped",), cell_mm=cell, profile=ProfileOptions(threshold_c=0.0, duration="cycles", cycles=4)))
        pr = sim.profile_results["lumped"]
        return {"rth": [float(x) for x in sr.rth], "t63": [t63(sr, i) for i in range(len(sr.rth))], "peaks": [float(np.max(t)) for t in pr.t_heaters]}
    finally:
        api.lumped = PROG


def main():
    """!
    @brief Print the table and write out/time_response.json.
    @return None.
    """
    cases = [("1 mm part, 100 x 80, centre", simple(100, 80, [(1.0, 50, 40, 1.0)]), 0.5, True),
             ("3 mm part, 200 x 150, at (60, 50)", simple(200, 150, [(3.0, 60, 50, 1.0)]), 0.5, True),
             ("1 mm + 10 mm parts, 200 x 150", simple(200, 150, [(1.0, 100, 75, 1.0), (10.0, 145, 100, 2.0)]), 0.5, True),
             ("example board", rb.build("example_board"), 1.0, False)]
    rows = []
    print("| board | heater | FVM 0.5 mm: rth (K/W) / t63 (s) | program: rth / t63 / square-wave peak (degC) | capped: rth / t63 / peak |")
    print("| :-- | --: | :-- | :-- | :-- |")
    for (label, p, cell, ref) in cases:
        a, b = lumped_time(p, cell, PROG), lumped_time(p, cell, CAPPED)
        f = profiles.step_response_fvm(p, cell_mm=0.5) if ref else None
        for i in range(len(a["rth"])):
            fv = f"{f.rth[i]:.2f} / {t63(f, i):.2f}" if f is not None else "-"
            print(f"| {label} | {i + 1} | {fv} | {a['rth'][i]:.2f} / {a['t63'][i]:.2f} / {a['peaks'][i]:.2f} | {b['rth'][i]:.2f} / {b['t63'][i]:.2f} / {b['peaks'][i]:.2f} |", flush=True)
        rows.append({"case": label, "program": a, "capped": b, "fvm": None if f is None else {"rth": [float(x) for x in f.rth], "t63": [t63(f, i) for i in range(len(f.rth))]},
                     "identical": a == b})
        print(f"  {label}: program and capped identical: {a == b}")
    OUT.mkdir(exist_ok=True)
    (OUT / "time_response.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
