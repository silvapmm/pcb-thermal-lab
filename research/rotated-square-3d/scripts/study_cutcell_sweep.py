#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cutcell_sweep.py
@brief Re-measure, on the current program, how much the layered FVM depends on where the outline cuts the grid, and what the cut-cell links (option P1) change, on simple boards first.
@details The part stays fixed on a cell centre and only the outline moves, so the continuum answer changes with the position: every position has its own
         reference, the program's FVM and the links at a cell 8 times finer (1 mm cells) or 4 times finer (0.5 mm cells), their mean, with their difference printed as
         the uncertainty (`reference`). The reference is the program's own layered model at a finer cell, not an independent solver. Studies (each prints a markdown
         table and writes `out/cutsweep_<name>.json`):

         square   - 20 mm square and 24 x 12 mm rectangle, a 3 mm part (centred, or 3.5 mm off centre towards the edge), the outline shifted by k/8 of a cell
                    on both axes and turned 0 to 45 degrees; h_side 10, 100, 2000; error of the peak against the reference (bias, spread, worst case)
         patterned- the same square with a 3 x 3 via array under the part, with the top copper held 1.2 mm inside the outline (laminate nodes in the cut cells), or both
         smallcell- a board edge swept so that the cover of the edge cell goes from 0.002 to 1: the conductance ratios, the diagonal, the condition number estimate,
                    the sweeps of the SOR and the iterations of the CG, with the centroid distance left free and floored at a quarter cell
         balance  - heat to the air over the power, the edge length (sum of the side conductances over h and the perimeter, an effective thickness), the volume (sum of the covers over the polygon area)
         harness  - the boards of the frozen-number harness whose outline cuts cells, program against links at 2, 1 and 0.5 mm

         Light cases only (cells of 0.5 mm and finer on a 30 mm box stay below 0.3 GB).
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_cutcell_sweep.py [square|patterned|smallcell|balance|harness|all]   (from the repository root)
"""

import json
import os
import sys
import time

import numpy as np
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))

import fvm_cutcell as fc          # noqa: E402
import cutcell                    # noqa: E402
import rotsq                      # noqa: E402
from pcbthermal import Problem, fvm   # noqa: E402

SCHEMES = ("program", "program@exact", "aperture", "links", "links@exact", "links+strip")
OUT = os.path.join(os.path.dirname(HERE), "out")


def tmax(problem, cell, scheme):
    """!
    @brief Hottest temperature for a scheme name ("links@floor" = links with the face-to-centroid distance floored at a quarter cell).
    @param problem Problem.
    @param cell Cell in mm.
    @param scheme One of SCHEMES.
    @return degC.
    """
    if scheme == "links@floor":
        return fc.tmax(problem, cell, "links", d_min=0.25)
    return fc.tmax(problem, cell, scheme)


def rot(x, y, ang, c):
    """!
    @brief Rotate a point about (c, c).
    @param x X in mm.
    @param y Y in mm.
    @param ang Angle in degrees.
    @param c Centre of rotation (both coordinates) in mm.
    @return (x, y) in mm.
    """
    a = np.radians(ang)
    dx, dy = x - c, y - c
    return c + dx * np.cos(a) - dy * np.sin(a), c + dx * np.sin(a) + dy * np.cos(a)


def edge_board(angle=0.0, sx=0.0, sy=0.0, h_side=2000.0, shape="square", off=0.0, vias=False, pattern=False, box=30.0, pc=0.0):
    """!
    @brief A board of fixed part and moving edge: the part (and the vias) stay where they are on the grid, the board outline is moved by (sx, sy) and turned about its own centre.
    @details Moving only the outline keeps the read-out of the cell-centred peak (where the part sits against the cell centres) the same for every position, so
             the dependence of the error on the position is the effect of the cut cell and nothing else. The continuum answer changes with the position of the
             edge, so each position has its own reference (`reference`).
    @param angle Turn of the board in degrees about its own centre.
    @param sx Shift of the board in x in mm.
    @param sy Shift of the board in y in mm.
    @param h_side Edge coefficient in W/m2K.
    @param shape "square" (20 mm) or "rect" (24 x 12 mm).
    @param off Offset of the part from the box centre along x, in mm.
    @param vias True: a 3 x 3 via array of 0.3 mm drills, 1 mm pitch, centred on the part.
    @param pattern True: the top copper stops 1.2 mm inside the outline (laminate nodes where the outline cuts), the bottom layer is full copper.
    @param box Side of the box in mm.
    @param pc Shift of the part (and the vias) on both axes in mm; the sweeps set it to half a cell so that the part is centred on a cell centre and the read-out bias of the
              cell-centred peak (about 3 K for a 2 W, 3 mm part centred on a cell corner at 1 mm) stays small and the same for every position of the edge.
    @return Problem.
    """
    c = box / 2.0
    hw, hh = (10.0, 10.0) if shape == "square" else (12.0, 6.0)

    def put(pts):
        # The board corners: turned about the board centre, then shifted
        return [list(np.array(rot(c + x, c + y, angle, c)) + np.array([sx, sy])) for x, y in pts]

    p = Problem.new(box, box, 2, h_side=h_side)
    if pattern:
        p.add_zone(1, polygon=put([(-hw + 1.2, -hh + 1.2), (hw - 1.2, -hh + 1.2), (hw - 1.2, hh - 1.2), (-hw + 1.2, hh - 1.2)]), fill=1.0)
        p.add_zone(2, polygon=put([(-hw - 1, -hh - 1), (hw + 1, -hh - 1), (hw + 1, hh + 1), (-hw - 1, hh + 1)]), fill=1.0)
    else:
        p.add_full_copper()
    p.add_heater(1, 2.0, rect=(c + pc + off - 1.5, c + pc - 1.5, c + pc + off + 1.5, c + pc + 1.5), name="U")
    if vias:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                p.add_via(float(c + pc + off + i * 1.0), float(c + pc + j * 1.0), diameter=0.3)
    p.set_outline(put([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]))
    return p


def reference(kw, cell):
    """!
    @brief Continuum estimate of the peak of a board at one position: the program's FVM and the links at a cell eight times finer (a shifted edge lies on its grid lines).
    @param kw Options of `edge_board`, including the position.
    @param cell The coarse cell in mm.
    @return (reference, uncertainty): the mean of the program and links at the fine cell, and their difference (K).
    """
    fine = cell / 8.0 if cell >= 1.0 else cell / 4.0
    a = fc.tmax(edge_board(**kw), fine, "program")
    b = fc.tmax(edge_board(**kw), fine, "links")
    return 0.5 * (a + b), abs(a - b)


def stats(err):
    """!
    @brief Bias, spread and worst case of a list of errors.
    @param err List of floats (K).
    @return dict(mean, spread, worst).
    """
    a = np.array(err)
    return {"mean": float(a.mean()), "spread": float(a.max() - a.min()), "worst": float(np.abs(a).max())}


def sweep(kw, cell, ks=8, angles=range(0, 50, 5)):
    """!
    @brief Errors of every scheme over the shifts (on both axes, k/ks of a cell) and the turns of one board.
    @param kw Options of `edge_board`.
    @param cell Cell in mm.
    @param ks Number of shift steps over one cell.
    @param angles Turns in degrees.
    @return (dict scheme -> dict(shift=stats, turn=stats, all=stats), largest uncertainty of the references).
    """
    kw = dict(kw, pc=cell / 2.0)
    shifts = [dict(kw, sx=k / ks * cell, sy=k / ks * cell) for k in range(ks)]
    turns = [dict(kw, angle=float(a)) for a in angles]
    refs = [reference(q, cell) for q in shifts + turns]
    res = {}
    for s in SCHEMES:
        e = [tmax(edge_board(**q), cell, s) - r[0] for q, r in zip(shifts + turns, refs)]
        e_sh, e_tu = e[:len(shifts)], e[len(shifts):]
        res[s] = {"shift": stats(e_sh), "turn": stats(e_tu), "all": stats(e), "shift_values": e_sh, "turn_values": e_tu}
    return res, max(r[1] for r in refs)


def print_sweep(tag, cell, res, unc):
    """!
    @brief Print one markdown block of a sweep.
    @param tag Case label.
    @param cell Cell in mm.
    @param res Result of `sweep`.
    @param unc Largest uncertainty of the references (K).
    @return None.
    """
    for s in SCHEMES:
        r = res[s]
        print(f"| {tag} | {cell:g} | {unc:.2f} | {s} | {r['shift']['mean']:+.3f} | {r['shift']['spread']:.3f} | {r['turn']['mean']:+.3f} | {r['turn']['spread']:.3f} | {r['all']['worst']:.3f} |", flush=True)


HEAD = ("| board | cell (mm) | reference uncertainty (K) | scheme | shift: mean error (K) | shift: spread | turn: mean error | turn: spread | worst |\n"
        "| :-- | --: | --: | :-- | --: | --: | --: | --: | --: |")


def study_square():
    """!
    @brief Shift and turn sweeps of the square and the rectangle at three edge coefficients.
    @return dict of the numbers.
    """
    out = {}
    print("\n### square: error of the peak against the fine-cell value of the same board (K), the part fixed on the grid, the outline moved by k/8 of a cell on both axes and turned 0 to 45 degrees\n")
    print(HEAD)
    for shape, off in (("square", 0.0), ("square", 3.5), ("rect", 5.0)):
        for hs in (10.0, 100.0, 2000.0):
            for cell in (1.0, 0.5):
                kw = dict(h_side=hs, shape=shape, off=off)
                res, unc = sweep(kw, cell)
                tag = f"{shape} off {off:g} h {hs:g}"
                out[f"{tag}|{cell:g}"] = {"unc": unc, "res": res}
                print_sweep(tag, cell, res, unc)
    return out


def study_patterned():
    """!
    @brief The square with vias under the part, with the top copper held inside the outline, or both.
    @return dict of the numbers.
    """
    out = {}
    print("\n### patterned: vias and copper held 1.2 mm inside the outline, 20 mm square, part 3.5 mm off centre\n")
    print(HEAD)
    for tag, extra in (("vias", dict(vias=True)), ("pattern", dict(pattern=True)), ("vias+pattern", dict(vias=True, pattern=True))):
        for hs in (100.0, 2000.0):
            for cell in (1.0, 0.5):
                kw = dict(h_side=hs, shape="square", off=3.5, **extra)
                res, unc = sweep(kw, cell, ks=4, angles=(0, 10, 20, 30, 45))
                out[f"{tag}|{hs:g}|{cell:g}"] = {"unc": unc, "res": res}
                print_sweep(f"{tag} h {hs:g}", cell, res, unc)
    return out


def condition(K):
    """!
    @brief 1-norm condition number estimate of a sparse matrix (SuperLU factor and the Higham estimator).
    @param K Sparse symmetric matrix.
    @return float.
    """
    A = K.tocsc()
    lu = spla.splu(A)
    inv = spla.LinearOperator(A.shape, matvec=lu.solve, rmatvec=lambda v: lu.solve(v, trans="T"), dtype=float)
    return float(spla.onenormest(A) * spla.onenormest(inv))


def diagnose(p, n, scheme):
    """!
    @brief Matrix diagnostics of one network: smallest cover, largest lateral link over a whole pair, diagonal spread, condition estimate, SOR sweeps, CG iterations, peak.
    @param p Problem.
    @param n Cells along each side of the (square) box.
    @param scheme "program", "links" or "links@floor".
    @return dict.
    """
    kw = {"d_min": 0.25} if scheme == "links@floor" else {}
    if scheme == "program":
        net = fvm.Network(p, n, n)
        gx = net._harmonic(net.S[:, :, :-1], net.S[:, :, 1:]) * net.dy / net.dx
    else:
        with fc.using_cutcell("links", **kw):
            net = fvm.Network(p, n, n)
        gx, _ = net._lateral_links()
    K = net.K.tocsr()
    d = K.diagonal()
    # Largest x link of the top layer over the link of two whole cells (S of a whole cell, times dy / dx)
    ratio = float(gx[0].max() / (net.S[0][net.cover > 0.99].max() * net.dy / net.dx))
    th, res, info = net.solve_sor()
    Q = net.Q.ravel()
    dinv = 1.0 / d
    Mj = spla.LinearOperator(K.shape, matvec=lambda x: dinv * x)
    cg = {"n": 0}

    def cb(_):
        cg["n"] += 1
    spla.cg(K, Q, rtol=1e-9, atol=0.0, callback=cb, maxiter=20000, M=Mj)
    return {"mincover": float(net.cover[net.active].min()), "ratio": ratio, "diag_ratio": float(d[d > 0].min() / d.max()), "cond": condition(K),
            "sor": int(info["iterations"]), "cg": cg["n"], "tmax": float(th.max()) + p.board.ambient}


def refine(make, cells=(0.125, 0.0625)):
    """!
    @brief Continuum estimate of the peak of a board whose edges lie on the grid lines of the fine cells: Richardson step on the program's FVM.
    @param make Function returning a fresh Problem.
    @param cells The two fine cells in mm (the second is half the first).
    @return degC.
    """
    t1 = fc.tmax(make(), cells[0], "program")
    t2 = fc.tmax(make(), cells[1], "program")
    return t2 + (t2 - t1) / 3.0


def study_smallcell():
    """!
    @brief Small cells: a straight edge at covers 1 to 1/8 and a 12 mm square turned through angles (corner cells down to 1/64); links, conditioning, SOR and CG.
    @details The cover of a cell is sampled 8 x 8 (the program) or 16 x 16 (the geometry of the cut cells), so a straight edge gives covers that are multiples
             of 1/8 and a sliver thinner than that is lost: the smallest cover the program can hold on a straight edge is 1/8, on a corner 1/64.
    @return dict of the numbers.
    """
    out = {}
    head = ("| case | scheme | min cover | largest x link / whole pair | min / max diagonal | cond1 estimate | SOR sweeps | CG iterations | peak (degC) | error vs continuum (K) |\n"
            "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    print("\n### smallcell: 12 mm board in a 16 mm box at 1 mm, h_side 2000; a straight right edge (edge cell cover c) and the square turned\n")
    print(head)

    def edge_board_c(cov):
        q = Problem.new(16.0, 16.0, 2, h_side=2000.0).add_full_copper()
        q.add_heater(1, 2.0, rect=(5, 5, 8, 8), name="U")
        q.set_outline([[2, 2], [13 + cov, 2], [13 + cov, 14], [2, 14]])
        return q

    def turn_board(ang):
        q = Problem.new(16.0, 16.0, 2, h_side=2000.0).add_full_copper()
        q.add_heater(1, 2.0, rect=(7.0, 7.0, 10.0, 10.0), name="U")
        q.set_outline(rotsq.turned_square(11.0, float(ang), (8.0, 8.0)))
        return q

    def row(tag, scheme, p, ref):
        r = diagnose(p, 16, scheme)
        r["error"] = r["tmax"] - ref
        out[f"{tag}|{scheme}"] = r
        print(f"| {tag} | {scheme} | {r['mincover']:.4f} | {r['ratio']:.2f} | {r['diag_ratio']:.2e} | {r['cond']:.3e} | {r['sor']} | {r['cg']} | {r['tmax']:.3f} | {r['error']:+.3f} |", flush=True)

    for cov in (1.0, 0.5, 0.25, 0.125):
        ref = refine(lambda: edge_board_c(cov))
        for scheme in ("program", "links", "links@floor"):
            row(f"edge c={cov:g}", scheme, edge_board_c(cov), ref)
    for ang in (0, 5, 10, 20, 30, 45):
        # The continuum value of each turn is its own: the mean of the program and links at 1/8 mm (the 11 mm square is turned about its centre, the part stays)
        ref = 0.5 * (fc.tmax(turn_board(ang), 0.125, "program") + fc.tmax(turn_board(ang), 0.125, "links"))
        for scheme in ("program", "links", "links@floor"):
            row(f"turned {ang}", scheme, turn_board(ang), ref)
    return out


def study_balance():
    """!
    @brief Energy balance, edge length and volume of the cut-cell network against the polygon.
    @return dict of the numbers.
    """
    out = {}
    print("\n### balance: heat to the air over the power; edge conductance over h t P; sum of covers over the polygon area\n")
    print("| board | cell (mm) | scheme | heat / power - 1 | t_eff = sum g_side / (h P) (mm) | sum(cover) dx dy / area - 1 |\n| :-- | --: | :-- | --: | --: | --: |")
    cases = {"square turned 20": lambda: edge_board(angle=20.0), "square shifted": lambda: edge_board(sx=0.3, sy=0.3), "rect turned 33": lambda: edge_board(angle=33.0, shape="rect", off=5.0),
             "disc 20 mm": lambda: rotsq.disc_board(20.0, 1.5, 2000.0, box_mm=30.0)}
    for name, mk in cases.items():
        for cell in (1.0, 0.5):
            for scheme in ("program", "links", "links+strip"):
                p = mk()
                if scheme == "program":
                    net = fvm.Network(p, int(round(30 / cell)), int(round(30 / cell)))
                else:
                    with fc.using_cutcell(scheme):
                        net = fvm.Network(p, int(round(30 / cell)), int(round(30 / cell)))
                theta, _ = net.solve_steady("direct")
                po = net.power_out(theta)
                bal = sum(po.values()) / float(net.Q.sum()) - 1.0
                poly = p.board.outline
                area = abs(0.5 * np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
                per = float(np.sum(np.hypot(*(np.roll(poly, -1, axis=0) - poly).T)))
                # Effective thickness t_eff in mm: sum of the side conductances over h_side and the perimeter (the same for every scheme if the edge is counted exactly)
                edge = float(net.g_side.sum()) / (p.board.h_side * per) * 1e3
                vol = float(net.cover.sum()) * net.dx * net.dy / area - 1.0
                out[f"{name}|{cell:g}|{scheme}"] = {"balance": bal, "edge": edge, "volume": vol}
                print(f"| {name} | {cell:g} | {scheme} | {bal:+.2e} | {edge:.5f} | {vol:+.4f} |", flush=True)
    return out


def study_harness():
    """!
    @brief The frozen-number boards whose outline cuts cells: program against links at several cells (hottest temperature, K).
    @return dict of the numbers.
    """
    import regress_boards as rb
    out = {}
    print("\n### harness: boards of the frozen-number harness with an outline, hottest temperature (degC) and shift of `links`\n")
    print("| board | cell (mm) | program | links | links - program (K) | % of the rise |\n| :-- | --: | --: | --: | --: | --: |")
    for name in ("round_outline", "t_outline", "example_cut_to_T", "part_across_outline"):
        for cell in (2.0, 1.0, 0.5):
            p = rb.build(name)
            a = fc.tmax(p, cell, "program")
            try:
                b = fc.tmax(rb.build(name), cell, "links")
            except ValueError as e:
                print(f"| {name} | {cell:g} | {a:.3f} | refused: {e} | | |")
                continue
            rise = a - p.board.ambient
            out[f"{name}|{cell:g}"] = {"program": a, "links": b}
            print(f"| {name} | {cell:g} | {a:.3f} | {b:.3f} | {b - a:+.3f} | {100 * (b - a) / rise:+.2f} |", flush=True)
    return out


def main():
    """!
    @brief Run the studies named on the command line and save the numbers.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    table = {"square": study_square, "patterned": study_patterned, "smallcell": study_smallcell, "balance": study_balance, "harness": study_harness}
    for name, fn in table.items():
        if which in (name, "all"):
            t = time.time()
            res = fn()
            with open(os.path.join(OUT, f"cutsweep_{name}.json"), "w") as f:
                json.dump(res, f, indent=1)
            print(f"\n({name}: {time.time() - t:.0f} s)")


if __name__ == "__main__":
    main()
