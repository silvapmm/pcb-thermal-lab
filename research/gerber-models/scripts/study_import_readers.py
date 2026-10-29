#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_import_readers.py
@brief Does the choice of reader change the thermal result? The Stormduino imported twice, with the independent reader and with gerbonara + shapely, and run through the same program network.
@details Both imports use the same box, pixel (0.1 mm) and holes; only the copper masks differ (binary masks by centre sampling, coverage masks by 4 x 4 sub-sampling). For every mask pair the reference on the pixel grid and the imported path
         (flow-based faces) are solved by the program's own `fvm.Network` with a 6 x 6 mm heater (1 W) on the top layer. Reported: the difference of the two readers in copper area per layer, in pixels, and in the heater temperature of every run.
         Run: .venv/bin/python research/gerber-models/scripts/study_import_readers.py (from the repository root; about 5 minutes, needs gerbonara and shapely).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import copy

import numpy as np

import gerber_geometry as gg
import faces as im

HEATER = {"layer": 1, "size": 6.0, "power": 1.0, "x": 33.0, "y": 27.0}


def gerbonara_masks(ib):
    """!
    @brief The copper masks of an imported board drawn by gerbonara + shapely on the same window.
    @param ib Imported board (box, pixel and layer files come from the independent import).
    @return List of (binary, coverage) pairs, rows from the top, one per layer.
    """
    x0, y0, x1, y1 = ib.box
    out = []
    for ly in ib.layers:
        geom, _ = gg.load_copper(ly["path"])
        binary = gg.sample_mask(geom, x0, y1, x1 - x0, y1 - y0, ib.pix) > 0.5
        fine = gg.sample_mask(geom, x0, y1, x1 - x0, y1 - y0, ib.pix / 4) > 0.5
        n = 4
        cov = fine.reshape(fine.shape[0] // n, n, fine.shape[1] // n, n).mean(axis=(1, 3))
        out.append((binary, cov))
    return out


def run(ib, problem, label):
    """!
    @brief The reference and the imported path for the masks of an imported board.
    @param ib Imported board.
    @param problem Problem.
    @param label Name for the report.
    @return Dict with the heater mean rise of the reference and of the imported faces (coverage and binary masks).
    """
    ny, nx = int(round(ib.height / ib.cell)), int(round(ib.width / ib.cell))
    s = HEATER["size"] / 2.0
    sl = (slice(int(HEATER["y"] - s), int(HEATER["y"] + s)), slice(int(HEATER["x"] - s), int(HEATER["x"] + s)))
    ref = im.block_mean(im.solve_fine(ib, problem, "binary"), ib)
    out = {"reference": ref[0][sl].mean()}
    for kind in ("coverage", "binary"):
        faces = im.layer_faces(im.layer_sheets(ib, problem, kind), ib, problem, "flow")
        out[f"flow {kind}"] = im.solve_faces(ib, problem, faces)[0][sl].mean()
    print(f"{label}: " + ", ".join(f"{k} {v:.3f} K" for k, v in out.items()))
    return out


def main():
    """!
    @brief Import with both readers and compare.
    @return None.
    """
    roles = im.roles_of_downloaded("storm")
    ib = im.import_board(roles, pix=0.1, cell=1.0)
    for ly, path in zip(ib.layers, roles["copper"]):
        ly["path"] = path
    problem = im.to_problem(ib, HEATER)
    print(f"{len(ib.holes)} plated holes; box {ib.box}")
    native = {k: [ly[k].copy() for ly in ib.layers] for k in ("binary", "coverage")}
    ours = run(ib, problem, "independent reader")
    gb = gerbonara_masks(ib)
    ib2 = copy.copy(ib)
    ib2.layers = [dict(ly, binary=b, coverage=c) for ly, (b, c) in zip(ib.layers, gb)]
    other = run(ib2, problem, "gerbonara + shapely")
    for l, ly in enumerate(ib.layers):
        a, b = native["binary"][l], gb[l][0]
        print(f"layer {ly['name']}: copper area independent {a.sum() * ib.pix ** 2:.1f} mm2, gerbonara {b.sum() * ib.pix ** 2:.1f} mm2 ({100 * (a.sum() / b.sum() - 1):+.2f} %), pixels that differ {100 * (a ^ b).sum() / (a | b).sum():.2f} % of the union; coverage area difference {100 * (native['coverage'][l].sum() / gb[l][1].sum() - 1):+.2f} %")
    print("difference of the two readers in the temperature of the heater (%): " + ", ".join(f"{k} {100 * (ours[k] / other[k] - 1):+.3f}" for k in ours))


if __name__ == "__main__":
    main()
