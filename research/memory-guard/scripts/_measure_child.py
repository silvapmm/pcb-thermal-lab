#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _measure_child.py
@brief Child process of the memory study: builds one case, solves it and writes the unknown count, the times and a checksum of the answer to a JSON file. It is started by lib/measure.py, one case per process.
@details Usage (by the wrapper, not by hand): python _measure_child.py '<spec json>' <output json>.
         Modes: "solve" (default) solves once; "compare" solves a fvm case with both orderings and reports the largest difference of the two answers (small cases only: it holds both).
         The resident size at the start (after the imports) is recorded so that the study can subtract the base of the program.
"""

import json
import resource
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[2]))

import numpy as np                                    # noqa: E402

import cases                                          # noqa: E402
import cell_major                                     # noqa: E402
from pcbthermal import api, fvm, solid3d              # noqa: E402

UNIT = 1 if sys.platform == "darwin" else 1024        # ru_maxrss: bytes on macOS, kilobytes on Linux


def main(spec, out_path):
    """!
    @brief Run the case and write the JSON result.
    @param spec Case spec (cases.py) plus "mode" and "order".
    @param out_path Path of the JSON file to write.
    @return None.
    """
    r = {"rss_start": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * UNIT}
    t0 = time.perf_counter()
    p = cases.build(spec)
    cell, model = float(spec["cell_mm"]), spec["model"]
    r["t_build_problem"] = time.perf_counter() - t0
    mode, order = spec.get("mode", "solve"), spec.get("order", "layer")
    if model == "fvm" and (mode == "compare" or order == "cell"):
        nx = max(int(round(p.board.width * 1000.0 / cell)), 2)
        ny = max(int(round(p.board.height * 1000.0 / cell)), 2)
        t1 = time.perf_counter()
        net = fvm.Network(p, nx, ny)
        r["t_assemble"] = time.perf_counter() - t1
        r["unknowns"] = int(net.K.shape[0] - (int(net.drop.sum()) if net.drop is not None else 0))
        if mode == "compare":
            ta = time.perf_counter()
            th_a, _ = net.solve_steady()
            tb = time.perf_counter()
            th_b, _ = cell_major.solve_cell_major(net)
            tc = time.perf_counter()
            r.update(t_solve_layer=tb - ta, t_solve_cell=tc - tb, max_abs_diff_K=float(np.abs(th_a - th_b).max()), theta_max=float(th_a.max()))
        else:
            t2 = time.perf_counter()
            th, res = cell_major.solve_cell_major(net)
            r.update(t_solve=time.perf_counter() - t2, residual=res, theta_max=float(th.max()))
    elif model == "fvm":
        nx = max(int(round(p.board.width * 1000.0 / cell)), 2)
        ny = max(int(round(p.board.height * 1000.0 / cell)), 2)
        t1 = time.perf_counter()
        net = fvm.Network(p, nx, ny)
        r["t_assemble"] = time.perf_counter() - t1
        r["unknowns"] = int(net.K.shape[0] - (int(net.drop.sum()) if net.drop is not None else 0))
        t2 = time.perf_counter()
        th, res = net.solve_steady()
        r.update(t_solve=time.perf_counter() - t2, residual=res, theta_max=float(th.max()))
    else:
        # fdm, solid3d, lumped, analytic through the program's own entry point (the whole run: the computed-h loop is off, h is typed in cases.build)
        r["unknowns"] = cases.count(spec)[0]
        opts = api.SolverOptions(models=(model,), cell_mm=cell)
        t2 = time.perf_counter()
        if model == "solid3d":
            with solid3d.size_limit(10 ** 8):               # The guard under study replaces this limit; the study itself is protected by the parent's cutoff
                sim = api.simulate(p, opts)
        else:
            sim = api.simulate(p, opts)
        r["t_solve"] = time.perf_counter() - t2
        res = sim.results[model]
        r["theta_max"] = float(res.t_max - res.ambient)
    r["rss_end"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * UNIT
    with open(out_path, "w") as fh:
        json.dump(r, fh)


if __name__ == "__main__":
    main(json.loads(sys.argv[1]), sys.argv[2])
