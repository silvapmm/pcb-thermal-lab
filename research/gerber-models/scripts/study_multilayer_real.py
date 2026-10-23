"""!
@file study_multilayer_real.py
@brief The mappings on a real four-layer board (Cadence Allegro, inner planes, 283 plated holes) with the typical 4-layer stack-up of the program, thin and thick copper.
@details Six random 30 x 30 mm windows inside the drilled area of the board "alleg". Layers: top, GND plane, VCC plane, bottom (the Gerber files, drawn by native_gerber.py).
         Stack-up of pcbthermal/data/stackups.json (4 layers, JLCPCB): copper 35 / 15.2 / 15.2 / 35 um, FR-4 gaps 210.4 / 1065 / 210.4 um, 0.3 W/mK through and 0.9 in plane;
         each layer node is its copper plus half of the adjacent gaps (the program's advanced stack-up); the copper phase of a layer conducts k_cu t_cu + k_lam (slab - t_cu), the laminate
         phase k_lam slab. Every plated hole is a copper barrel (25 um plating) across all the gaps. 10 W/m2K on the two outer faces. Heater: 1 W on a 6 x 6 mm block of the top layer.
         Variant "heavy": 70 / 35 / 35 / 70 um copper. Reference: all four layers resolved at 0.1 mm (360 000 unknowns). Run: .venv/bin/python research/gerber-models/scripts/study_multilayer_real.py (from the repository root) (about 10 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import math
import time
from multiprocessing import Pool

import numpy as np

import conduction as cd
import readers
import native_gerber as ng

PIX = 0.1
WIN = 30.0
GAPS_UM = (210.4, 1065.0, 210.4)
STACKS = {"1 oz outer / 0.5 oz inner": (35.0, 15.2, 15.2, 35.0), "2 oz outer / 1 oz inner": (70.0, 35.0, 35.0, 70.0)}
K_TH, K_LAM, PLATING = 0.3, 0.9, 25e-6
CELLS = (0.6, 1.0, 2.0)
METHODS = ("arithmetic", "geometric", "lam 0.5", "lam 0.7", "lam 0.9", "cellnum", "dual m=0")


def phases(copper_um):
    """!
    @brief Conductance of the copper phase and of the laminate phase of every layer node, and the gaps in metres.
    @param copper_um Copper thickness of every layer (um).
    @return Tuple (list of (a, b) per layer in W/K, gaps array in m).
    """
    tc = np.array(copper_um) * 1e-6
    gaps = np.array(GAPS_UM) * 1e-6
    out = []
    for l in range(len(tc)):
        slab = tc[l] + (gaps[l - 1] / 2 if l > 0 else 0.0) + (gaps[l] / 2 if l < len(gaps) else 0.0)
        out.append((cd.K_CU * tc[l] + K_LAM * (slab - tc[l]), K_LAM * slab))
    return out, gaps


def via_conductance(holes, x_left, y_top, cell, shape, gaps):
    """!
    @brief Vertical conductance of every cell and gap: the FR-4 plus the plated barrels whose centre is in the cell.
    @param holes Plated holes (x, y, diameter) in mm.
    @param x_left X of the left edge (mm).
    @param y_top Y of the top edge (mm).
    @param cell Cell size (mm).
    @param shape Grid shape (ny, nx).
    @param gaps Gap thicknesses (m).
    @return Array (gaps, ny, nx) in W/K.
    """
    ny, nx = shape
    g = np.stack([np.full(shape, K_TH * (cell * 1e-3) ** 2 / d) for d in gaps])
    for x, y, d in holes:
        i, j = int((y_top - y) / cell), int((x - x_left) / cell)
        if 0 <= i < ny and 0 <= j < nx:
            r = d * 1e-3 / 2
            area = math.pi * (r * r - max(r - PLATING, 0.0) ** 2)
            g[:, i, j] += cd.K_CU * area / gaps
    return g


def faces(name, S, n, a, b):
    """!
    @brief Face conductances of one layer for a named mapping.
    @param name Method name of METHODS.
    @param S Pixel sheet conductances of the layer.
    @param n Pixels per cell side.
    @param a Conductance of the copper phase of this layer.
    @param b Conductance of the laminate phase of this layer.
    @return Tuple (gx, gy).
    """
    blk = cd.cell_blocks(S, n)
    f = (blk == a).mean(axis=(2, 3))
    if name == "arithmetic":
        s = cd.map_power(f, 1.0, a, b)
        return cd.faces_from_cells(s, s)
    if name == "geometric":
        s = cd.map_power(f, 0.0, a, b)
        return cd.faces_from_cells(s, s)
    if name.startswith("lam"):
        return cd.faces_from_cells(*cd.map_lambda(blk, float(name.split()[1])))
    if name == "cellnum":
        return cd.faces_from_cells(*cd.map_cell_problem(blk))
    return cd.dual_faces(S, n, 0)


def work(args):
    """!
    @brief One window and one stack-up: the reference and every mapping at every cell size.
    @param args Tuple (stack name, copper um, window origin (ox, oy), plated holes of the window, layer masks (4, 360, 360)).
    @return List of records (stack name, cell mm, method, error of the mean %, error of the maximum %).
    """
    name, copper, (ox, oy), holes, masks = args
    ph, gaps = phases(copper)
    S = [np.where(m, a, b) for m, (a, b) in zip(masks, ph)]
    L, ny, nx = len(S), masks.shape[1], masks.shape[2]
    hs, he = int(12 / PIX), int(18 / PIX)
    gx = np.stack([cd.harm(s[:, :-1], s[:, 1:]) for s in S])
    gy = np.stack([cd.harm(s[:-1, :], s[1:, :]) for s in S])
    gz = via_conductance(holes, ox, oy + WIN, PIX, (ny, nx), gaps)
    T = cd.solve_stack(gx, gy, gz, PIX, np.arange(hs, he), np.arange(hs, he))[0][hs:he, hs:he]
    rm, rx = T.mean(), T.max()
    out = []
    for c in CELLS:
        n = int(round(c / PIX))
        gzc = via_conductance(holes, ox, oy + WIN, c, (ny // n, nx // n), gaps)
        k0, k1 = int(round(12 / c)), int(round(18 / c))
        for meth in METHODS:
            fl = [faces(meth, S[l], n, *ph[l]) for l in range(L)]
            Tc = cd.solve_stack(np.stack([f[0] for f in fl]), np.stack([f[1] for f in fl]), gzc, c, np.arange(k0, k1), np.arange(k0, k1))[0][k0:k1, k0:k1]
            out.append((name, c, meth, 100 * (Tc.mean() / rm - 1), 100 * (Tc.max() / rx - 1)))
    return out


def main():
    """!
    @brief Pick the windows, run both stack-ups, print the errors.
    @return None.
    """
    t0 = time.time()
    f = readers.board_files("alleg")
    holes = [(x, y, d) for x, y, d, p in ng.read_drill(f["drill"]) if p]
    hx, hy = np.array([h[0] for h in holes]), np.array([h[1] for h in holes])
    x0, x1, y0, y1 = hx.min(), hx.max(), hy.min() - 0.5, hy.max() + 0.5
    rng = np.random.default_rng(11)
    tasks, wins = [], []
    keys = ("F", "L2", "L3", "B")
    while len(wins) < 6:
        ox, oy = rng.uniform(x0, max(x1 - WIN, x0 + 1)), rng.uniform(y0, max(y1 - WIN, y0 + 1))
        masks = np.stack([ng.render(f[k], ox, oy + WIN, WIN, WIN, PIX) for k in keys])
        hb = masks[0][120:180, 120:180].mean()
        if 0.1 <= hb <= 0.9:
            wh = [h for h in holes if ox <= h[0] < ox + WIN and oy <= h[1] < oy + WIN]
            wins.append((ox, oy, wh, masks))
    print(f"{len(wins)} windows; plated holes per window: {[len(w[2]) for w in wins]}; copper under the heater (top layer): {[round(float(w[3][0][120:180, 120:180].mean()), 2) for w in wins]}", flush=True)
    for name, copper in STACKS.items():
        for ox, oy, wh, masks in wins:
            tasks.append((name, copper, (ox, oy), wh, masks))
    out = []
    with Pool(2) as pool:                                      # a 4-layer reference needs several GB: two at a time
        for r in pool.imap_unordered(work, tasks):
            out += r
    print(f"{len(tasks)} runs, {time.time() - t0:.0f} s\n")
    print("MAE of the mean-temperature error % (bias in brackets) / MAE of the maximum-temperature error %")
    print(f"{'stack':27s}{'cell':>5s}" + "".join(f"{m:>22}" for m in METHODS))
    for name in STACKS:
        for c in CELLS:
            row = []
            for m in METHODS:
                e = np.array([(o[3], o[4]) for o in out if o[0] == name and o[1] == c and o[2] == m])
                row.append(f"{np.abs(e[:, 0]).mean():5.1f} ({e[:, 0].mean():+5.1f}) /{np.abs(e[:, 1]).mean():4.1f}")
            print(f"{name:27s}{c:5.1f}" + "".join(f"{x:>22}" for x in row))


if __name__ == "__main__":
    main()
