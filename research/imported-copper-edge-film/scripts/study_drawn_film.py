#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_drawn_film.py
@brief Does the film from the centroid of the board part of a cell (series film, d >= 0, floor 0.25) also hold for the DRAWN layers of a board with an outline? The program before and after the change, against the independent 3D truth.
@details Cases (every board is turned by 0, 11.25, 22.5, 33.75 and 45 degrees and shifted against the grid by 0 and 0.3 of a cell: ten boards, one physics, so one truth):
         * `sq_in`: the 20 mm square, copper 1.2 mm inside the outline, 2 layers, 4 mm heater; truth from `lib/truth_values.json` (extrapolated 3D, `truth3d.py`), h_side 10 to 1000.
         * `sq_wall`: the same with the copper REACHING the outline (the case the reviewer left untested for drawn layers).
         * `sq12`: a 12 mm square with a 2 mm heater, copper to the wall (truth 87.83 K at 200 W/m2K, the final opinion's `small`).
         * `sq_4l`: four layers; `sq_pad`: a 7.2 mm pad on the top layer and planes below; `sq_stripes`: stripes 1.2 mm every 2.4 mm plus a pad on the top layer.
         * `T` and `L`: axis-aligned T and L outlines (copper to the wall or 1.2 mm inside), turned and shifted as the squares, 2.4 mm heater.
         * `mixed`: the 20 mm square with the top layer imported and the others drawn, laminate nodes between a drawn and an imported layer.
         Truths of the new cases come from `lib/truth_mask.py` (full board, any outline, cells 0.4, 0.2 mm and the series of `study_truth.py`), stored in `lib/truth_values_drawn.json`.
         The program measured is the tree named by PCBT_TREE (default this checkout), so the run before the change is made on a checkout of `develop`.
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_drawn_film.py truths` (computes the truths, about 20 s each),
         `PCBT_TREE=<tree> .venv/bin/python .../study_drawn_film.py run <out.json> [case,...]`, `.venv/bin/python .../study_drawn_film.py report <before.json> <after.json>`.
"""

import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
LIB = os.path.join(HERE, "..", "lib")
sys.path.insert(0, os.environ.get("PCBT_TREE", ROOT))
sys.path.insert(1, LIB)
import numpy as np                                                              # noqa: E402
from matplotlib.path import Path                                                # noqa: E402

from pcbthermal import Problem, copper, fvm                                     # noqa: E402

ANGLES = (0.0, 11.25, 22.5, 33.75, 45.0)
SHIFTS = (0.0, 0.3)
TRUTH_FILE = os.path.join(LIB, "truth_values_drawn.json")


def rect(x0, y0, x1, y1):
    """!
    @brief A rectangle as a polygon.
    @param x0 Left, mm.
    @param y0 Bottom, mm.
    @param x1 Right, mm.
    @param y1 Top, mm.
    @return List of [x, y].
    """
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


SQ20 = rect(0, 0, 20, 20)
SQ12 = rect(0, 0, 12, 12)
T_OUT = [[0, 20], [20, 20], [20, 14], [13.2, 14], [13.2, 0], [6.8, 0], [6.8, 14], [0, 14]]
L_OUT = [[0, 0], [20, 0], [20, 8], [8, 8], [8, 20], [0, 20]]
T_IN = [[1.2, 18.8], [18.8, 18.8], [18.8, 15.2], [12.0, 15.2], [12.0, 1.2], [8.0, 1.2], [8.0, 15.2], [1.2, 15.2]]
L_IN = [[1.2, 1.2], [18.8, 1.2], [18.8, 6.8], [6.8, 6.8], [6.8, 18.8], [1.2, 18.8]]
HEAT20 = (8.0, 8.0, 12.0, 12.0)
HEAT24_T = (8.8, 16.0, 11.2, 18.4)
HEAT24_L = (8.8, 2.8, 11.2, 5.2)


def stripes(lim0, lim1, width=1.2, pitch=2.4):
    """!
    @brief Stripes along x between lim0 and lim1 in y (a list of rectangles) plus a 7.2 mm pad at the centre of the 20 mm board.
    @param lim0 First stripe start, mm.
    @param lim1 Last allowed y, mm.
    @param width Stripe width, mm.
    @param pitch Stripe pitch, mm.
    @return List of polygons.
    """
    out, y = [], lim0
    while y < lim1 - 1e-9:
        out.append(rect(lim0, y, lim1, min(y + width, lim1)))
        y += pitch
    out.append(rect(6.4, 6.4, 13.6, 13.6))
    return out


CASES = {
    "sq_in": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), heater=HEAT20, layers=2, hs=(10.0, 50.0, 200.0, 500.0, 1000.0), cells=(1.0, 0.5)),
    "sq_wall": dict(outline=SQ20, cu=lambda: None, heater=HEAT20, layers=2, hs=(200.0, 1000.0), cells=(1.0, 0.5)),
    "sq12": dict(outline=SQ12, cu=lambda: None, heater=(5.0, 5.0, 7.0, 7.0), layers=2, hs=(200.0,), cells=(1.0, 0.5, 0.25)),
    "sq_4l": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), heater=HEAT20, layers=4, hs=(200.0, 1000.0), cells=(1.0, 0.5)),
    "sq_pad": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), top=lambda: rect(6.4, 6.4, 13.6, 13.6), heater=HEAT20, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "sq_stripes": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), top=lambda: stripes(1.2, 18.8), heater=HEAT20, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "T_wall": dict(outline=T_OUT, cu=lambda: None, heater=HEAT24_T, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "T_in": dict(outline=T_OUT, cu=lambda: T_IN, heater=HEAT24_T, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "L_wall": dict(outline=L_OUT, cu=lambda: None, heater=HEAT24_L, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "L_in": dict(outline=L_OUT, cu=lambda: L_IN, heater=HEAT24_L, layers=2, hs=(200.0,), cells=(1.0, 0.5)),
    "mixed_2l": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), heater=HEAT20, layers=2, hs=(200.0,), cells=(1.0, 0.5), imported=(0,), truth_like="sq_in"),
    "imp_2l": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), heater=HEAT20, layers=2, hs=(200.0,), cells=(1.0, 0.5), imported=(0, 1), truth_like="sq_in"),
    "mixed_4l": dict(outline=SQ20, cu=lambda: rect(1.2, 1.2, 18.8, 18.8), heater=HEAT20, layers=4, hs=(200.0,), cells=(1.0, 0.5), imported=(0, 3), truth_like="sq_4l"),
}


def layers_cu(spec):
    """!
    @brief Copper polygon (or None) of every layer of a case, board frame.
    @param spec Case dict.
    @return List.
    """
    out = []
    for k in range(spec["layers"]):
        out.append(spec["top"]() if (k == 0 and "top" in spec) else spec["cu"]())
    return out


def truths():
    """!
    @brief Compute and store the 3D truths of the cases that have no stored truth.
    @return None.
    """
    import truth_mask
    data = json.load(open(TRUTH_FILE)) if os.path.exists(TRUTH_FILE) else {}
    for name, spec in CASES.items():
        if name in ("sq_in", "sq12") or "truth_like" in spec:
            continue
        for h in spec["hs"]:
            key = f"{name}|{h}"
            if key in data:
                continue
            cu = layers_cu(spec)
            nz = 12 if spec["layers"] == 2 else 8
            t0 = time.time()
            r = truth_mask.truth(spec["outline"], cu, spec["heater"], h, nz=nz)
            data[key] = r
            print(key, round(r["truth"], 4), [round(v, 4) for v in r["solves"]], "balance %.0e" % r["balance"], round(time.time() - t0), "s", flush=True)
            json.dump(data, open(TRUTH_FILE, "w"), indent=1)


def truth_of(name, h):
    """!
    @brief The stored truth of a case.
    @param name Case name.
    @param h Edge coefficient.
    @return Truth in K.
    """
    spec = CASES[name]
    name = spec.get("truth_like", name)
    if name == "sq_in":
        return json.load(open(os.path.join(LIB, "truth_values.json")))[f"2|1.2|{h}"]["truth"]
    if name == "sq12":
        return 87.83
    return json.load(open(TRUTH_FILE))[f"{name}|{h}"]["truth"]


def build(spec, h, ang, shift_mm, imported=()):
    """!
    @brief The Problem of one board: turned by ang about the centre of its bounding box, shifted, in a box large enough for the turn; layers in `imported` as masks, the others as zones.
    @param spec Case dict.
    @param h Edge coefficient W/m2K.
    @param ang Turn in degrees.
    @param shift_mm Shift of the board in x and y, mm.
    @param imported Indices (0 based) of the layers imported from a raster of their polygon.
    @return Problem.
    """
    out = np.asarray(spec["outline"], float)
    cx0, cy0 = out[:, 0].max() / 2, out[:, 1].max() / 2
    side = max(out[:, 0].max(), out[:, 1].max())
    W = 32.0 if side > 15 else 20.0
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    c0 = W / 2 + shift_mm

    def tobox(poly):
        """!
        @brief Board-frame polygon to box coordinates.
        @param poly Polygon in mm.
        @return List of [x, y].
        """
        return [[c0 + (x - cx0) * ca - (y - cy0) * sa, c0 + (x - cx0) * sa + (y - cy0) * ca] for x, y in poly]
    p = Problem.new(W, W, spec["layers"], h_side=h)
    p.board.h_top = p.board.h_bottom = 10.0
    p.add_heater(1, 1.0, polygon=tobox(rect(*spec["heater"])), name="U")
    p.set_outline(tobox(spec["outline"]))
    cus = layers_cu(spec)
    pix, sub = 0.05, 4
    n = int(round(W / pix))
    if imported:
        t = (np.arange(n * sub) + 0.5) / sub * pix
        X, Y = np.meshgrid(t, W - t)
        pts = np.column_stack([X.ravel(), Y.ravel()])
    masks = []
    for k, cu in enumerate(cus):
        poly = spec["outline"] if cu is None else cu
        polys = cu if (cu is not None and np.ndim(cu[0][0]) == 1) else [poly]       # a list of polygons (stripes) or one
        if k in imported:
            m = np.zeros(len(pts), bool)
            for q in polys:
                m |= Path(np.array(tobox(q))).contains_points(pts)
            masks.append(np.round(255 * m.reshape(n, sub, n, sub).mean(axis=(1, 3))).astype(np.uint8))
        else:
            masks.append(np.zeros((n, n), np.uint8))
            for q in polys:
                p.add_zone(k + 1, polygon=tobox(q))
    if imported:
        p.imported = copper.imported_from_rasters(masks, pix, "faces")
        p.imported.layers = [e for e in p.imported.layers if e["index"] in imported]
    return p


def heater_rise(p, cell):
    """!
    @brief Mean rise of the heater (its own weights), the hottest rise and the balance error.
    @param p Problem.
    @param cell Cell in mm.
    @return Tuple (mean K, hottest K, balance).
    """
    n = int(round(p.board.width * 1e3 / cell))
    net = fvm.Network(p, n, n)
    r = fvm.solve_steady(p, cell_mm=cell)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum()), float(r.t_max - r.ambient), float(r.balance_error)


def run(out, names):
    """!
    @brief Run the cases on the tree and store the heater means of the ten boards.
    @param out Output JSON path.
    @param names Case names.
    @return None.
    """
    res = json.load(open(out)) if os.path.exists(out) else {}
    for name in names:
        spec = CASES[name]
        for h in spec["hs"]:
            for cell in spec["cells"]:
                key = f"{name}|{h}|{cell}"
                if key in res:
                    continue
                vals, bal = [], 0.0
                t0 = time.time()
                for sh in SHIFTS:
                    for ang in ANGLES:
                        m, tm, be = heater_rise(build(spec, h, ang, sh * cell, spec.get("imported", ())), cell)
                        vals.append(m)
                        bal = max(bal, abs(be))
                res[key] = {"vals": vals, "balance": bal}
                tr = truth_of(name, h)
                e = 100 * (np.array(vals) / tr - 1)
                print(f"{key:28s} mean {e.mean():+6.2f} spread {np.ptp(e):5.2f} worst {np.abs(e).max():5.2f} balance {bal:.0e} ({time.time() - t0:.0f} s)", flush=True)
                json.dump(res, open(out, "w"))


def report(fa, fb):
    """!
    @brief Print before and after the change: mean, spread and worst error against the truth of every case, and the boards that got worse.
    @param fa JSON of the run before.
    @param fb JSON of the run after.
    @return None.
    """
    a, b = json.load(open(fa)), json.load(open(fb))
    print("%-26s | %-26s | %-26s | worse boards" % ("case|h|cell", "before mean/spread/worst %", "after mean/spread/worst %"))
    for key in a:
        if key not in b or key.split("|")[0] not in CASES:
            continue
        name, h, cell = key.split("|")
        tr = truth_of(name, float(h))
        ea = 100 * (np.array(a[key]["vals"]) / tr - 1)
        eb = 100 * (np.array(b[key]["vals"]) / tr - 1)
        worse = int(np.sum(np.abs(eb) > np.abs(ea) + 0.5))
        print("%-26s | %+6.2f %5.2f %5.2f        | %+6.2f %5.2f %5.2f        | %d  (balance %.0e)" % (key, ea.mean(), np.ptp(ea), np.abs(ea).max(), eb.mean(), np.ptp(eb), np.abs(eb).max(), worse, b[key]["balance"]))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "truths":
        truths()
    elif cmd == "run":
        run(sys.argv[2], sys.argv[3].split(",") if len(sys.argv) > 3 else list(CASES))
    elif cmd == "report":
        report(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
