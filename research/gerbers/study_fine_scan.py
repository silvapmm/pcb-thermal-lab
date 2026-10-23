"""!
@file study_fine_scan.py
@brief Fine scan of the two cheap parameters of the mapping on the 42 windows of study_mapping.py.
@details p: exponent of the power mean of the two phases, from the copper fraction alone (p = 0 is the geometric mean, p = 1 the program's fill fraction).
         lam: weight between the two bounds of Wiener (0.5 = their geometric mean). Run: python study_fine_scan.py (about 2 minutes).
"""

from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows
from study_mapping import CELLS, HEATER

PS = tuple(np.round(np.arange(-0.30, 0.31, 0.05), 2))
LAMS = tuple(np.round(np.arange(0.30, 0.91, 0.10), 2))


def work(args):
    """!
    @brief The scan on one window.
    @param args Tuple (key, mask).
    @return List of records (key, cell mm, method, error of the mean %).
    """
    key, mask = args
    pix = windows.PIX
    S = cd.sheet_of(mask)
    hs, he = int(HEATER[0] / pix), int(HEATER[1] / pix)
    T = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), pix, hs, he, hs, he)
    ref = T[hs:he, hs:he].mean()
    out = []
    for c in CELLS:
        n = int(round(c / pix))
        blk = cd.cell_blocks(S, n)
        k0, k1 = int(round(HEATER[0] / c)), int(round(HEATER[1] / c))
        f = (blk == cd.S_CU).mean(axis=(2, 3))

        def ev(name, gx, gy):
            """!@brief Solve the coarse grid and record the error. @return None."""
            Tc = cd.solve_faces(gx, gy, c, k0, k1, k0, k1)[k0:k1, k0:k1]
            out.append((key, c, name, 100 * (Tc.mean() / ref - 1)))

        for p in PS:
            Sc = cd.map_power(f, float(p))
            ev(f"p {p:+.2f}", *cd.faces_from_cells(Sc, Sc))
        for lam in LAMS:
            ev(f"lam {lam:.2f}", *cd.faces_from_cells(*cd.map_lambda(blk, float(lam))))
    return out


def main():
    """!
    @brief Run the scan and print the MAE and the bias of every parameter value.
    @return None.
    """
    masks, meta = windows.load()
    tasks = [(f"{m[0]}:{m[1]},{m[2]}", masks[i]) for i, m in enumerate(meta)]
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(work, tasks):
            out += r
    by = {}
    for key, c, name, e in out:
        by.setdefault((name, c), []).append(e)
    print("MAE (%) of the mean-temperature error, signed bias in brackets")
    print(f"{'param':10s}" + "".join(f"{c:>20}" for c in CELLS) + f"{'avg MAE':>10}")
    for n in sorted({n for n, _ in by}):
        row = [(np.abs(by[(n, c)]).mean(), np.mean(by[(n, c)])) for c in CELLS]
        print(f"{n:10s}" + "".join(f"{a:10.2f} ({b:+5.1f})" for a, b in row) + f"{np.mean([a for a, _ in row]):10.2f}")


if __name__ == "__main__":
    main()
