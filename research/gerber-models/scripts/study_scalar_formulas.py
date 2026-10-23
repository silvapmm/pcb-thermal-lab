"""!
@file study_scalar_formulas.py
@brief Scalar mappings from the copper fraction alone: arithmetic, geometric, Bruggeman and the Hashin-Shtrikman bounds, on the 42 windows of study_mapping.py.
@details All of them are one number per cell computed from the fill fraction f (no mask needed), so they could replace the program's formula as they are.
         Run: .venv/bin/python research/gerber-models/scripts/study_scalar_formulas.py (from the repository root) (about 1 minute).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows
from study_mapping import CELLS, HEATER

FORMULAS = {
    "arithmetic (today)": lambda f: cd.map_power(f, 1.0),
    "geometric": lambda f: cd.map_power(f, 0.0),
    "Bruggeman 2D": cd.map_bruggeman,
    "HS lower": lambda f: cd.map_hashin_shtrikman(f, "lower"),
    "HS upper": lambda f: cd.map_hashin_shtrikman(f, "upper"),
    "HS mean (geometric)": lambda f: np.sqrt(cd.map_hashin_shtrikman(f, "lower") * cd.map_hashin_shtrikman(f, "upper")),
    "harmonic": lambda f: cd.map_power(f, -1.0),
}


def work(args):
    """!
    @brief Every formula on one window and every cell size.
    @param args Tuple (key, mask).
    @return List of records (cell mm, formula, error of the mean %, error of the maximum %).
    """
    key, mask = args
    pix = windows.PIX
    S = cd.sheet_of(mask)
    hs, he = int(HEATER[0] / pix), int(HEATER[1] / pix)
    T = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), pix, hs, he, hs, he)
    rm, rx = T[hs:he, hs:he].mean(), T[hs:he, hs:he].max()
    out = []
    for c in CELLS:
        n = int(round(c / pix))
        f = (cd.cell_blocks(S, n) == cd.S_CU).mean(axis=(2, 3))
        k0, k1 = int(round(HEATER[0] / c)), int(round(HEATER[1] / c))
        for name, fn in FORMULAS.items():
            sc = fn(f)
            Tc = cd.solve_faces(*cd.faces_from_cells(sc, sc), c, k0, k1, k0, k1)[k0:k1, k0:k1]
            out.append((c, name, 100 * (Tc.mean() / rm - 1), 100 * (Tc.max() / rx - 1)))
    return out


def main():
    """!
    @brief Run all windows and print the MAE and the bias of every formula.
    @return None.
    """
    masks, meta = windows.load()
    tasks = [(f"{m[0]}", masks[i]) for i, m in enumerate(meta)]
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(work, tasks):
            out += r
    print("MAE of the mean-temperature error % (bias in brackets); the maximum-temperature MAE follows")
    print(f"{'formula':22s}" + "".join(f"{c:>26}" for c in CELLS))
    for name in FORMULAS:
        cells = []
        for c in CELLS:
            e = np.array([(x[2], x[3]) for x in out if x[0] == c and x[1] == name])
            cells.append(f"{np.abs(e[:, 0]).mean():5.1f} ({e[:, 0].mean():+5.1f}) / {np.abs(e[:, 1]).mean():5.1f}")
        print(f"{name:22s}" + "".join(f"{x:>26}" for x in cells))


if __name__ == "__main__":
    main()
