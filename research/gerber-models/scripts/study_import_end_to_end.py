"""!
@file study_import_end_to_end.py
@brief Where the import stands: the Gerber set of a board goes through `lib/importer.py` into the program's own finite-volume network, and the result is compared with the program as it is and with the resolved pixel grid.
@details Two boards: the Stormduino (Arduino Uno clone, MIT, two copper layers, plated holes from the drill file, 1 mm cells) and our IC board (`lib/our_board.py`, one layer, 16 plated holes). On each one a 6 x 6 mm heater (1 W) on the top layer,
         10 W/m2K on both faces, insulated edges. Three runs of the program's `fvm.Network`: the reference at the pixel grid (0.1 mm, the binary mask), the program as it is with one zone per cell filled with the copper fraction (today),
         and the imported path: flow-based face conductances from the coverage mask (the recommended source), plus the same faces from the binary mask to isolate the mapping from the mask. Reports the mean and maximum rise of the heater
         block on the top layer, the maximum rise of the board and the time of every step; writes the fields for the figure to out/import_end_to_end.npz.
         Run: .venv/bin/python research/gerber-models/scripts/study_import_end_to_end.py (from the repository root; about 10 minutes, 8 GB of memory).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import time

import numpy as np

import faces as im
import our_board
from paths import DATA, OUT

HEATER = {"layer": 1, "size": 6.0, "power": 1.0}


def run_board(label, roles, box, heater_xy):
    """!
    @brief Import one board and run the four solves.
    @param label Name for the report.
    @param roles Dict of files.
    @param box Optional box (mm) or None.
    @param heater_xy Heater centre in board coordinates (mm).
    @return Dict with the report numbers and the fields (top layer, 1 mm cells).
    """
    t = time.time()
    ib = im.import_board(roles, pix=0.1, cell=1.0, box=box)
    heater = dict(HEATER, x=heater_xy[0], y=heater_xy[1])
    p = im.to_problem(ib, heater)
    print(f"{label}: {ib.width:.0f} x {ib.height:.0f} mm, {len(ib.layers)} copper layer(s), {len(ib.holes)} plated holes imported as vias; import {time.time() - t:.0f} s")
    for w in ib.warnings:
        print("  warning:", w)
    res = {}
    t = time.time()
    fine = im.solve_fine(ib, p, "binary")
    res["fine"] = im.block_mean(fine, ib)
    print(f"  reference on the pixel grid: {time.time() - t:.0f} s")
    del fine
    t = time.time()
    res["today"] = im.solve_today(ib, p, "binary")
    print(f"  program as it is (one zone per cell): {time.time() - t:.0f} s")
    for kind in ("binary", "coverage"):
        t = time.time()
        sheets = im.layer_sheets(ib, p, kind)
        res[f"flow_{kind}"] = im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, "flow"))
        res[f"lambda_{kind}"] = im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, "lambda"))
        print(f"  imported faces from the {kind} mask: {time.time() - t:.0f} s")
    s = heater["size"] / 2.0
    j0, j1, i0, i1 = int(heater["x"] - s), int(heater["x"] + s), int(heater["y"] - s), int(heater["y"] + s)
    ref = res["fine"][0, i0:i1, j0:j1]
    rows = {}
    for k in ("today", "flow_binary", "flow_coverage", "lambda_binary", "lambda_coverage"):
        f = res[k][0, i0:i1, j0:j1]
        rows[k] = (100 * (f.mean() / ref.mean() - 1), 100 * (f.max() / ref.max() - 1), 100 * (res[k].max() / res["fine"].max() - 1))
    print(f"  heater block on the top layer: reference mean {ref.mean():.1f} K, max {ref.max():.1f} K; board maximum {res['fine'].max():.1f} K")
    print(f"  {'run':18s} {'heater mean %':>14s} {'heater max %':>13s} {'board max %':>12s}")
    for k, v in rows.items():
        print(f"  {k:18s} {v[0]:+14.1f} {v[1]:+13.1f} {v[2]:+12.1f}")
    return {"ib": ib, "res": res, "rows": rows, "heater": (heater["x"], heater["y"])}


def main():
    """!
    @brief Run both boards and save the fields for the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    out = {}
    storm = run_board("Stormduino", im.roles_of_downloaded("storm"), None, (33.0, 27.0))
    gpath, dpath = our_board.write(DATA / "synthetic")
    ours = run_board("our IC board", {"copper": [gpath], "outline": None, "drills": [dpath]}, (0.0, 0.0, our_board.SIZE, our_board.SIZE), (20.0, 20.0))
    for tag, r in (("storm", storm), ("ours", ours)):
        for k, v in r["res"].items():
            out[f"{tag}_{k}"] = v[0]
        out[f"{tag}_cov"] = r["ib"].layers[0]["coverage"]
        out[f"{tag}_holes"] = np.array([(h["bx"], h["by"], h["d"]) for h in r["ib"].holes])
        out[f"{tag}_heater"] = np.array(r["heater"])
    np.savez(OUT / "import_end_to_end.npz", **out)


if __name__ == "__main__":
    main()
