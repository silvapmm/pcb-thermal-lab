#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The reviewer's independent checks of the cut-cell links study (README 10): do the sliver defect, the spreads over the outline position and the geometry claims hold against references that share nothing with the schemes?
@details Subcommands (each writes `out/review_<name>.json`):
         - `sliver`   the board of `study_small_cells.py` (edge column of cover c) at h_side 10, 200, 2000 against the independent two-sheet solver (`lib/indep_sheet.py`, the same board
                      as an aligned rectangle, second-order edge, 1/4, 1/8, 1/16 mm extrapolated): error of the FVM schemes, the FDM and the 3D solid at 1 mm; and the 3D solid and
                      the FVM against the same board drawn as a rectangle at 1 and 0.5 mm (no cut cell);
         - `frame`    the frame references of `study_scheme_sweep.py` recomputed with the independent solver for the square with the part 3.5 mm off (1 mm, h_side 200, 2000) and
                      the strip (0.5 mm, h_side 10, 200), on the 17 positions of the study plus 7 shifts along x and 10 random turns with shifts;
         - `tee`      the small T: error of the hottest node and of the mean over the part (`analysis.heater_stats`) against the program at 1/12 and 1/24 mm, to tell the read-out from
                      a link effect;
         - `geometry` the prototype's apertures against brute-force sampling on a turned L, the small T and a notch crossed twice; the vectorised apertures (`lib/vecaperture.py`)
                      against the prototype and their cost on a 20 000-vertex outline at 0.25 mm; the cells where the film factor reaches the floor with the copper held off the edge.
Usage: .venv/bin/python research/cut-cell-links/scripts/study_review.py [sliver|frame|tee|geometry|all]   (from the repository root; sliver 2 min, frame 6 min, tee 4 min, geometry 30 s; below 2 GB)
"""

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)
OUT = os.path.join(os.path.dirname(HERE), "out")

import cutlinks as cl          # noqa: E402
import boards as bd            # noqa: E402
import indep_sheet as ind      # noqa: E402
import vecaperture as va       # noqa: E402
import cutgeom                 # noqa: E402
from pcbthermal import Problem, fdm, solid3d, fvm, analysis   # noqa: E402

AMB = 25.0
FINE = (0.25e-3, 0.125e-3, 0.0625e-3)


def sliver_board(c, h_side):
    """!
    @brief The board of `study_small_cells.board`: left edge column [5, 6] mm covered by the fraction c.
    @param c Cover of the edge column.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    e = 6.0 - c
    p = Problem.new(30, 30, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0, 13.5, 11.0, 16.5), name="U")
    p.set_outline([[e, 5], [25, 5], [25, 25], [e, 25]])
    return p


def sliver_rect(c, h_side):
    """!
    @brief The same board drawn as an aligned rectangle (no outline, so no cut cell).
    @param c Cover of the edge column of `sliver_board`.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    e = 6.0 - c
    p = Problem.new(25 - e, 20, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(8.0 - e, 8.5, 11.0 - e, 11.5), name="U")
    return p


def study_sliver():
    """!
    @brief Sliver board against the independent solver and against the rectangle.
    @return dict of the numbers.
    """
    out = {}
    print("| h_side | c | reference (degC) | program | aperture | aperture+film | FDM | 3D solid |\n| --: | --: | --: | --: | --: | --: | --: | --: |")
    for hs in (10.0, 200.0, 2000.0):
        for c in (0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0):
            e = 6.0 - c
            W, H = (25 - e) * 1e-3, 20e-3
            src = ((8 - e) * 1e-3, 8.5e-3, (11 - e) * 1e-3, 11.5e-3)
            ref = ind.richardson(lambda h: ind.solve(W, H, h, hs, src)[0] + AMB, FINE)[0]
            row = {s: cl.tmax(sliver_board(c, hs), 1.0, s) - ref for s in ("program", "aperture", "aperture+film")}
            row["fdm"] = fdm.solve_steady(sliver_board(c, hs), cell_mm=1.0).t_max - ref
            row["solid3d"] = solid3d.solve_steady(sliver_board(c, hs), cell_mm=1.0).t_max - ref
            out[f"{hs:g}|{c:g}"] = dict(ref=ref, **row)
            print(f"| {hs:g} | {c:g} | {ref:.3f} | " + " | ".join(f"{row[k]:+.3f}" for k in ("program", "aperture", "aperture+film", "fdm", "solid3d")) + " |", flush=True)
    print("\n| h_side | c | cell | 3D outline - 3D rectangle | FVM outline - FVM rectangle |\n| --: | --: | --: | --: | --: |")
    for hs in (10.0, 200.0):
        for c in (0.01, 0.02, 0.1, 1.0):
            for cell in (1.0, 0.5):
                d3 = solid3d.solve_steady(sliver_board(c, hs), cell_mm=cell).t_max - solid3d.solve_steady(sliver_rect(c, hs), cell_mm=cell).t_max
                df = fvm.solve_steady(sliver_board(c, hs), cell_mm=cell).t_max - fvm.solve_steady(sliver_rect(c, hs), cell_mm=cell).t_max
                out[f"rect|{hs:g}|{c:g}|{cell:g}"] = dict(solid3d=d3, fvm=df)
                print(f"| {hs:g} | {c:g} | {cell:g} | {d3:+.3f} | {df:+.3f} |", flush=True)
    return out


def study_frame():
    """!
    @brief Frame references from the independent solver, more positions than the study.
    @return dict of the numbers.
    """
    cache = json.load(open(os.path.join(OUT, "refs.json"))) if os.path.exists(os.path.join(OUT, "refs.json")) else {}
    rng = np.random.default_rng(7)
    out = {}
    for (shape, off), hss, cell in ((("square", 3.5), (200.0, 2000.0), 1.0), (("strip", 0.0), (10.0, 200.0), 0.5)):
        pos = [(f"turn {a}", dict(angle=float(a))) for a in range(0, 50, 5)]
        pos += [(f"shift {k}/8", dict(sx=k / 8 * cell, sy=k / 8 * cell)) for k in range(1, 8)]
        pos += [(f"xshift {k}/8", dict(sx=k / 8 * cell)) for k in range(1, 8)]
        pos += [(f"mix{i}", dict(angle=float(rng.uniform(0, 45)), sx=float(rng.uniform(0, cell)), sy=float(rng.uniform(0, cell)))) for i in range(10)]
        for hs in hss:
            errs = {s: {} for s in ("program", "aperture", "aperture+film")}
            dref = []
            for label, pk in pos:
                kw = dict(h_side=hs, shape=shape, off=off, pc=cell / 2, box=32.0, **pk)
                fb = bd.frame_board(**kw)
                poly = np.array(fb.heaters[0].polygon)
                ref = ind.richardson(lambda h: ind.solve(fb.board.width, fb.board.height, h, hs, poly, poly=True)[0] + AMB, FINE)[0]
                key = f"{shape}|{off}|{hs}|{label}|{cell}"
                if key in cache:
                    dref.append(ref - cache[key])
                for s in errs:
                    errs[s][label] = cl.tmax(bd.edge_board(**kw), cell, s) - ref
            out[f"{shape}|{off}|{hs:g}|{cell:g}"] = dict(errs=errs, ref_minus_study=dref)
            print(f"{shape} off {off:g}, h_side {hs:g}, cell {cell:g}: independent minus study reference over {len(dref)} positions: mean {np.mean(dref):+.3f}, range {np.ptp(dref):.3f} K")
            for s, e in errs.items():
                a = np.array(list(e.values()))
                base = np.array([v for k, v in e.items() if not k.startswith(("mix", "xshift"))])
                print(f"  {s:14s} spread on the study's 17 positions {np.ptp(base):.3f} K, on all {len(a)} {np.ptp(a):.3f} K, bias {a.mean():+.3f} K", flush=True)
    return out


def study_tee():
    """!
    @brief Small T: hottest node and part mean against the fine program.
    @return dict of the numbers.
    """
    out = {}

    def m(p, c, s):
        r = cl.solve(p, c, s)
        return np.array([r.t_max, analysis.heater_stats(r, p)[0]["t_mean"]])

    for hs in (10.0, 200.0):
        rows = []
        for k in range(12):
            a = 10.0 + k / 12.0
            r1, r2 = m(bd.small_t(a, hs), 1 / 12, "program"), m(bd.small_t(a, hs), 1 / 24, "program")
            ref = r2 + (r2 - r1)                       # first order; the change from 1/12 to 1/24 is 0.02 K or less, so the order hardly matters
            rows.append([a] + [v for s in ("program", "aperture", "aperture+film") for v in m(bd.small_t(a, hs), 1.0, s) - ref])
        A = np.array(rows)
        out[f"{hs:g}"] = A.tolist()
        print(f"\nsmall T, h_side {hs:g}, cell 1 mm (K): a, then peak and part-mean errors of program, aperture, aperture+film")
        for r in rows:
            print(" ".join(f"{v:+.3f}" for v in r))
        for n, s in enumerate(("program", "aperture", "aperture+film")):
            print(f"  {s}: peak bias {A[:, 1 + 2 * n].mean():+.2f} spread {np.ptp(A[:, 1 + 2 * n]):.2f} | part mean bias {A[:, 2 + 2 * n].mean():+.2f} spread {np.ptp(A[:, 2 + 2 * n]):.2f}", flush=True)
    return out


def _turn(pts, ang):
    """!
    @brief Turn mm points about (15, 15) and convert to metres.
    @param pts List of (x, y) in mm.
    @param ang Degrees.
    @return Array (n, 2) in m.
    """
    a = math.radians(ang)
    return np.array([[15 + (x - 15) * math.cos(a) - (y - 15) * math.sin(a), 15 + (x - 15) * math.sin(a) + (y - 15) * math.cos(a)] for x, y in pts]) * 1e-3


def _brute(poly, nx, ny, dx, dy, m=4000):
    """!
    @brief Apertures by m point samples on every face (resolution 1/m).
    @param poly Outline (n, 2) in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param m Samples per face.
    @return (ax, ay).
    """
    from matplotlib.path import Path
    pth, t = Path(poly), (np.arange(m) + 0.5) / m
    ax, ay = np.zeros((ny, nx - 1)), np.zeros((ny - 1, nx))
    for j in range(nx - 1):
        Y = (np.arange(ny)[:, None] + t[None]) * dy
        ax[:, j] = pth.contains_points(np.c_[np.full(Y.size, (j + 1) * dx), Y.ravel()]).reshape(ny, m).mean(1)
    for i in range(ny - 1):
        X = (np.arange(nx)[:, None] + t[None]) * dx
        ay[i, :] = pth.contains_points(np.c_[X.ravel(), np.full(X.size, (i + 1) * dy)]).reshape(nx, m).mean(1)
    return ax, ay


def study_geometry():
    """!
    @brief Apertures at re-entrant corners, the vectorised apertures and their cost, the film floor with the copper held off the edge.
    @return dict of the numbers.
    """
    out = {}
    shapes = {
        "L": [[5.3, 5.3], [24.7, 5.3], [24.7, 12.45], [12.45, 12.45], [12.45, 24.7], [5.3, 24.7]],
        "T": [[0, 12], [10.37, 12], [10.37, 0], [19.63, 0], [19.63, 12], [30, 12], [30, 24], [0, 24]],
        "notch": [[5, 5], [25, 5], [25, 25], [15.6, 25], [15.4, 10.3], [15.2, 25], [5, 25]],
    }
    print("| shape | turn | prototype - brute force (faces between two board cells) | vectorised - prototype |\n| :-- | --: | --: | --: |")
    for name, pts in shapes.items():
        for ang in (0, 7, 23, 45):
            poly = _turn(pts, ang)
            g = cutgeom.cut_geometry_exact(poly, 30, 30, 1e-3, 1e-3)
            bx, by = _brute(poly, 30, 30, 1e-3, 1e-3)
            # A face that lies on the outline has board on one side only (the prototype gives 0, a sample on the line is undecided): compare faces between two board cells
            cv = g["cover"]
            mx, my = (cv[:, :-1] > 0) & (cv[:, 1:] > 0), (cv[:-1] > 0) & (cv[1:] > 0)
            onx = (np.abs(g["ax"] - bx) > 0.5) & ((cv[:, :-1] == 0) | (cv[:, 1:] == 0) | (g["ax"] == 0))
            ony = (np.abs(g["ay"] - by) > 0.5) & ((cv[:-1] == 0) | (cv[1:] == 0) | (g["ay"] == 0))
            eb = max(np.abs(g["ax"] - bx)[mx & ~onx].max(initial=0), np.abs(g["ay"] - by)[my & ~ony].max(initial=0))
            vx, vy = va.apertures(poly, 30, 30, 1e-3, 1e-3)
            ev = max(np.abs(vx - g["ax"]).max(), np.abs(vy - g["ay"]).max())
            out[f"{name}|{ang}"] = dict(brute=float(eb), vector=float(ev))
            print(f"| {name} | {ang} | {eb:.1e} | {ev:.1e} |")
    nv = 20000
    th = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    r = 0.048 + 0.0015 * np.sin(60 * th)
    poly = np.c_[0.05 + r * np.cos(th), 0.05 + r * np.sin(th)]
    import tracemalloc
    tracemalloc.start()
    t0 = time.time()
    ax, ay = va.apertures(poly, 400, 400, 0.25e-3, 0.25e-3)
    tv = time.time() - t0
    peak = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()
    t0 = time.time()
    cutgeom.cut_geometry_exact(poly[::10], 400, 400, 0.25e-3, 0.25e-3)
    tp = time.time() - t0
    cut = int(((ax > 0) & (ax < 1)).sum() + ((ay > 0) & (ay < 1)).sum())
    out["cost"] = dict(vector_s=tv, vector_mb=peak, prototype_s_2000_vertices=tp, cut_faces=cut)
    print(f"\n20 000-vertex wavy disc, 400 x 400 cells of 0.25 mm: vectorised {tv:.3f} s, {peak:.1f} MB traced, {cut} partly open faces; prototype on 2000 of the vertices {tp:.1f} s")
    print("\n| h_side | copper | node layers | smallest film factor | node cells at the floor 0.25 |\n| --: | :-- | --: | --: | --: |")
    for hs in (200.0, 1000.0, 2000.0, 1e4):
        for pat in (False, True):
            p = bd.edge_board(angle=20, h_side=hs, pattern=pat, pc=0.5)
            p.validate()
            cl.CutLinkNetwork.mode = "aperture+film"
            n = cl.CutLinkNetwork(p, 30, 30)
            f = n.film_factor[:, n._edge_lengths() > 0]
            out[f"floor|{hs:g}|{pat}"] = dict(nl=int(n.nl), fmin=float(f.min()), at_floor=int((f <= 0.25 + 1e-12).sum()))
            print(f"| {hs:g} | {'held 1.2 mm inside' if pat else 'full'} | {n.nl} | {f.min():.3f} | {(f <= 0.25 + 1e-12).sum()} |")
    return out


def main():
    """!
    @brief Run the subcommands named on the command line and save their numbers.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("geometry", study_geometry), ("sliver", study_sliver), ("tee", study_tee), ("frame", study_frame)):
        if which in (name, "all"):
            with open(os.path.join(OUT, f"review_{name}.json"), "w") as f:
                json.dump(fn(), f, indent=1)


if __name__ == "__main__":
    main()
