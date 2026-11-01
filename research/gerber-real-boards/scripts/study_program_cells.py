#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_program_cells.py
@brief The imported-copper mappings AS IMPLEMENTED IN THE PROGRAM (`pcbthermal/copper.py`, branch feature/imported-copper) at the program's cells (0.5, 1 and 2 mm), on real windows of the downloaded boards: the error of the mapping alone (against the program's own network on the pixel) and against the independent 3D solver.
@details Answers the item owed by README 10 / INTEGRATION 9 (step 1): "the same split at the program's cells on at least one larger window, and a test that the naive order fails".
         Part `mapping`: windows of 12 mm (pixel 0.1 mm) and 24 mm (pixel 0.125 mm), heater 4 mm at the centre of the top layer (edges on the lines of the 0.5, 1 and 2 mm cells), h = 10 W/m2K on both faces,
         adiabatic sides, simple stack-up 1.6 mm, copper 35 micrometres. Variants: faces (default), lambda 0.5, fill (the old path), naive (faces from the unreduced sheet, `CopperSource.reduce_sheet = False`).
         Reference: the program's network on the pixel grid (fill 0 or 1 per pixel, laminate rule on); the difference is the error of the mapping alone. Binary pixel-centre masks, as the earlier studies.
         Part `ref3d`: 12 mm windows, heater 4.8 mm, cells 0.6 and 1.2 mm, against `lib/ref3d.py` (independent 3D finite volumes, nothing of pcbthermal imported), the setting of README 10.
         Windows: for each board the top copper is drawn at 0.4 mm and the 12 (24) mm window whose central block is nearest to 55 % copper is taken (deterministic).
         Run (repository root): .venv/bin/python research/gerber-real-boards/scripts/study_program_cells.py --part mapping|ref3d [--boards a,b] [--side 12|24]
         Memory: one reference at a time; 12 mm: about 1 GB, 24 mm pixel network about 2 GB, ref3d about 2 to 3 GB.
         NOT verified: any measurement on a physical board; heaters other than a square on the top layer; copper thickness other than 35 micrometres; plated holes (left out of both sides).
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import argparse
import time

import numpy as np

from pcbthermal import copper, fvm, gerber
from pcbthermal.model import Problem

import ref3d
import registry

THICK, H_FACE, T_CU = 1.6, 10.0, 35e-6


def window(key, side, heater, pix):
    """!
    @brief The deterministic real window of a board (central block nearest to 55 % copper) rasterised as a binary pixel-centre mask.
    @param key Board key of registry.BOARDS.
    @param side Window side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @return List of uint8 rasters (rows from the top), top layer first, or None.
    """
    layers = [gerber.read_layer(f) for f in registry.roles(key)["copper"]]
    x0, y0, x1, y1 = layers[0].bbox()
    coarse = gerber.rasterize(layers[0], gerber.Window(x0, y1, x1 - x0, y1 - y0), 0.4, 1) > 127
    w, h, step = int(round(side / 0.4)), int(round(heater / 0.4)), int(round(4.0 / 0.4))
    best = None
    for i in range(0, coarse.shape[0] - w, step):
        for j in range(0, coarse.shape[1] - w, step):
            win = coarse[i:i + w, j:j + w]
            core = win[(w - h) // 2:(w - h) // 2 + h, (w - h) // 2:(w - h) // 2 + h]
            if 0.25 < win.mean() < 0.85 and 0.3 < core.mean() < 0.8:
                if best is None or abs(core.mean() - 0.55) < best[0]:
                    best = (abs(core.mean() - 0.55), i, j)
    if best is None:
        return None
    _, i, j = best
    win = gerber.Window(x0 + j * 0.4, y1 - i * 0.4, side, side)
    return [gerber.rasterize(l, win, pix, 1) for l in layers]


def board(rasters, mapping, side, heater, pix):
    """!
    @brief A square imported board with one heater at the centre of the top layer.
    @param rasters Rasters, top first.
    @param mapping Copper mapping.
    @param side Side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @return Problem.
    """
    p = Problem.new(side, side, layers=len(rasters), thickness_mm=THICK, copper_um=35, h_top=H_FACE, h_bottom=H_FACE, h_side=None)
    c = side / 2
    p.add_heater(1, 1.0, rect=(c - heater / 2, c - heater / 2, c + heater / 2, c + heater / 2))
    p.imported = copper.imported_from_rasters(rasters, pix, mapping)
    return p


def heater_mean(theta, cell, side, heater):
    """!
    @brief Mean rise of the top layer over the cells whose centres lie in the heater block.
    @param theta Array (layers, ny, nx).
    @param cell Cell in mm.
    @param side Side in mm.
    @param heater Heater side in mm.
    @return float K.
    """
    c = side / 2
    x = (np.arange(theta.shape[2]) + 0.5) * cell
    y = (np.arange(theta.shape[1]) + 0.5) * cell
    m = (x[None, :] > c - heater / 2) & (x[None, :] < c + heater / 2) & (y[:, None] > c - heater / 2) & (y[:, None] < c + heater / 2)
    return float(theta[0][m].mean())


def run(p, cell, side, heater, faces=None):
    """!
    @brief The heater mean of the program's FVM.
    @param p Problem.
    @param cell Cell in mm.
    @param side Side in mm.
    @param heater Heater side in mm.
    @param faces Argument faces of the network.
    @return float K.
    """
    n = int(round(side / cell))
    return heater_mean(fvm.Network(p, n, n, faces=faces).solve_steady()[0], cell, side, heater)


def part_mapping(boards, side, pix, cells=(0.5, 1.0, 2.0), heater=4.0):
    """!
    @brief Part mapping: the error of the mapping alone at the program's cells.
    @param boards Board keys.
    @param side Window side in mm.
    @param pix Pixel in mm.
    @param cells Cells in mm.
    @param heater Heater side in mm.
    @return list of rows (board, layers, cell, error of faces, lambda, fill, naive in percent).
    """
    rows = []
    for key in boards:
        ras = window(key, side, heater, pix)
        if ras is None:
            print(f"{key}: no window")
            continue
        t = time.time()
        ref = run(board(ras, "fill", side, heater, pix), pix, side, heater)
        for cell in cells:
            pct = lambda v: 100.0 * (v / ref - 1.0)                  # noqa: E731
            f = pct(run(board(ras, "faces", side, heater, pix), cell, side, heater))
            l = pct(run(board(ras, "lambda", side, heater, pix), cell, side, heater))
            d = pct(run(board(ras, "fill", side, heater, pix), cell, side, heater))
            p = board(ras, "faces", side, heater, pix)
            src = copper.CopperSource.of(p)
            src.reduce_sheet = False
            nv = pct(run(p, cell, side, heater, faces=src))
            rows.append((key, len(ras), cell, f, l, d, nv))
            print(f"{key:9s} L{len(ras)} {side:g} mm cell {cell}: faces {f:+.2f}  lambda {l:+.2f}  fill {d:+.2f}  naive {nv:+.2f}", flush=True)
        print(f"  ({time.time() - t:.0f} s)", flush=True)
    return rows


def summary(rows, reference="the program's network on the pixel"):
    """!
    @brief Print the mean absolute error and the wins per layer count and cell.
    @param rows Rows of part_mapping or part_ref3d.
    @param reference Text naming the reference.
    @return None.
    """
    print(f"\nmean |error| / largest |error| in percent of the heater rise, against {reference}")
    for layers in sorted({r[1] for r in rows}):
        for cell in sorted({r[2] for r in rows}):
            sel = [r for r in rows if r[1] == layers and r[2] == cell]
            if not sel:
                continue
            cols = []
            for k, name in ((3, "faces"), (4, "lambda"), (5, "fill"), (6, "naive")):
                a = np.abs([r[k] for r in sel])
                cols.append(f"{name} {a.mean():.2f} / {a.max():.2f}")
            wins = sum(abs(r[3]) < abs(r[5]) for r in sel)
            print(f"  {layers} layers, cell {cell}: n = {len(sel)}  " + "  ".join(cols) + f"  faces closer than fill in {wins}")


def part_ref3d(boards, side=12.0, heater=4.8, pix=0.1, cells=(0.6, 1.2)):
    """!
    @brief Part ref3d: the mappings against the independent 3D solver.
    @param boards Board keys.
    @param side Window side in mm.
    @param heater Heater side in mm.
    @param pix Pixel in mm.
    @param cells Cells in mm.
    @return list of rows (board, layers, cell, faces, lambda, fill, naive errors in percent).
    """
    rows = []
    for key in boards:
        ras = window(key, side, heater, pix)
        if ras is None:
            continue
        L = len(ras)
        n_sub = 8 if L == 2 else 3
        gap = (THICK * 1e-3 - L * T_CU) / (L - 1)
        t = time.time()
        masks = [(r > 127)[::-1] for r in ras]
        m = ref3d.build(masks, pix * 1e-3, T_CU, [gap] * (L - 1), n_sub=n_sub, h_top=H_FACE, h_bottom=H_FACE)
        c = side / 2
        hm = np.zeros(masks[0].shape, bool)
        xs = (np.arange(hm.shape[1]) + 0.5) * pix
        hm[:] = (xs[None, :] > c - heater / 2) & (xs[None, :] < c + heater / 2) & (xs[:, None] > c - heater / 2) & (xs[:, None] < c + heater / 2)
        ref = float(ref3d.solve(m, hm, 1.0)["top"][hm].mean())
        for cell in cells:
            pct = lambda v: 100.0 * (v / ref - 1.0)                  # noqa: E731
            f = pct(run(board(ras, "faces", side, heater, pix), cell, side, heater))
            l = pct(run(board(ras, "lambda", side, heater, pix), cell, side, heater))
            d = pct(run(board(ras, "fill", side, heater, pix), cell, side, heater))
            p = board(ras, "faces", side, heater, pix)
            src = copper.CopperSource.of(p)
            src.reduce_sheet = False
            nv = pct(run(p, cell, side, heater, faces=src))
            rows.append((key, L, cell, f, l, d, nv))
            print(f"{key:9s} L{L} cell {cell}: 3D {ref:.1f} K; faces {f:+.2f}  lambda {l:+.2f}  fill {d:+.2f}  naive {nv:+.2f}  ({time.time() - t:.0f} s)", flush=True)
    return rows


def main():
    """!
    @brief Command line entry.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[2] if __doc__ else "")
    ap.add_argument("--part", choices=("mapping", "ref3d"), required=True)
    ap.add_argument("--boards", default="")
    ap.add_argument("--side", type=float, default=12.0)
    ap.add_argument("--pix", type=float, default=0.0, help="pixel in mm (default 0.1 for 12 mm windows, 0.125 for larger ones)")
    args = ap.parse_args()
    boards = [b for b in args.boards.split(",") if b] or [k for k in registry.available() if len(registry.roles(k)["copper"]) >= 2]
    if args.part == "mapping":
        pix = args.pix or (0.1 if args.side <= 12.0 else 0.125)
        summary(part_mapping(boards, args.side, pix))
    else:
        summary(part_ref3d(boards), "the independent 3D solver")


if __name__ == "__main__":
    main()
