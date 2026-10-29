#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_validation_boards.py
@brief The converter on every board we have, layer by layer: the copper area, the connected pieces, the holes and the time of the independent reader against gerbonara + shapely (the vector truth), at two pixel sizes and with a coverage mask.
@details Boards: the eight of data/ (`storm`, `chibi`, `easyeda`, `pcbrnd`, `pcad`, `dip`, `fritz`, `alleg`; from one to four copper layers). For each copper layer the reference is the area of the gerbonara + shapely union clipped to the board box (an exact vector
         area, the polygons not being rasterised); the readings are the binary mask of the independent reader at 0.1 mm and 0.05 mm and the coverage mask (4 x 4 sub-samples) at 0.1 mm. The pieces are the 8-connected pieces of the 0.05 mm mask against the
         polygons of the vector union, and the holes are the plated holes of the drill file against gerbonara's. Writes out/validation_boards.json (used by make_figures.py) and prints the table of README section 4.41.
         Run: .venv/bin/python research/gerber-import/scripts/study_validation_boards.py (from the repository root; about 3 minutes, needs gerbonara and shapely).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import json
import time

import numpy as np
from scipy import ndimage
from shapely.geometry import box as sbox

import gerber_geometry as gg
import importer
import readers
from paths import OUT

BOARDS = ("storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz", "alleg")
LAYER_NAMES = ("F", "L2", "L3", "L4", "L5", "B")


def pieces(geom):
    """!
    @brief Number of separate polygons of a shapely geometry.
    @param geom Geometry.
    @return int Count.
    """
    return len(geom.geoms) if hasattr(geom, "geoms") else (0 if geom.is_empty else 1)


def run_board(name):
    """!
    @brief Run the readers on every copper layer of a board.
    @param name Board key.
    @return list of dicts, one per layer.
    """
    roles = importer.roles_of_downloaded(name)
    present = [k for k in LAYER_NAMES if k in readers.board_files(name)]          # the role of every copper file, top first
    out = []
    ibs = {}
    for pix in (0.1, 0.05):
        t = time.time()
        ibs[pix] = (importer.import_board(roles, pix=pix, cell=pix), time.time() - t)
    ib01, t01 = ibs[0.1]
    ib005, t005 = ibs[0.05]
    x0, y0, x1, y1 = ib01.box
    clip = sbox(x0, y0, x1, y1)
    for k, path in enumerate(roles["copper"]):
        t = time.time()
        geom = gg.load_copper(path)[0].intersection(clip)
        tv = time.time() - t
        vec = geom.area
        a01 = ib01.layers[k]["binary"].sum() * 0.1 ** 2
        a005 = ib005.layers[k]["binary"].sum() * 0.05 ** 2
        acov = ib01.layers[k]["coverage"].sum() * 0.1 ** 2
        lab, n = ndimage.label(ib005.layers[k]["binary"], structure=np.ones((3, 3)))
        out.append({"board": name, "layer": present[k], "vector_mm2": vec, "err_bin_0.1": 100 * (a01 / vec - 1), "err_bin_0.05": 100 * (a005 / vec - 1),
                    "err_cov_0.1": 100 * (acov / vec - 1), "pieces_native": int(n), "pieces_vector": pieces(geom), "t_native_s": (t01 + t005) / 2 / len(roles["copper"]), "t_vector_s": tv})
    holes_native = len(ib01.holes)
    holes_gerbonara = None
    if roles["drills"]:
        try:
            hg = [h for h in gg.drill_holes(roles["drills"][0]) if x0 <= h[0] <= x1 and y0 <= h[1] <= y1]
            holes_gerbonara = len(hg)
        except SyntaxError:                                      # gerbonara refuses an Allegro drill file that carries no number format
            holes_gerbonara = "refused"
    for r in out:
        r["holes_native"], r["holes_gerbonara"] = holes_native, holes_gerbonara
    return out


def main():
    """!
    @brief Run all the boards, print the table and save out/validation_boards.json.
    @return None.
    """
    rows = []
    for b in BOARDS:
        rows += run_board(b)
        print(f"{b} done", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "validation_boards.json").write_text(json.dumps(rows, indent=1))
    print(f"\n{'board':8s} {'layer':5s} {'vector mm2':>10s} {'bin 0.1':>9s} {'bin 0.05':>9s} {'cov 0.1':>9s} {'pieces (ours/vector)':>21s} {'holes (ours/gerbonara)':>23s}")
    for r in rows:
        h = f"{r['holes_native']}/{r['holes_gerbonara']}" if r["holes_gerbonara"] is not None else f"{r['holes_native']}/-"
        print(f"{r['board']:8s} {r['layer']:5s} {r['vector_mm2']:10.1f} {r['err_bin_0.1']:+8.2f}% {r['err_bin_0.05']:+8.2f}% {r['err_cov_0.1']:+8.2f}% {r['pieces_native']:>10d}/{r['pieces_vector']:<10d} {h:>23s}")
    a = np.array([[abs(r["err_bin_0.1"]), abs(r["err_bin_0.05"]), abs(r["err_cov_0.1"])] for r in rows])
    print(f"\nmean absolute area error over {len(rows)} layers: binary 0.1 mm {a[:, 0].mean():.2f} %, binary 0.05 mm {a[:, 1].mean():.2f} %, coverage 0.1 mm {a[:, 2].mean():.2f} % (maximum {a.max(axis=0).round(2).tolist()})")


if __name__ == "__main__":
    main()
