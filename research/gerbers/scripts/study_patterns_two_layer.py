"""!
@file study_patterns_two_layer.py
@brief The patterns of study_patterns.py on a two-layer board as the program models it: a patterned top layer over a full plane or over bare laminate.
@details The program's own formula for the layer phases (copper phase k_cu t_cu + k_lam (slab - t_cu), laminate phase k_lam slab, slab 0.8 mm of a 1.6 mm board), FR-4 0.3 W/mK through the
         1.53 mm gap, 10 W/m2K on the two outer faces, 1 W on a 6 x 6 mm block of the top layer. The top-layer patterns have about 50 % of copper: stripes at 0, 45 and 90 degrees,
         cross-hatch, isolated squares, a perforated plane (pitch 1 mm). The question asked: what does a uniform "fill 0.5" mean for the temperature, and which mapping is right
         for each real pattern? Reported: the error of the block-mean temperature of each mapping against the resolved pattern. Run: .venv/bin/python research/gerbers/scripts/study_patterns_two_layer.py (from the repository root) (about 4 minutes).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math
from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows

PIX = windows.PIX
CELLS = (0.6, 1.0)
TC, SLAB, GAP = cd.T_CU, 0.8e-3, 1.53e-3
A_PH, B_PH = cd.K_CU * TC + cd.K_LAM * (SLAB - TC), cd.K_LAM * SLAB
GZ_AREA = 0.3 / GAP                       # W/m2K through the dielectric
METHODS = ("arithmetic (today)", "geometric", "lam 0.5", "dual m=0")


def patterns():
    """!
    @brief The top-layer patterns (about 50 % copper, pitch 1 mm).
    @return List of (label, mask).
    """
    n = int(round(windows.WIN / PIX))
    c = (np.arange(n) + 0.5) * PIX
    X, Y = np.meshgrid(c, c)
    P = 1.0
    out = []
    for theta in (0, 45, 90):
        a = math.radians(theta)
        out.append((f"stripes {theta} deg", np.mod(X * math.cos(a) + Y * math.sin(a), P) < 0.5 * P))
    out.append(("cross-hatch", (np.mod(X, P) < 0.3 * P) | (np.mod(Y, P) < 0.3 * P)))
    out.append(("isolated squares", (np.mod(X, P) < 0.7 * P) & (np.mod(Y, P) < 0.7 * P)))
    dx, dy = np.mod(X, P) - P / 2, np.mod(Y, P) - P / 2
    out.append(("perforated plane", dx * dx + dy * dy > (0.4 * P) ** 2))
    return out


def run(args):
    """!
    @brief One pattern over one bottom layer: reference and every mapping.
    @param args Tuple (label, mask, bottom "plane" or "none").
    @return List of records (label, bottom, copper fraction, cell mm, method, error of the mean %).
    """
    label, mask, bottom = args
    n_px = mask.shape[0]
    top = np.where(mask, A_PH, B_PH)
    bot = np.full(mask.shape, A_PH if bottom == "plane" else B_PH)
    S = [top, bot]
    hs, he = int(12 / PIX), int(18 / PIX)
    gx = np.stack([cd.harm(s[:, :-1], s[:, 1:]) for s in S])
    gy = np.stack([cd.harm(s[:-1, :], s[1:, :]) for s in S])
    gz = np.full(mask.shape, GZ_AREA * (PIX * 1e-3) ** 2)
    ref = cd.solve_two_layers(gx, gy, gz, PIX, np.arange(hs, he), np.arange(hs, he))[0][hs:he, hs:he].mean()
    out = []
    for c in CELLS:
        n = int(round(c / PIX))
        k0, k1 = int(round(12 / c)), int(round(18 / c))
        gzc = np.full((n_px // n, n_px // n), GZ_AREA * (c * 1e-3) ** 2)
        blk_t = cd.cell_blocks(top, n)
        f = (blk_t == A_PH).mean(axis=(2, 3))
        faces_top = {"arithmetic (today)": cd.faces_from_cells(*(2 * [cd.map_power(f, 1.0, A_PH, B_PH)])), "geometric": cd.faces_from_cells(*(2 * [cd.map_power(f, 0.0, A_PH, B_PH)])),
                     "lam 0.5": cd.faces_from_cells(*cd.map_lambda(blk_t, 0.5)), "dual m=0": cd.dual_faces(top, n, 0)}
        sb = bot[:gzc.shape[0] * n:n, :gzc.shape[1] * n:n]
        gbx, gby = cd.faces_from_cells(sb, sb)
        for name, (tx, ty) in faces_top.items():
            T = cd.solve_two_layers(np.stack([tx, gbx]), np.stack([ty, gby]), gzc, c, np.arange(k0, k1), np.arange(k0, k1))[0][k0:k1, k0:k1].mean()
            out.append((label, bottom, float(mask.mean()), c, name, 100 * (T / ref - 1)))
    return out


def main():
    """!
    @brief Run every pattern over both bottom layers and print the errors.
    @return None.
    """
    tasks = [(l, m, b) for l, m in patterns() for b in ("plane", "none")]
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(run, tasks):
            out += r
    print("error of the block-mean temperature of the top layer (%), mapping against the resolved pattern")
    for bottom in ("plane", "none"):
        for c in CELLS:
            print(f"\nbottom: {bottom}, cells {c} mm" + "".join(f"{m:>20}" for m in METHODS))
            for label in dict.fromkeys(o[0] for o in out):
                row = "".join(f"{[o[5] for o in out if o[0] == label and o[1] == bottom and o[3] == c and o[4] == m][0]:+19.1f} " for m in METHODS)
                cu = [o[2] for o in out if o[0] == label][0]
                print(f"  {label:18s} (copper {cu:.2f})" + row)


if __name__ == "__main__":
    main()
