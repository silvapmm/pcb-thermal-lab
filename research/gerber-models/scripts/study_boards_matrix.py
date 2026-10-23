"""!
@file study_boards_matrix.py
@brief Every mapping of copper to face conductances on every board we have, in one table: the Stormduino, our IC board, the rectangle board (edges on the cells and between them) and eight synthetic boards (perforated plane, hatched plane, plane with holes, island and ring, random board, diagonal and horizontal tracks, a pads-and-arcs board written by Ucamco's `gerber-writer`).
@details Same protocol as study_mapping_options.py: binary masks at 0.1 mm, 1 mm cells, a 6 x 6 mm heater of 1 W at the centre of the board (at (33, 27) mm on the Stormduino), 10 W/m2K on both faces, insulated edges, the program's FVM through `faces.FaceNetwork`; the error is that of the mean heater rise against the same network on the 0.1 mm pixel grid.
         The synthetic Gerbers are the ones of gerber-import (`make_synthetic.py`, gerbonara's writer, and `study_gerber_writer.py`); they live in gerber-import/data/synthetic. Writes out/boards_matrix.json (used by make_figures.py).
         Run: PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_boards_matrix.py (from the repository root; about 15 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json

import numpy as np

import faces as im
import native_gerber as ng
import our_board
import study_mapping_options as so
from paths import DATA, OUT

SYNTHETIC = (("perforated plane", "plane_perforated.gbr"), ("hatched plane", "hatched.gbr"), ("plane with holes", "plane_holes.gbr"), ("island and ring", "island_and_ring.gbr"),
             ("random board", "random_board.gbr"), ("diagonal tracks", "thin_diagonal.gbr"), ("pads and arcs (gerber-writer)", "gw_traces_arcs.gbr"))


def synthetic_board(file):
    """!
    @brief Import a synthetic Gerber over its own box padded to whole cells.
    @param file File name in gerber-import/data/synthetic.
    @return tuple (ImportedBoard, heater centre (mm)).
    """
    path = DATA / "synthetic" / file
    x0, y0, x1, y1 = [float(v) for v in ng.layer_bbox(path)]
    box = (float(np.floor(x0)) - 1.0, float(np.floor(y0)) - 1.0, float(np.ceil(x1)) + 1.0, float(np.ceil(y1)) + 1.0)
    ib = im.import_board({"copper": [path], "outline": None, "drills": []}, pix=0.1, cell=1.0, box=box)
    return ib, (ib.width / 2.0, ib.height / 2.0)


def main():
    """!
    @brief Run the boards and print the table.
    @return None.
    """
    res = {}
    ib = im.import_board(im.roles_of_downloaded("storm"), pix=0.1, cell=1.0)
    res["Stormduino (2 layers)"] = so.run("Stormduino", ib, (33.0, 27.0))
    g, d = our_board.write(DATA / "synthetic")
    ib = im.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=0.1, cell=1.0, box=(0.0, 0.0, our_board.SIZE, our_board.SIZE))
    res["our IC board"] = so.run("our IC board", ib, (20.0, 20.0))
    for shift in (0.0, 0.4):
        c = (sum(so.rb.heater(shift)[0::2]) / 2.0, sum(so.rb.heater(shift)[1::2]) / 2.0)
        res[f"rectangles, shift {shift}"] = so.run(f"rectangles {shift}", so.rect_import(shift), c)
    for name, file in SYNTHETIC:
        ib, c = synthetic_board(file)
        res[name] = so.run(name, ib, c)
    names = list(res)
    print("\nerror of the mean heater rise against the pixel grid (%), binary masks, 1 mm cells, the program's FVM")
    print(f"{'mapping':14s}" + "".join(f"{n[:16]:>17s}" for n in names) + f"{'mean |err|':>12s}")
    for m in im.METHODS:
        v = [res[n][m] for n in names]
        print(f"{m:14s}" + "".join(f"{x:+17.1f}" for x in v) + f"{np.mean(np.abs(v)):12.1f}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "boards_matrix.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
