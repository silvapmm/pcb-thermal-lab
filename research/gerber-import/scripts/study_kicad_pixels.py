#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_kicad_pixels.py
@brief The nets against the KiCad project, pixel by pixel: the copper of the Stormduino drawn from its own `.kicad_pcb` (tracks, vias, pads, zone fills, each with its net) against the copper the independent reader draws from the Gerber files.
@details The check of README 4.33 asks whether the objects of the CAD file lie on the copper of the Gerbers and whether the pieces hold one net each. This study makes the comparison visible and counts it on every pixel: the objects of the `.kicad_pcb` are rasterised on the same grid as the Gerber mask (a track is a segment with round ends, a via a disc, a pad a circle, a stadium, a rectangle or a rounded rectangle at the angle of the file, a zone its filled polygons), each pixel keeps the net of the object that covers it, and the two masks are compared. Pixels of the Gerber without any CAD object, pixels of CAD objects without Gerber copper, and the nets of the pixels are reported per layer and per net; differences within one pixel of an edge are counted apart (a pixel centre on an edge goes either way).
         Needs data/storm (scripts/fetch_boards.py). Writes out/kicad_pixels.npz and out/kicad_pixels.json (read by make_figures.py). Run: .venv/bin/python research/gerber-import/scripts/study_kicad_pixels.py (from the repository root; about 1 minute).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import json
import math

import numpy as np
from matplotlib.path import Path as MPath
from scipy import ndimage

import importer as im
import kicad_pcb
from paths import DATA, OUT

PIX = 0.05                                    # mm, a pixel at most a quarter of the thinnest track
NAMES = ("F.Cu", "B.Cu")


class Grid:
    """!
    @brief The pixel grid of the imported board, with the pixel centres in the coordinates of the `.kicad_pcb` file (x as in the file, y down).
    """

    def __init__(self, ib):
        """!
        @brief Build the grid from an imported board.
        @param ib ImportedBoard.
        @return None.
        """
        self.rows, self.cols = ib.layers[0]["binary"].shape
        self.x = ib.box[0] + (np.arange(self.cols) + 0.5) * ib.pix           # file x
        self.y = -(ib.box[3] - (np.arange(self.rows) + 0.5) * ib.pix)         # file y (down): the Gerber y is the negative of it
        self.pix = ib.pix

    def window(self, x0, x1, y0, y1):
        """!
        @brief Index ranges of the pixels whose centres lie in a box (file coordinates).
        @param x0 Left.
        @param x1 Right.
        @param y0 Top (smaller file y).
        @param y1 Bottom.
        @return tuple (row slice, column slice) or None when the box is outside the grid.
        """
        c0, c1 = np.searchsorted(self.x, x0), np.searchsorted(self.x, x1)
        r0, r1 = np.searchsorted(self.y, y0), np.searchsorted(self.y, y1)       # y increases with the row index (file axis down)... see note below
        if c1 <= c0 or r1 <= r0:
            return None
        return slice(max(r0, 0), min(r1, self.rows)), slice(max(c0, 0), min(c1, self.cols))


def segment_mask(grid, a, b, w):
    """!
    @brief Pixels within w/2 of a segment (a track with round ends).
    @param grid Grid.
    @param a Start (x, y) in file coordinates.
    @param b End.
    @param w Width (mm).
    @return tuple (row slice, column slice, boolean array) of the pixels covered, or None.
    """
    pad = w / 2 + grid.pix
    win = grid.window(min(a[0], b[0]) - pad, max(a[0], b[0]) + pad, min(a[1], b[1]) - pad, max(a[1], b[1]) + pad)
    if win is None:
        return None
    X, Y = np.meshgrid(grid.x[win[1]], grid.y[win[0]])
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L2, 0, 1) if L2 > 0 else np.zeros_like(X)
    d = np.hypot(X - (a[0] + t * dx), Y - (a[1] + t * dy))
    return win[0], win[1], d <= w / 2


def pad_mask(grid, p):
    """!
    @brief Pixels covered by a pad: circle, oval (stadium), rectangle or rounded rectangle at the angle written in the file.
    @param grid Grid.
    @param p Pad dict of kicad_pcb.read.
    @return tuple (row slice, column slice, boolean array) or None.
    """
    w, h = p["size"]
    r = max(w, h) / 2 + grid.pix
    win = grid.window(p["p"][0] - r, p["p"][0] + r, p["p"][1] - r, p["p"][1] + r)
    if win is None:
        return None
    X, Y = np.meshgrid(grid.x[win[1]], grid.y[win[0]])
    th = math.radians(p["angle"])
    # coordinates in the pad's own axes (the file rotates counter-clockwise with y down, as the position of the pads in kicad_pcb.read)
    u = (X - p["p"][0]) * math.cos(th) - (Y - p["p"][1]) * math.sin(th)
    v = (X - p["p"][0]) * math.sin(th) + (Y - p["p"][1]) * math.cos(th)
    if p["shape"] == "circle":
        return win[0], win[1], np.hypot(u, v) <= w / 2
    if p["shape"] == "oval":
        # a stadium: a segment along the long side with round ends of the short side
        if w >= h:
            q = np.hypot(np.clip(np.abs(u) - (w - h) / 2, 0, None), v)
            return win[0], win[1], q <= h / 2
        q = np.hypot(u, np.clip(np.abs(v) - (h - w) / 2, 0, None))
        return win[0], win[1], q <= w / 2
    if p["shape"] == "roundrect":
        rad = min(w, h) * p.get("rratio", 0.25)
        q = np.hypot(np.clip(np.abs(u) - (w / 2 - rad), 0, None), np.clip(np.abs(v) - (h / 2 - rad), 0, None))
        return win[0], win[1], q <= rad
    return win[0], win[1], (np.abs(u) <= w / 2) & (np.abs(v) <= h / 2)


def polygon_mask(grid, pts):
    """!
    @brief Pixels inside a polygon (even-odd).
    @param grid Grid.
    @param pts Vertices (x, y) in file coordinates.
    @return tuple (row slice, column slice, boolean array) or None.
    """
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    win = grid.window(min(xs) - grid.pix, max(xs) + grid.pix, min(ys) - grid.pix, max(ys) + grid.pix)
    if win is None:
        return None
    X, Y = np.meshgrid(grid.x[win[1]], grid.y[win[0]])
    inside = MPath(pts).contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    return win[0], win[1], inside


def rasterise(grid, kc):
    """!
    @brief The copper of the `.kicad_pcb` on the grid: for each layer the net id of the object covering every pixel (0 = none), and the kind (1 zone fill, 2 track, 3 via, 4 pad; the last one drawn wins).
    @param grid Grid.
    @param kc Result of kicad_pcb.read.
    @return tuple (net image, kind image), each of shape (2, rows, cols).
    """
    net = np.zeros((2, grid.rows, grid.cols), np.int16)
    kind = np.zeros((2, grid.rows, grid.cols), np.int8)

    def put(li, res, n, k):
        """!
        @brief Write an object into the images.
        @param li Layer index.
        @param res Result of one of the mask functions or None.
        @param n Net id.
        @param k Kind code.
        @return None.
        """
        if res is None:
            return
        rs, cs, m = res
        net[li][rs, cs][m] = n
        kind[li][rs, cs][m] = k

    for z in kc["zones"]:
        if z["layer"] in NAMES:
            li = NAMES.index(z["layer"])
            for poly in z["filled"]:
                put(li, polygon_mask(grid, poly), z["net"], 1)
            # KiCad plots a filled zone with a stroke of the zone's minimum thickness along its outline, so the Gerber copper extends half of it beyond the polygon
            zone = (kind[li] == 1) & (net[li] == z["net"])
            grown = ndimage.distance_transform_edt(~zone) <= z["min_thickness"] / 2 / grid.pix
            new = grown & (net[li] == 0)
            net[li][new] = z["net"]
            kind[li][new] = 1
    for s in kc["segments"]:
        if s["layer"] in NAMES:
            put(NAMES.index(s["layer"]), segment_mask(grid, s["a"], s["b"], s["w"]), s["net"], 2)
    for v in kc["vias"]:
        for li in range(2):
            put(li, segment_mask(grid, v["p"], v["p"], v["size"]), v["net"], 3)
    for p in kc["pads"]:
        if p["kind"] == "np_thru_hole" and max(p["size"]) <= p["drill"] + 1e-9:
            continue                                  # a drilled hole without an annulus is not copper
        for li, n in enumerate(NAMES):
            if n in p["layers"] or "*.Cu" in p["layers"]:
                put(li, pad_mask(grid, p), p["net"], 4)
    return net, kind


def main():
    """!
    @brief Rasterise the CAD file, compare it with the Gerber copper and write the results.
    @return None.
    """
    ib = im.import_board(im.roles_of_downloaded("storm"), pix=PIX, cell=1.0)
    kc = kicad_pcb.read(DATA / "storm" / "stormduino.kicad_pcb")
    grid = Grid(ib)
    net, kind = rasterise(grid, kc)
    res = {"pixel_mm": PIX, "layers": {}, "nets": {}}
    store = {}
    for li, name in enumerate(NAMES):
        g = ib.layers[li]["binary"]
        k = kind[li] > 0                             # an object of the CAD file covers the pixel (a pad without a net has net 0 but is copper)
        near_g = ndimage.binary_dilation(g, iterations=1)
        near_k = ndimage.binary_dilation(k, iterations=1)
        only_g, only_k = g & ~k, k & ~g
        only_g_far, only_k_far = only_g & ~near_k, only_k & ~near_g
        res["layers"][name] = {"gerber_pixels": int(g.sum()), "cad_pixels": int(k.sum()), "both": int((g & k).sum()),
                               "only_gerber": int(only_g.sum()), "only_cad": int(only_k.sum()),
                               "only_gerber_beyond_one_pixel": int(only_g_far.sum()), "only_cad_beyond_one_pixel": int(only_k_far.sum()),
                               "only_gerber_by_kind": {}}
        store[f"gerber_{li}"] = np.packbits(g)
        store[f"cad_{li}"] = np.packbits(k)
        store[f"net_{li}"] = net[li]
        store[f"kind_{li}"] = kind[li]
        store[f"onlyg_far_{li}"] = np.packbits(only_g_far)
        store[f"onlyk_far_{li}"] = np.packbits(only_k_far)
        print(f"{name}: Gerber {int(g.sum()):,} px, CAD {int(k.sum()):,} px, both {int((g & k).sum()):,}; only Gerber {int(only_g.sum()):,} ({int(only_g_far.sum()):,} beyond 1 px), only CAD {int(only_k.sum()):,} ({int(only_k_far.sum()):,} beyond 1 px)")
    for n, nm in kc["nets"].items():
        if n == 0:
            continue                                  # net 0 is "no net": not an object of the CAD file
        px, inside = 0, 0
        for li in range(2):
            m = net[li] == n
            px += int(m.sum())
            inside += int((m & ib.layers[li]["binary"]).sum())
        if px:
            res["nets"][nm] = {"cad_pixels": px, "on_gerber_copper": inside}
    worst = sorted(((v["on_gerber_copper"] / v["cad_pixels"], k, v["cad_pixels"]) for k, v in res["nets"].items()))[:5]
    print("nets with the lowest share of their CAD pixels on Gerber copper:", [(k, round(r, 4), px) for r, k, px in worst])
    store["shape"] = np.array([grid.rows, grid.cols])
    store["box"] = np.array(ib.box)
    np.savez_compressed(OUT / "kicad_pixels.npz", **store)
    (OUT / "kicad_pixels.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
