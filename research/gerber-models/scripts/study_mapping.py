"""!
@file study_mapping.py
@brief Which way of turning resolved copper into the conductances of a coarse square grid is best?
@details Reference: the 0.1 mm copper mask of a 36 x 36 mm window solved as it is (one copper sheet on laminate, 10 W/m2K on both faces, 1 W on a
         6 x 6 mm block). Coarse grids of 0.6, 1.0 and 2.0 mm cells are built from the SAME mask, so only the mapping is compared (the fidelity of the
         pixels is another question, see study_raster_error.py). 42 windows from 7 real boards (windows.py).
         Error = relative difference of the mean temperature of the heated block (and of its maximum) against the reference.
         Run: .venv/bin/python research/gerber-models/scripts/study_mapping.py (from the repository root)   (about 2 minutes on 4 cores)
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import collections
import json
import time
from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows

CELLS = (0.6, 1.0, 2.0)                                           # mm
PS = (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0)        # exponents of the power mean
LAMS = (0.0, 0.25, 0.5, 0.75, 1.0)                                # weights between the two bounds
HEATER = windows.HEATER


def run_window(args):
    """!
    @brief Every mapping on one window and every cell size.
    @param args Tuple (key string, boolean mask of the window).
    @return List of records (key, cell mm, method, error of the mean %, error of the maximum %).
    """
    key, mask = args
    S = cd.sheet_of(mask)
    pix = windows.PIX
    hs, he = int(HEATER[0] / pix), int(HEATER[1] / pix)
    T = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), pix, hs, he, hs, he)
    ref_mean, ref_max = T[hs:he, hs:he].mean(), T[hs:he, hs:he].max()
    recs = []

    def evaluate(name, c, gx, gy):
        """!@brief Solve the coarse grid and record the error. @return None."""
        k0, k1 = int(round(HEATER[0] / c)), int(round(HEATER[1] / c))
        Tc = cd.solve_faces(gx, gy, c, k0, k1, k0, k1)[k0:k1, k0:k1]
        recs.append((key, c, name, 100 * (Tc.mean() / ref_mean - 1), 100 * (Tc.max() / ref_max - 1)))

    for c in CELLS:
        n = int(round(c / pix))
        blk = cd.cell_blocks(S, n)
        f = (blk == cd.S_CU).mean(axis=(2, 3))
        for p in PS:
            Sc = cd.map_power(f, p)
            evaluate(f"pmean {p:+.2f}", c, *cd.faces_from_cells(Sc, Sc))
        for lam in LAMS:
            evaluate(f"lam {lam:.2f}", c, *cd.faces_from_cells(*cd.map_lambda(blk, lam)))
        evaluate("cellnum", c, *cd.faces_from_cells(*cd.map_cell_problem(blk)))
        for m in sorted({0, n // 4, n // 2}):
            evaluate(f"dual m/n={m / n:.2f}", c, *cd.dual_faces(S, n, m))
    return recs


def normalise(name):
    """!
    @brief Group the dual variants whose margin differs only by the rounding of n/4.
    @param name Method name of a record.
    @return Grouped name.
    """
    if name.startswith("dual"):
        f = float(name.split("=")[1])
        return "dual m/n=0" if f == 0 else ("dual m/n=0.5" if f >= 0.5 else "dual m/n~0.2")
    return name


def summarise(records):
    """!
    @brief Print the tables: error by method and cell size, best per size and per board.
    @param records List of records of run_window.
    @return None.
    """
    by = collections.defaultdict(list)
    for key, c, name, em, ex in records:
        by[(normalise(name), c)].append((em, ex, key.split(":")[0]))
    names = sorted({n for n, _ in by}, key=lambda s: (s.split()[0] != "pmean", s.split()[0], s))
    print("MAE of the mean-temperature error / MAE of the maximum / bias (mean signed error) / worst window, in %")
    print(f"{'method':14s} | " + " | ".join(f"{c} mm cells".center(27) for c in CELLS) + " | mean MAE")
    for n in names:
        cells, tot = [], []
        for c in CELLS:
            a = np.array([(x[0], x[1]) for x in by[(n, c)]])
            tot.append(np.abs(a[:, 0]).mean())
            cells.append(f"{np.abs(a[:, 0]).mean():5.1f}/{np.abs(a[:, 1]).mean():5.1f} {a[:, 0].mean():+5.1f} {np.abs(a[:, 0]).max():5.1f}")
        print(f"{n:14s} | " + " | ".join(f"{x:>27s}" for x in cells) + f" | {np.mean(tot):5.2f}")
    print("\nBest per cell size (MAE of the mean):")
    for c in CELLS:
        best = sorted((np.abs([x[0] for x in by[(n, c)]]).mean(), n) for n in names)[:4]
        print(f"  {c} mm:", ", ".join(f"{n} {m:.2f}" for m, n in best))
    sel = ["pmean +1.00", "pmean +0.00", "lam 0.50", "cellnum", "dual m/n=0", "dual m/n=0.5"]
    print("\nPer board, MAE of the mean-temperature error over the three cell sizes:")
    print(f"{'board':9s}" + "".join(f"{s:>14s}" for s in sel))
    for b in sorted({x[2] for v in by.values() for x in v}):
        print(f"{b:9s}" + "".join(f"{np.mean([abs(x[0]) for c in CELLS for x in by[(s, c)] if x[2] == b]):14.1f}" for s in sel))


def main():
    """!
    @brief Run all windows in 4 processes and print the summary.
    @return None.
    """
    masks, meta = windows.load()
    tasks = [(f"{m[0]}:{m[1]},{m[2]}", masks[i]) for i, m in enumerate(meta)]
    t0 = time.time()
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(run_window, tasks):
            out += r
    windows.OUT.mkdir(exist_ok=True)
    json.dump(out, open(windows.OUT / "mapping_records.json", "w"))
    print(f"{len(tasks)} windows, {len(out)} records, {time.time() - t0:.0f} s\n")
    summarise(out)


if __name__ == "__main__":
    main()
