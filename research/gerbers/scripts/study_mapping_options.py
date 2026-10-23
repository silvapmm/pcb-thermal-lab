"""!
@file study_mapping_options.py
@brief Every mapping of copper to face conductances as a selectable option, on four boards, through the program's own finite-volume network: the error of the mean heater rise against the same network on the 0.1 mm pixel grid.
@details Boards: the Stormduino (two layers, 109 vias), our IC board (one layer, 16 holes) and the rectangle board of lib/rect_board.py with the copper on the cell edges and 0.4 mm off them (one layer). Binary masks, 1 mm cells, a 6 x 6 mm heater of 1 W on the top layer.
         The mappings are the ones of `importer.METHODS` (fill fraction as the program does, geometric mean, Bruggeman, Hashin-Shtrikman lower and upper, Wiener lower and upper, lambda 0.5, numerical cell problem, flow-based faces).
         This is the comparison asked for as an option of the program (`SolverOptions.copper_mapping` in the design of INTEGRATION.md). Writes out/mapping_options.npz.
         Run: PYTHONPATH=. .venv/bin/python research/gerbers/scripts/study_mapping_options.py (from the repository root; about 5 minutes).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import numpy as np

import importer as im
import our_board
import rect_board as rb
from paths import DATA, OUT

HEATER = {"layer": 1, "size": 6.0, "power": 1.0}


def rect_import(shift):
    """!
    @brief The rectangle board as an ImportedBoard (one layer, no holes).
    @param shift Offset of the features (mm).
    @return ImportedBoard.
    """
    ib = im.ImportedBoard(box=(0.0, 0.0, rb.W, rb.H), pix=0.1, cell=1.0)
    top = rb.mask(shift)[::-1]                                            # rows from the top, as the Gerber masks
    ib.layers.append({"name": "rect", "binary": top.copy(), "coverage": top.astype(float)})
    return ib


def run(label, ib, xy):
    """!
    @brief Reference and every mapping on one board.
    @param label Name for the report.
    @param ib ImportedBoard.
    @param xy Heater centre (mm).
    @return dict method -> error of the mean heater rise (%).
    """
    heater = dict(HEATER, x=xy[0], y=xy[1])
    p = im.to_problem(ib, heater)
    ref = im.block_mean(im.solve_fine(ib, p, "binary"), ib)
    s = 3.0
    sl = (0, slice(int(xy[1] - s), int(xy[1] + s)), slice(int(xy[0] - s), int(xy[0] + s)))
    r = ref[sl].mean()
    out = {}
    sheets = im.layer_sheets(ib, p, "binary")
    for m in im.METHODS:
        f = im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, m))
        out[m] = 100 * (f[sl].mean() / r - 1)
    print(f"{label}: reference mean {r:.1f} K")
    return out


def main():
    """!
    @brief Run the four boards, print the table and save out/mapping_options.npz.
    @return None.
    """
    res = {}
    ib = im.import_board(im.roles_of_downloaded("storm"), pix=0.1, cell=1.0)
    res["Stormduino"] = run("Stormduino", ib, (33.0, 27.0))
    g, d = our_board.write(DATA / "synthetic")
    ib = im.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=0.1, cell=1.0, box=(0.0, 0.0, our_board.SIZE, our_board.SIZE))
    res["our IC board"] = run("our IC board", ib, (20.0, 20.0))
    for shift in (0.0, 0.4):
        c = (sum(rb.heater(shift)[0::2]) / 2.0, sum(rb.heater(shift)[1::2]) / 2.0)
        res[f"rectangles, shift {shift}"] = run(f"rectangle board, shift {shift}", rect_import(shift), c)
    names = list(res)
    print(f"\nerror of the mean heater rise against the pixel grid (%), binary masks, 1 mm cells, the program's FVM")
    print(f"{'mapping':14s}" + "".join(f"{n:>22s}" for n in names))
    for m in im.METHODS:
        print(f"{m:14s}" + "".join(f"{res[n][m]:+22.1f}" for n in names))
    np.savez(OUT / "mapping_options.npz", boards=np.array(names), methods=np.array(im.METHODS), err=np.array([[res[n][m] for m in im.METHODS] for n in names]))


if __name__ == "__main__":
    main()
