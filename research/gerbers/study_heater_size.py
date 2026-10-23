"""!
@file study_heater_size.py
@brief Does the best mapping depend on the size of the heated part? Heaters of 1.2, 3, 6 and 12 mm (square) on the 42 windows of study_mapping.py.
@details Small heaters (a few cells) are the hard case: the part sits on a few cells whose conductance is mapped, and the maximum depends on the copper right under it.
         Cells that do not tile the heater are skipped (1.2 mm only with 0.6 mm cells; 3 mm only with 0.6 and 1.0 mm cells).
         Run: python study_heater_size.py (about 2 minutes).
"""

from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows

PIX = windows.PIX
SIZES = (1.2, 3.0, 6.0, 12.0)                 # mm; the heater starts at 12 mm from the window corner
CELLS = (0.6, 1.0, 2.0)
METHODS = ("arithmetic", "geometric", "lam 0.5", "cellnum", "dual m=0")


def work(args):
    """!
    @brief Every mapping on one window for every heater size.
    @param args Tuple (key, mask).
    @return List of records (size mm, cell mm, method, error of the mean %, error of the maximum %).
    """
    key, mask = args
    S = cd.sheet_of(mask)
    gxr, gyr = cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :])
    out = []
    for size in SIZES:
        a, b = int(round(12.0 / PIX)), int(round((12.0 + size) / PIX))
        T = cd.solve_faces(gxr, gyr, PIX, a, b, a, b)[a:b, a:b]
        rm, rx = T.mean(), T.max()
        for c in CELLS:
            if abs(size / c - round(size / c)) > 1e-9 or abs(12.0 / c - round(12.0 / c)) > 1e-9:
                continue
            n = int(round(c / PIX))
            blk = cd.cell_blocks(S, n)
            f = (blk == cd.S_CU).mean(axis=(2, 3))
            k0, k1 = int(round(12.0 / c)), int(round((12.0 + size) / c))
            cand = {"arithmetic": cd.faces_from_cells(*(2 * [cd.map_power(f, 1.0)])), "geometric": cd.faces_from_cells(*(2 * [cd.map_power(f, 0.0)])),
                    "lam 0.5": cd.faces_from_cells(*cd.map_lambda(blk, 0.5)), "cellnum": cd.faces_from_cells(*cd.map_cell_problem(blk)),
                    "dual m=0": cd.dual_faces(S, n, 0)}
            for name, (gx, gy) in cand.items():
                Tc = cd.solve_faces(gx, gy, c, k0, k1, k0, k1)[k0:k1, k0:k1]
                out.append((size, c, name, 100 * (Tc.mean() / rm - 1), 100 * (Tc.max() / rx - 1)))
    return out


def main():
    """!
    @brief Run all windows and print MAE of the mean and of the maximum (bias of the mean in brackets).
    @return None.
    """
    masks, meta = windows.load()
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(work, [(m[0], masks[i]) for i, m in enumerate(meta)]):
            out += r
    print("MAE of the mean-temperature error % (bias) / MAE of the maximum-temperature error %")
    print(f"{'heater':>8s} {'cell':>5s}" + "".join(f"{m:>24}" for m in METHODS))
    for size in SIZES:
        for c in CELLS:
            rows = [(m, np.array([(o[3], o[4]) for o in out if o[0] == size and o[1] == c and o[2] == m])) for m in METHODS]
            if rows[0][1].size == 0:
                continue
            print(f"{size:6.1f}mm {c:4.1f}" + "".join(f"{np.abs(e[:, 0]).mean():8.1f} ({e[:, 0].mean():+5.1f}) /{np.abs(e[:, 1]).mean():5.1f}" for _, e in rows))


if __name__ == "__main__":
    main()
