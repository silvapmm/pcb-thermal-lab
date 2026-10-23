"""!
@file study_two_layer.py
@brief Validate the mappings on a two-layer board with plated holes (Stormduino, an Arduino Uno clone).
@details Reference: both copper layers resolved at 0.1 mm, FR-4 between them (0.3 W/mK through, 1.53 mm), every drilled hole a copper barrel (25 um plating)
         joining the layers, 10 W/m2K on the two outer faces, 1 W on a 6 x 6 mm block of the top layer at three random places.
         Coarse grids of 0.6, 1.0 and 2.0 mm built from the same masks (the board is cut to 66 x 48 mm so that all the grids tile it).
         Run: .venv/bin/python research/gerbers/scripts/study_two_layer.py (from the repository root)   (about 3 minutes)
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math
import time

import numpy as np

import conduction as cd
import readers

K_TH, D_GAP = 0.3, 1.53e-3          # FR-4 through-plane conductivity (W/mK) and the gap between the two copper layers (m)
T_PLATE = 25e-6                     # plating of a barrel (m)
PIX = 0.1                           # mm
ROWS, COLS = 480, 660               # pixels kept (multiples of 60 so that 0.6, 1.0 and 2.0 mm cells tile them)
BLOCK = 60                          # heater block in pixels (6 mm)


def barrel_conductance(d_mm):
    """!
    @brief Conductance of one plated barrel between the two layers.
    @param d_mm Drill diameter (mm).
    @return W/K.
    """
    r = d_mm * 1e-3 / 2
    return cd.K_CU * math.pi * (r ** 2 - (r - T_PLATE) ** 2) / D_GAP


def vertical_conductance(holes, x_left, y_top, cell, shape):
    """!
    @brief Vertical conductance per cell: FR-4 over the whole cell plus the barrels whose centre falls in it.
    @param holes List of (x, y, diameter) in mm.
    @param x_left X of the left edge of the grid (mm).
    @param y_top Y of the top edge of the grid (mm).
    @param cell Cell size (mm).
    @param shape Grid shape (ny, nx).
    @return Array (ny, nx) in W/K.
    """
    ny, nx = shape
    g = np.full(shape, K_TH * (cell * 1e-3) ** 2 / D_GAP)
    for x, y, d in holes:
        i, j = int((y_top - y) / cell), int((x - x_left) / cell)
        if 0 <= i < ny and 0 <= j < nx:
            g[i, j] += barrel_conductance(d)
    return g


def mapping(name, S, n):
    """!
    @brief Face conductances of one layer for a named mapping.
    @param name "iso p=1", "geo p=0", "lam 0.5", "lam 0.6", "cellnum", or "dual m=<rows>".
    @param S Pixel sheet conductances of the layer.
    @param n Pixels per cell side.
    @return Tuple (gx, gy).
    """
    blk = cd.cell_blocks(S, n)
    f = (blk == cd.S_CU).mean(axis=(2, 3))
    if name == "iso p=1":
        sc = cd.map_power(f, 1.0)
        return cd.faces_from_cells(sc, sc)
    if name == "geo p=0":
        sc = cd.map_power(f, 0.0)
        return cd.faces_from_cells(sc, sc)
    if name.startswith("lam"):
        return cd.faces_from_cells(*cd.map_lambda(blk, float(name.split()[1])))
    if name == "cellnum":
        return cd.faces_from_cells(*cd.map_cell_problem(blk))
    return cd.dual_faces(S, n, int(name.split("=")[1]))


def main():
    """!
    @brief Build the reference, then every mapping at every cell size; print the errors.
    @return None.
    """
    t0 = time.time()
    files = readers.board_files("storm")
    holes = readers.holes(files["drill"])
    x0, y0, x1, y1 = readers.box(files["edge"], files["F"])
    S = {l: cd.sheet_of(readers.render(files[l], x0, y1, COLS * PIX, ROWS * PIX, PIX)) for l in "FB"}
    gz = vertical_conductance(holes, x0, y1, PIX, (ROWS, COLS))
    gx = np.stack([cd.harm(S[l][:, :-1], S[l][:, 1:]) for l in "FB"])
    gy = np.stack([cd.harm(S[l][:-1, :], S[l][1:, :]) for l in "FB"])
    rng = np.random.default_rng(3)
    places = []
    mask_top = S["F"] == cd.S_CU
    while len(places) < 3:                                  # random 6 x 6 mm blocks of the top layer with 20..90 % of copper
        a, b = int(rng.integers(1, 7)), int(rng.integers(1, 10))
        if 0.2 < mask_top[a * BLOCK:(a + 1) * BLOCK, b * BLOCK:(b + 1) * BLOCK].mean() < 0.9 and (a, b) not in places:
            places.append((a, b))
    ref = {}
    for a, b in places:
        T = cd.solve_two_layers(gx, gy, gz, PIX, np.arange(a * BLOCK, (a + 1) * BLOCK), np.arange(b * BLOCK, (b + 1) * BLOCK))
        p = T[0][a * BLOCK:(a + 1) * BLOCK, b * BLOCK:(b + 1) * BLOCK]
        ref[(a, b)] = (p.mean(), p.max())
        print(f"reference, block {(a, b)}: top mean {p.mean():.2f} K, max {p.max():.2f} K ({time.time() - t0:.0f} s)", flush=True)

    print("\nerror of the mean / of the maximum of the heated block; MAE of the mean")
    print(f"{'method':12s}| cell | " + " | ".join(f"block {pl}".rjust(22) for pl in places) + " | MAE")
    for c in (0.6, 1.0, 2.0):
        n = int(round(c / PIX))
        k = BLOCK // n
        gzc = vertical_conductance(holes, x0, y1, c, (ROWS // n, COLS // n))
        for name in ("iso p=1", "geo p=0", "lam 0.5", "lam 0.6", "cellnum", "dual m=0", f"dual m={n // 5}"):
            faces = [mapping(name, S[l], n) for l in "FB"]
            gxc, gyc = np.stack([f[0] for f in faces]), np.stack([f[1] for f in faces])
            errs, txt = [], []
            for a, b in places:
                T = cd.solve_two_layers(gxc, gyc, gzc, c, np.arange(a * k, (a + 1) * k), np.arange(b * k, (b + 1) * k))[0][a * k:(a + 1) * k, b * k:(b + 1) * k]
                em, ex = 100 * (T.mean() / ref[(a, b)][0] - 1), 100 * (T.max() / ref[(a, b)][1] - 1)
                errs.append(abs(em))
                txt.append(f"{em:+5.1f} / {ex:+5.1f} %")
            print(f"{name:12s}| {c:3.1f}  | " + " | ".join(t.rjust(22) for t in txt) + f" | {np.mean(errs):4.1f} %", flush=True)
    print(f"total {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
