#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient_fine.py
@brief How does an imported board behave in time with fine cells: does the step response of the heater converge with the cell, does the heat capacity of the copper matter, and what does a transient cost?
@details A window of 30 mm of a multilayer board is imported at 0.1 mm pixels; a 4 mm heater of 1 W steps on at t = 0. Runs of the program's own transient machinery (fvm.transient_from_network, implicit Euler,
         ten doubling stages) on: (R) the pixel grid (the reference), (F1, F05, F025) the flow-based face networks at 1.0, 0.5 and 0.25 mm cells (0.25 mm needs pixels of 0.025 mm: re-imported). Two variants of the
         capacity: the program's capacity of a network with no zones (bare laminate: what the face network of research/gerber-models gives, an omission of that research code) and the capacity with the copper added
         from the coverage (boardrun.set_capacity). Compared: the heater mean rise at t = 0.1, 1, 10 s and at the end, the time to 63.2 % of the steady rise (TransientResult.time_constant), the steady rise, and the
         seconds and the peak memory of each run. Output: out/transient_fine.json.
         Success criterion (before the run): the step response at 0.5 and 0.25 mm agrees with the reference within 3 % at every listed time and with each other within 2 %; the copper capacity moves the time constant
         by the share the arithmetic predicts (reported; if it is over 5 % the import must set the capacity). NOT verified: a measured step response of a physical board, power profiles (square waves) on an imported board,
         the animation, computed heat transfer coefficients (h is typed, 10 W/m2K).
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_transient_fine.py [board] [--quick]   (about 20 minutes on a quiet machine; --quick: 0.1 mm pixel, cells 1.0 and 0.5 only)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import time

import numpy as np

import boardrun
import faces as im
import memory_model as mm
import rb_paths
from pcbthermal import fvm

TIMES = (0.1, 1.0, 10.0)


def step_curve(res, centre, size, grid, nb_layer=0):
    """!
    @brief The heater mean rise at the listed times and the time constant of a transient result.
    @param res TransientResult.
    @param centre Heater centre (mm).
    @param size Heater side (mm).
    @param grid Grid size of the frames (mm).
    @param nb_layer Layer index of the heater.
    @return dict with t (list of times), rise (mean heater rise above the ambient at each listed time and the last frame), tau (s), steady_K.
    """
    out = []
    for t in list(TIMES) + [res.times[-1]]:
        k = int(np.argmin(np.abs(res.times - t)))
        f = res.frames[k] - res.ambient
        out.append((float(res.times[k]), boardrun.heater_stats(f, grid, centre, size, nb_layer)[0]))
    return {"samples": out, "tau": float(res.time_constant()), "steady_K": float(res.steady_t_max - res.ambient)}


def run(key, window, pix, cell, copper_capacity, fine=False, t_end=200.0):
    """!
    @brief One transient.
    @param key Board key.
    @param window Window side (mm); the window is taken at the centre of the board.
    @param pix Pixel (mm).
    @param cell Cell (mm); ignored when fine is True (the grid is the pixel grid).
    @param copper_capacity True: the capacity holds the copper (boardrun.set_capacity); False: the program's capacity without zones.
    @param fine True for the pixel-grid reference.
    @param t_end End of the run (s).
    @return dict with the step curve, seconds, peak memory.
    """
    import native_gerber as ng
    import registry
    roles = registry.roles(key)
    b = ng.layer_bbox(roles["outline"]) if roles["outline"] else ng.layer_bbox(roles["copper"][0])
    cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
    box = (cx - window / 2.0, cy - window / 2.0, cx + window / 2.0, cy + window / 2.0)
    grid = pix if fine else cell
    ib = boardrun.import_window(key, box, pix, grid)
    centre = (window / 2.0, window / 2.0)
    p = boardrun.make_problem(ib, centre, 4.0)
    ny, nx = int(round(ib.height / grid)), int(round(ib.width / grid))
    t = time.time()
    sheets = im.layer_sheets(ib, p, "coverage")
    if fine:
        net = fvm.Network(p, nx, ny, assemble=False, ladder=False)
        for l, S in enumerate(sheets):
            net.S[l] = S * net.cover
        net.K = net._assemble()
        n = 1
    else:
        net = im.FaceNetwork(p, nx, ny, assemble=False, ladder=False)
        net.set_faces(im.layer_faces(sheets, ib, p, "flow"))
        n = int(round(cell / pix))
    del sheets
    if copper_capacity:
        boardrun.set_capacity(net, p, [ly["coverage"] for ly in ib.layers], n)
    res = fvm.transient_from_network(net, p.board.ambient, t_end, n_out=30, theta_scheme=1.0, log_times=True)
    rec = step_curve(res, centre, 4.0, grid)
    rec.update(board=key, window=window, pix=pix, cell=grid, copper_capacity=copper_capacity, fine=fine, seconds=time.time() - t, peak_bytes=mm.peak_rss_bytes(), unknowns=int(net.nl * nx * ny))
    return rec


def main(argv):
    """!
    @brief Run the reference and the cell runs and print the comparison.
    @param argv Command-line words: an optional board key, --quick.
    @return None.
    """
    quick = "--quick" in argv
    key = next((a for a in argv if not a.startswith("--")), "isastm")
    window = 30.0
    cases = [("reference, pixel grid", dict(pix=0.1, cell=0.1, fine=True))]
    for c in ((1.0, 0.5) if quick else (1.0, 0.5, 0.25)):
        cases.append((f"flow faces {c} mm", dict(pix=c / 10.0, cell=c)))      # pixel = cell / 10: an even number of pixels per cell, which the flow-based faces need
    rows = []
    for cap in (True, False):
        for name, kw in cases:
            if not cap and kw.get("fine"):
                continue                                      # the reference is run once, with the copper capacity
            rec = run(key, window, copper_capacity=cap, **kw)
            rec["name"] = name
            rows.append(rec)
            s = rec["samples"]
            print(f"{name:26s} copper capacity {str(cap):5s}: rise at " + ", ".join(f"{t:.1f} s {v:.2f} K" for t, v in s) + f"; tau {rec['tau']:.1f} s; steady {rec['steady_K']:.2f} K; {rec['seconds']:.0f} s", flush=True)
    ref = next(r for r in rows if r["fine"])
    print("\ndifference from the reference (percent of the rise) at the listed times:")
    for r in rows:
        if r["fine"]:
            continue
        d = [100.0 * (a[1] / b[1] - 1.0) for a, b in zip(r["samples"], ref["samples"])]
        print(f"  {r['name']:26s} copper capacity {str(r['copper_capacity']):5s}: " + ", ".join(f"{x:+.1f}" for x in d) + f"; tau {100.0 * (r['tau'] / ref['tau'] - 1.0):+.1f} %")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "transient_fine.json", "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
