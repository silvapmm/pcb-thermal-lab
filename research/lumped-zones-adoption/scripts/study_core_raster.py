#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_core_raster.py
@brief Study 13: does the choice of the zone model (a core or the one-node fallback) depend on the raster? The share of the footprint that the core covers is counted on the Lumped grid, and the fallback threshold (92 %) acts on that count.
@details Found by `study_frozen_impact.py`: the inverted-T example board (nine vias scaled to 3.02 mm pitch under a 10 mm part) has a core of 82 % of the footprint at 1.0 mm (zones, 95.86 degC) and 94.8 % at 0.5 mm
         (the one-node fallback, 92.94 degC, the program's value; the FVM at 0.5 mm: 94.43 degC), a jump of 2.9 K with the cell. Here the share is measured on the 93 simple boards (and the example board with
         arrays) at 1.0, 0.75 and 0.5 mm and at 0.1 mm (the nearest to the geometric value; the grid is built without assembly, cheap), together with the choice (zones or fallback) at each, and the hottest rise
         of the zone variant at 1.0 and 0.5 mm against the reference where the choice differs. Questions: how many boards change choice with the raster, how large is the temperature step when they do,
         and would a rule on the 0.1 mm share (an input that does not depend on the Lumped cell) remove the dependence.
         Success criterion (fixed before the run): no board changes choice between 0.5 and 1.0 mm, or the step in the hottest rise is below 2 % of the rise on every board that does.
Usage: python research/lumped-zones-adoption/scripts/study_core_raster.py   (from the repository root, with the program's .venv; references are read from the cache)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
import warm_refs                                                             # noqa: E402
from pcbthermal import lumped, viaconstriction                               # noqa: E402
from pcbthermal.fvm import Network                                           # noqa: E402

CELLS = (1.0, 0.75, 0.5, 0.1)


def core_share(problem, cell_mm):
    """!
    @brief The share of the footprint of the first heater that the core covers on a grid of the given cell.
    @param problem The Problem.
    @param cell_mm Cell in mm.
    @return float share (0 when there is no core).
    """
    b = problem.board
    nx, ny = int(round(b.width * 1000.0 / cell_mm)), int(round(b.height * 1000.0 / cell_mm))
    net = Network(problem, nx, ny, assemble=False, with_blocks=True, ladder=False)
    vs = viaconstriction.ViaSet(problem) if problem.vias else None
    cov = lumped._footprint_coverage(net, problem.heaters[0])
    core = zl.core_mask(net, cov, vs)
    if core is None:
        return 0.0
    return float(core.sum() / (cov > 0).sum())


def main():
    """!
    @brief Run the boards and print the table and the verdict.
    @return None.
    """
    zref.pc.load_libraries()
    rows = []
    print("| board | share at 1.0 / 0.75 / 0.5 / 0.1 mm | zones at 1.0 / 0.75 / 0.5 mm | rise error zones 1.0 / 0.5 mm % | program 1.0 / 0.5 mm % |\n| :-- | :-- | :-- | :-- | :-- |")
    for label, spec in warm_refs.all_specs():
        p = zref.refs.make_problem(spec)
        sh = [core_share(p, c) for c in CELLS]
        z = [0.0 < s <= zl.OPTIONS["max_core"] for s in sh[:3]]
        ref = zref.refs.reference(spec)["t_with"]
        e_z = [100 * (zref.lumped_tmax(p, "Z_none", c) / ref - 1) for c in (1.0, 0.5)]
        e_f = [100 * (zref.lumped_tmax(p, "Z_fine", c) / ref - 1) for c in (1.0, 0.5)]
        e_p = [100 * (zref.lumped_tmax(p, "P245", c) / ref - 1) for c in (1.0, 0.5)]
        rows.append(dict(label=label, share=sh, zones=z, err_z=e_z, err_p=e_p, err_f=e_f))
        if len(set(z)) > 1 or abs(e_z[0] - e_z[1]) > 2.0:
            print(f"| {label} | " + " / ".join(f"{s:.2f}" for s in sh) + " | " + " / ".join("yes" if v else "no" for v in z) + f" | {e_z[0]:+.1f} / {e_z[1]:+.1f} | {e_p[0]:+.1f} / {e_p[1]:+.1f} |", flush=True)
    flips = [r for r in rows if len(set(r["zones"][1:3] + r["zones"][:1])) > 1]
    flip10 = [r for r in rows if r["zones"][0] != r["zones"][2]]
    steps = [abs(r["err_z"][0] - r["err_z"][1]) for r in flip10]
    print(f"\n{len(rows)} boards; the choice (zones or fallback) differs between 1.0 and 0.5 mm on {len(flip10)}; step of the rise error between the two cells on those: max {max(steps) if steps else 0:.1f} % of the rise")
    allsteps = np.array([abs(r["err_z"][0] - r["err_z"][1]) for r in rows])
    print(f"over all boards the zone variant's rise error changes between 1.0 and 0.5 mm by: mean {allsteps.mean():.2f} %, max {allsteps.max():.2f} %; the program's: mean {np.mean([abs(r['err_p'][0] - r['err_p'][1]) for r in rows]):.2f} %, max {max(abs(r['err_p'][0] - r['err_p'][1]) for r in rows):.2f} %")
    for name, key in (("Z_none (share on the Lumped grid)", "err_z"), ("Z_fine (share on a 0.1 mm grid)", "err_f"), ("program", "err_p")):
        a1 = np.abs([r[key][0] for r in rows])
        a5 = np.abs([r[key][1] for r in rows])
        st = np.abs([r[key][0] - r[key][1] for r in rows])
        print(f"{name}: hottest-rise error at 1.0 mm mean abs {a1.mean():.2f} % max {a1.max():.2f} %; at 0.5 mm mean abs {a5.mean():.2f} % max {a5.max():.2f} %; step between the cells mean {st.mean():.2f} % max {st.max():.2f} %")
    near = [r for r in rows if 0.85 <= r["share"][3] <= 0.97]
    print(f"boards with a core share of 0.85 to 0.97 at 0.1 mm (the neighbourhood of the 0.92 rule): {len(near)}: " + ", ".join(f"{r['label'][:30]} {r['share'][3]:.2f}" for r in near))
    print("written", zref.save_json("core_raster.json", rows))


if __name__ == "__main__":
    main()
