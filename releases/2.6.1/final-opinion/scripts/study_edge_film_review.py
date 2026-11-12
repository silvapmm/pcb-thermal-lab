#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_film_review.py
@brief Review of fix/imported-copper-edge-film-centroid: the centroid edge film of imported copper on an outline against the film on the node, on boards the investigation did not run.
@details Subcommands (run from the root of a checkout; PCBT_TREE names the tree whose `pcbthermal` is measured, default the checkout itself; the 3D truth and the board builder
         are those of `research/imported-copper-edge-film/lib`, found through PCBT_EDGE_FILM_LIB, default that folder of the checkout):
         * `wall <h_side> <cells>`: the 20 mm board of the investigation with the imported copper REACHING the outline (inset 0), ten turned and shifted boards, mean / spread /
           worst error against the 3D truth (computed here, about 5 minutes per edge coefficient), film on the node and centroid film.
         * `small <h_side> <cells>`: the same on a 12 mm square with a 2 mm heater (truth 87.83 K at 200 W/m2K, about 10 minutes for the truth).
         * `shapes`: T, L, four layers, stripes and a pad, mixed boards (some layers drawn): symmetry, positive off-diagonal entries, constant field, balance, hottest
           temperature with both films at 1 and 0.5 mm.
         * `real`: the oswlight and rp2040 boards of the local library (PCBT_GERBER_DATA, `pcb-library/scripts/link_env.sh`), two 3 mm heaters of 1 W, 1 / 0.5 / 0.25 mm.
         The film on the node is the program with `fvm.Network._cut_edge_film` replaced by the identity (the program before the change, for boards whose layers are all imported).
         Run: `.venv/bin/python releases/2.6.1/final-opinion/scripts/study_edge_film_review.py wall 200,1000 1,0.5`.
"""

import math
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.environ.get("PCBT_TREE", ROOT))
import numpy as np                                                              # noqa: E402

from pcbthermal import Problem, copper, fvm, gerber                             # noqa: E402
from pcbthermal.geometry import signed_distance_to_outline                      # noqa: E402

LIB = os.environ.get("PCBT_EDGE_FILM_LIB", os.path.join(ROOT, "research", "imported-copper-edge-film", "lib"))
REAL = fvm.Network._cut_edge_film
ANGLES = (0.0, 11.25, 22.5, 33.75, 45.0)
SHIFTS = (0.0, 0.3)


def use_film(film):
    """!
    @brief Select the edge film of the program for the next runs.
    @param film 'centroid' (the program of the branch) or 'node' (the identity: the film on the node).
    @return None.
    """
    fvm.Network._cut_edge_film = REAL if film == "centroid" else (lambda self, g: g)


def truth(h_side, half_mm, heat_mm, inset_mm=0.0):
    """!
    @brief Extrapolated 3D truth of the mean heater rise (the rule of the investigation's study_truth.py: three solves, cell 0.2 and 0.1 mm, 12 and 24 slabs).
    @param h_side Edge coefficient W/m2K.
    @param half_mm Half side of the square board in mm.
    @param heat_mm Side of the heater in mm.
    @param inset_mm Copper inset from the wall in mm.
    @return Truth in K.
    """
    sys.path.insert(0, LIB)
    import truth3d
    truth3d.HEAT = heat_mm * 1e-3
    a = truth3d.solve(h_side, 0.2, 12, half=half_mm * 1e-3, inset=inset_mm * 1e-3)[0]
    b = truth3d.solve(h_side, 0.1, 12, half=half_mm * 1e-3, inset=inset_mm * 1e-3)[0]
    c = truth3d.solve(h_side, 0.1, 24, half=half_mm * 1e-3, inset=inset_mm * 1e-3)[0]
    return c + 0.64 * (c - b) + 0.59 * (b - a)


def square(h, ang, centre, side, heat, inset=0.0, box=None, layers=2, pix=0.05):
    """!
    @brief A square board turned by `ang` in a larger box, full imported copper held `inset` inside the outline, a square heater of 1 W at the centre turned with it.
    @param h Edge coefficient W/m2K.
    @param ang Turn in degrees.
    @param centre (x, y) of the centre in mm.
    @param side Side of the square in mm.
    @param heat Side of the heater in mm.
    @param inset Copper inset in mm.
    @param box Side of the box in mm (default 1.5 side).
    @param layers Copper layers.
    @param pix Pixel of the masks in mm.
    @return Problem.
    """
    W = box or 1.5 * side
    a = math.radians(ang)

    def to_box(pts):
        """!
        @brief Board-frame points to box coordinates.
        @param pts List of (u, v) in mm.
        @return List of [x, y] in mm.
        """
        return [[centre[0] + u * math.cos(a) - v * math.sin(a), centre[1] + u * math.sin(a) + v * math.cos(a)] for u, v in pts]
    p = Problem.new(W, W, layers, h_side=h)
    p.board.h_top = p.board.h_bottom = 10.0
    s, a2 = heat / 2, side / 2
    p.add_heater(1, 1.0, polygon=to_box([(-s, -s), (s, -s), (s, s), (-s, s)]), name="U")
    p.set_outline(to_box([(-a2, -a2), (a2, -a2), (a2, a2), (-a2, a2)]))
    n, sub = int(round(W / pix)), 4
    t = (np.arange(n * sub) + 0.5) / sub * pix
    X, Y = np.meshgrid(t, W - t)
    u = (X - centre[0]) * math.cos(a) + (Y - centre[1]) * math.sin(a)
    v = -(X - centre[0]) * math.sin(a) + (Y - centre[1]) * math.cos(a)
    lim = a2 - inset
    m = (np.abs(u) <= lim) & (np.abs(v) <= lim)
    pk = np.round(255 * m.reshape(n, sub, n, sub).mean(axis=(1, 3))).astype(np.uint8)
    p.imported = copper.imported_from_rasters([pk] * layers, pix, "faces")
    return p


def heater_rise(p, cell):
    """!
    @brief Mean rise of the first heater (its own weights), K.
    @param p Problem.
    @param cell Cell in mm.
    @return float.
    """
    n = int(round(p.board.width * 1e3 / cell))
    net = fvm.Network(p, n, n)
    r = fvm.solve_steady(p, cell_mm=cell)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum())


def ten_boards(h, cell, tr, side, heat, film):
    """!
    @brief Error statistics of the ten turned and shifted boards against a truth.
    @param h Edge coefficient.
    @param cell Cell in mm.
    @param tr Truth in K.
    @param side Board side in mm.
    @param heat Heater side in mm.
    @param film 'node' or 'centroid'.
    @return Tuple (mean, spread, worst) in percent.
    """
    use_film(film)
    c0 = 0.75 * side
    e = np.array([100 * (heater_rise(square(h, ang, (c0 + sh * cell, c0 + sh * cell), side, heat), cell) / tr - 1) for sh in SHIFTS for ang in ANGLES])
    use_film("centroid")
    return float(e.mean()), float(np.ptp(e)), float(np.abs(e).max())


def wall(hs, cells, side, heat):
    """!
    @brief Print the copper-to-the-wall table.
    @param hs Edge coefficients.
    @param cells Cells in mm.
    @param side Board side in mm.
    @param heat Heater side in mm.
    @return None.
    """
    for h in hs:
        tr = 87.83 if (side == 12.0 and h == 200.0) else truth(h, side / 2, heat)
        print(f"side {side} mm, h_side {h:g}: truth {tr:.3f} K", flush=True)
        for c in cells:
            for film in ("node", "centroid"):
                print("  cell %g %-8s mean %+.2f spread %.2f worst %.2f %%" % ((c, film) + ten_boards(h, c, tr, side, heat, film)), flush=True)


OUTLINES = {"T": [[0, 20], [20, 20], [20, 14], [13, 14], [13, 0], [7, 0], [7, 14], [0, 14]], "L": [[0, 0], [20, 0], [20, 8], [8, 8], [8, 20], [0, 20]],
            "turned": [[0.6, 0.3], [19.7, 1.0], [19.4, 19.6], [0.5, 19.2]]}


def shape_board(name, layers=2, inset=0.0, drawn=(), stripes=False, h=200.0, n=400):
    """!
    @brief A 20 mm board of one outline with imported copper to the wall or `inset` inside, optionally stripes and a pad on the top layer, some layers drawn instead.
    @param name 'T', 'L' or 'turned'.
    @param layers Copper layers.
    @param inset Copper inset in mm.
    @param drawn Indices of the layers drawn as a zone (the outline) instead of imported.
    @param stripes Stripes 1 mm every 2 mm and a 7 mm pad on the top layer.
    @param h Edge coefficient.
    @param n Pixels per side.
    @return Problem.
    """
    p = Problem.new(20, 20, layers, h_side=h)
    p.board.h_top = p.board.h_bottom = 10.0
    p.set_outline(OUTLINES[name])
    cy = 17.0 if name == "T" else (4.0 if name == "L" else 10.0)
    p.add_heater(1, 1.0, rect=(9.0, cy - 1, 11.0, cy + 1), name="U")
    c = (np.arange(n) + 0.5) * p.board.width / n
    X, Y = np.meshgrid(c, c)
    d = signed_distance_to_outline(p.board.outline, X.ravel(), Y.ravel()).reshape(n, n)
    masks = []
    for k in range(layers):
        m = d >= inset * 1e-3
        if stripes and k == 0:
            m &= (np.floor(Y / 1e-3) % 2 == 0) | ((np.abs(X - 10e-3) < 3.5e-3) & (np.abs(Y - 10e-3) < 3.5e-3))
        masks.append(np.where(m, 255, 0).astype(np.uint8)[::-1])
    p.imported = copper.imported_from_rasters(masks, 20.0 / n, "faces")
    p.imported.layers = [e for e in p.imported.layers if e["index"] not in drawn]
    for k in drawn:
        p.add_zone(k + 1, polygon=OUTLINES[name])
    return p


def shapes():
    """!
    @brief Print the matrix properties and the move of the hottest temperature on the T, L, four-layer, striped and mixed boards.
    @return None.
    """
    cases = [dict(name="T"), dict(name="L"), dict(name="T", inset=1.0), dict(name="L", inset=1.0), dict(name="turned", layers=4), dict(name="turned", layers=4, inset=1.0),
             dict(name="turned", stripes=True, inset=1.0), dict(name="turned", drawn=(1,)), dict(name="turned", layers=4, drawn=(1, 2), inset=1.0)]
    for case in cases:
        p = shape_board(**case)
        for cell in (1.0, 0.5):
            n = int(round(20 / cell))
            net = fvm.Network(p, n, n)
            K = net.K.tocsr()
            off = K.copy()
            off.setdiag(0)
            off.eliminate_zeros()
            const = np.abs(np.asarray(K.sum(axis=1)).ravel() - net.g_amb.ravel()).max() / net.g_amb.max()
            r = fvm.solve_steady(p, cell_mm=cell)
            use_film("node")
            tn = fvm.solve_steady(p, cell_mm=cell).t_max
            use_film("centroid")
            print(case, cell, "sym %.1e offmax %.1e const %.1e balance %.1e hottest centroid %.3f node %.3f (%+.2f %% of the rise)"
                  % (abs(K - K.T).max() / abs(K).max(), off.max(), const, r.balance_error, r.t_max, tn, 100 * (r.t_max - tn) / (tn - r.ambient)), flush=True)


def real():
    """!
    @brief Print the move of the hottest temperature on two real imported outline boards of the local library (two 3 mm heaters of 1 W, the centre and 3 mm inside the edge).
    @return None.
    """
    base = os.environ.get("PCBT_GERBER_DATA", os.path.join(ROOT, "pcb-library", "env", "data"))
    from pcbthermal.gerber.outline import outline_from_layer
    for key, names in (("oswlight", ["F", "L2", "L3", "B"]), ("rp2040", ["F", "B"])):
        folder = os.path.join(base, key)
        if not os.path.isdir(folder):
            print(key, "absent: skipped")
            continue
        lays = [gerber.read_layer(os.path.join(folder, nm + ".gbr")) for nm in names]
        ib = copper.import_copper(lays, outline_from_layer(gerber.read_layer(os.path.join(folder, "edge.gbr"))), [gerber.read_drill_file(os.path.join(folder, "drill.drl"))],
                                  pixel_mm=0.05, cell_mm=0.5)
        for h in (10.0, 200.0):
            p = ib.to_problem(thickness_mm=1.6, h_side=h)
            o = np.asarray(p.board.outline) * 1e3
            c = o.mean(axis=0)
            edge = c
            for t in np.linspace(0, 1, 400):
                q = c + t * (o[0] - c)
                if signed_distance_to_outline(p.board.outline, np.array([q[0] * 1e-3]), np.array([q[1] * 1e-3]))[0] >= 3.0e-3:
                    edge = q
            for (x, y), nm in ((c, "centre"), (edge, "edge")):
                p.add_heater(1, 1.0, rect=(x - 1.5, y - 1.5, x + 1.5, y + 1.5), name=nm)
            for cell in (1.0, 0.5, 0.25):
                out = {}
                for film in ("centroid", "node"):
                    use_film(film)
                    t0 = time.time()
                    r = fvm.solve_steady(p, cell_mm=cell)
                    out[film] = (r.t_max, r.balance_error, time.time() - t0)
                use_film("centroid")
                tc, tn = out["centroid"][0], out["node"][0]
                print(key, "h_side", h, "cell", cell, "centroid %.3f node %.3f (%+.2f %% of the rise) balance %.0e, %.1f / %.1f s"
                      % (tc, tn, 100 * (tc - tn) / (tn - r.ambient), out["centroid"][1], out["centroid"][2], out["node"][2]), flush=True)


def main():
    """!
    @brief Dispatch the subcommand.
    @return None.
    """
    cmd = sys.argv[1]
    if cmd in ("wall", "small"):
        hs = [float(x) for x in sys.argv[2].split(",")]
        cells = [float(x) for x in sys.argv[3].split(",")]
        wall(hs, cells, 20.0 if cmd == "wall" else 12.0, 4.0 if cmd == "wall" else 2.0)
    elif cmd == "shapes":
        shapes()
    elif cmd == "real":
        real()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
