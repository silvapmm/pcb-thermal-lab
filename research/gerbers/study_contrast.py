"""!
@file study_contrast.py
@brief Does the best mapping depend on the copper thickness (the contrast between copper and laminate)?
@details Fill-fraction average, geometric mean and the bounds mapping with lambda 0.4 to 0.7, on the 42 windows, for 18, 35, 70 and 140 um of copper
         on 1.6 mm of FR-4 (contrast S_copper / S_laminate = 4.8, 9.4, 18.7, 37.4). Run: python study_contrast.py (about 6 minutes).
"""

from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows
from study_mapping import CELLS, HEATER

THICKNESSES_UM = (18, 35, 70, 140)


def work(args):
    """!
    @brief The comparison on one window for one copper thickness.
    @param args Tuple ((key, mask), copper thickness in um).
    @return List of records (thickness, cell mm, method, error of the mean %).
    """
    (key, mask), t_um = args
    s_cu = cd.K_CU * t_um * 1e-6
    pix = windows.PIX
    S = cd.sheet_of(mask, s_cu)
    hs, he = int(HEATER[0] / pix), int(HEATER[1] / pix)
    T = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), pix, hs, he, hs, he)
    ref = T[hs:he, hs:he].mean()
    out = []
    for c in CELLS:
        n = int(round(c / pix))
        blk = cd.cell_blocks(S, n)
        f = (blk == s_cu).mean(axis=(2, 3))
        k0, k1 = int(round(HEATER[0] / c)), int(round(HEATER[1] / c))
        iso = cd.map_power(f, 1.0, s_cu)
        geo = cd.map_power(f, 0.0, s_cu)
        cand = {"iso": (iso, iso), "geo": (geo, geo), "lam 0.4": cd.map_lambda(blk, 0.4), "lam 0.5": cd.map_lambda(blk, 0.5), "lam 0.6": cd.map_lambda(blk, 0.6), "lam 0.7": cd.map_lambda(blk, 0.7)}
        for name, (sx, sy) in cand.items():
            Tc = cd.solve_faces(*cd.faces_from_cells(sx, sy), c, k0, k1, k0, k1)[k0:k1, k0:k1]
            out.append((t_um, c, name, 100 * (Tc.mean() / ref - 1)))
    return out


def main():
    """!
    @brief Run every window for every thickness and print the MAE and the bias.
    @return None.
    """
    masks, meta = windows.load()
    wins = [(f"{m[0]}:{m[1]},{m[2]}", masks[i]) for i, m in enumerate(meta)]
    out = []
    with Pool(4) as pool:
        for t in THICKNESSES_UM:
            for r in pool.imap_unordered(work, [(w, t) for w in wins]):
                out += r
    by = {}
    for t, c, name, e in out:
        by.setdefault((t, name, c), []).append(e)
    print("MAE (%) of the mean-temperature error (bias in brackets); contrast = S_copper / S_laminate")
    print(f"{'copper':>8s} {'contrast':>8s} {'method':8s}" + "".join(f"{c:>16}" for c in CELLS))
    for t in THICKNESSES_UM:
        for name in ("iso", "geo", "lam 0.4", "lam 0.5", "lam 0.6", "lam 0.7"):
            print(f"{t:6d}um {cd.K_CU * t * 1e-6 / cd.S_LAM:8.1f} {name:8s}" + "".join(f"{np.abs(by[(t, name, c)]).mean():9.1f} ({np.mean(by[(t, name, c)]):+5.1f})" for c in CELLS))


if __name__ == "__main__":
    main()
