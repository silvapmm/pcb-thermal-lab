#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_raster_error.py
@brief What does rasterising a Gerber copper layer lose against its exact vector geometry?
@details Three questions (board "storm", an Arduino Uno clone):
         1. Area: raster (binary and anti-aliased, several pixel sizes) against the exact vector area, per layer and per 1 mm cell.
         2. Thin traces: a binary raster (one sample per pixel centre) of synthetic traces from 0.05 to 0.5 mm wide, at random sub-pixel offsets and
            at two angles: area kept and the share of traces that come out interrupted.
         3. Reference convergence: the temperature of a 5 x 5 mm heater on the resolved copper (single layer) for pixels of 0.2, 0.1 and 0.05 mm.
         Run: .venv/bin/python research/gerber-models/scripts/study_raster_error.py (from the repository root)   (about 3 minutes; needs the board, see fetch_boards.py)
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import math

import numpy as np
import shapely
from shapely.geometry import LineString, box

import conduction as cd
import gerber_geometry as gg


def exact_cell_fill(geom, x0, y1, width, height, cell):
    """!
    @brief Exact copper area fraction of every cell (shapely intersection).
    @param geom shapely geometry (mm).
    @param x0 Left edge of the grid (mm).
    @param y1 Top edge of the grid (mm).
    @param width Grid width (mm).
    @param height Grid height (mm).
    @param cell Cell size (mm).
    @return Array (ny, nx) of fractions.
    """
    nx, ny = int(math.ceil(width / cell)), int(math.ceil(height / cell))
    shapely.prepare(geom)
    f = np.zeros((ny, nx))
    for i in range(ny):
        for j in range(nx):
            c = box(x0 + j * cell, y1 - (i + 1) * cell, x0 + (j + 1) * cell, y1 - i * cell)
            if shapely.intersects(geom, c):
                f[i, j] = geom.intersection(c).area / c.area
    return f


def cells_of(img, pix, cell):
    """!
    @brief Average a coverage image into cells.
    @param img Coverage image (rows, cols).
    @param pix Pixel size (mm).
    @param cell Cell size (mm), a multiple of pix.
    @return Array (cells_y, cells_x).
    """
    return cd.cell_blocks(img, int(round(cell / pix))).mean(axis=(2, 3))


def area_study(geoms, bbox):
    """!
    @brief Section 1: area error of the rasters.
    @param geoms Dict layer name -> exact geometry.
    @param bbox Board box (x0, y0, x1, y1) in mm.
    @return None (prints a table).
    """
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    print("=== 1. Area of a whole layer: raster against the exact vector area ===")
    print("layer | pixel mm | AA | area error | RMS error per 1 mm cell (fill fraction) | max error per 1 mm cell")
    for name, g in geoms.items():
        exact = exact_cell_fill(g, x0, y1, w, h, 1.0)
        for pix, aa in ((0.2, 1), (0.1, 1), (0.05, 1), (0.025, 1), (0.1, 4)):
            img = gg.sample_mask(g, x0, y1, round(w / 0.1) * 0.1, round(h / 0.1) * 0.1, pix, aa)
            f = cells_of(img, pix, 1.0)
            ny, nx = min(f.shape[0], exact.shape[0]), min(f.shape[1], exact.shape[1])
            e = f[:ny, :nx] - exact[:ny, :nx]
            tot = img.sum() * pix * pix
            print(f"  {name}   | {pix:5.3f}    | {aa}  | {100 * (tot / g.area - 1):+6.2f} %   | {np.sqrt((e ** 2).mean()):.4f}   | {np.abs(e).max():.3f}")


def thin_trace_study(seed=1, trials=200):
    """!
    @brief Section 2: what a binary raster does to a trace of width w.
    @param seed Seed of the random generator.
    @param trials Traces per width and pixel size.
    @return None (prints a table).
    """
    rng = np.random.default_rng(seed)
    pxs = (0.2, 0.1, 0.05, 0.025)
    print("\n=== 2. Thin traces: binary raster, area kept and share of interrupted traces ===")
    print("trace    | " + " | ".join(f"px {p:5.3f}".rjust(14) for p in pxs))
    for w in (0.05, 0.075, 0.1, 0.15, 0.2, 0.254, 0.3, 0.5):
        row = []
        for px in pxs:
            kept, broken = [], 0
            for _ in range(trials):
                ang = math.radians(rng.choice([0.0, 30.0]))
                y0, x0, L = rng.uniform(1, 3), rng.uniform(0, 1), 6.0
                g = LineString([(x0, y0), (x0 + L * math.cos(ang), y0 + L * math.sin(ang))]).buffer(w / 2, cap_style=2)
                gx, gy = np.arange(0, 9, px) + px / 2, np.arange(0, 6, px) + px / 2
                X, Y = np.meshgrid(gx, gy)
                shapely.prepare(g)
                m = shapely.contains_xy(g, X.ravel(), Y.ravel()).reshape(X.shape)
                kept.append(m.sum() * px * px / g.area)
                # Interrupted: some point of the centre line has no copper pixel within one pixel of it
                t = np.linspace(0.5, L - 0.5, int(L / (px / 2)))
                ii, jj = ((y0 + t * math.sin(ang)) / px).astype(int), ((x0 + t * math.cos(ang)) / px).astype(int)
                near = np.zeros(len(t), bool)
                for di in (-1, 0, 1):
                    for dj in (-1, 0, 1):
                        near |= m[np.clip(ii + di, 0, m.shape[0] - 1), np.clip(jj + dj, 0, m.shape[1] - 1)]
                broken += not near.all()
            row.append(f"{np.mean(kept) * 100:4.0f} %, {100 * broken / trials:3.0f} %")
        print(f"  {w:5.3f}  | " + " | ".join(r.rjust(14) for r in row))
    print("  (each cell: mean area kept, share of traces that came out interrupted)")


def reference_convergence(geom, hx=150.0, hy=-70.0):
    """!
    @brief Section 3: how the resolved reference changes with the pixel size (single layer, 1 W on 5 x 5 mm).
    @param geom Exact geometry of one layer (mm).
    @param hx X of the heater centre (mm).
    @param hy Y of the heater centre (mm).
    @return None (prints a table).
    """
    print("\n=== 3. Reference convergence: single layer, 5 x 5 mm heater ===")
    for pix in (0.2, 0.1, 0.05):
        half = 20.0                                                    # a 40 mm square window around the heater (inside the board)
        m = gg.sample_mask(geom, hx - half, hy + half, 2 * half, 2 * half, pix) > 0.5
        S = cd.sheet_of(m)
        gx, gy = cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :])
        c, r = int(half / pix), int(2.5 / pix)
        T = cd.solve_faces(gx, gy, pix, c - r, c + r, c - r, c + r)[c - r:c + r, c - r:c + r]
        print(f"  pixel {pix:5.3f} mm: patch mean {T.mean():6.2f} K, max {T.max():6.2f} K, copper {m.mean() * 100:4.1f} %")


def main():
    """!
    @brief Run the three studies on the Stormduino board.
    @return None.
    """
    files = gg.board_files("storm")
    geoms = {"F": gg.load_copper(files["F"])[0], "B": gg.load_copper(files["B"])[0]}
    bbox = gg.board_bbox(files["edge"], geoms["F"].bounds)
    for k, g in geoms.items():
        print(f"[{k}] exact area {g.area:.1f} mm2 ({g.area / ((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])) * 100:.1f} % of the box)")
    area_study(geoms, bbox)
    thin_trace_study()
    reference_convergence(geoms["F"])


if __name__ == "__main__":
    main()
