#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference_set.py
@brief Is the star coupling of the via better than the mean-potential via on boards it was not built on? The review's own reference set against the 3D solid.
@details Fifteen 10 x 10 mm boards (two layers unless stated, 1.6 mm, 35 um copper, 50 W/m2K on both faces, insulated edges), none of them taken from the studies that built
         the star: a lone via on full copper (drill 0.2, 0.3, 0.6, 1.0, 1.5 mm; four layers for 0.3 mm), 3 x 3 arrays at 1.0 and 0.6 mm pitch, a via at the corner of a
         copper quadrant (a quarter of its barrel touches the top copper), a 0.25 mm track ending on the via, a via on bare laminate 0.3, 0.6 and 1.0 mm outside a copper edge
         (the heater on the copper), a via 0.35 mm from an insulated edge and from a corner. The quantity is the via effect (maximum rise without the via minus with it).
         Modes:
         * `layered --tree T --out F`: FVM and FDM via effect at 2, 1, 0.5, 0.25 and 0.125 mm on the program tree T (a checkout of the commit before the star for "before");
         * `solid --tree T --out F --cell C --ndiel N [--cases a,b]`: the 3D solid (unchanged by the star) at a plan cell C and N dielectric slabs (the convergence through the
           thickness matters: the edge-through-via case reads 7.29 / 7.04 / 6.93 K at 4 / 8 / 16 slabs at 0.1 mm);
         * `dead --tree T`: the example board with the barrel plating set to 1 nm (the via can carry no heat): any change of the maximum is an artefact of the coupling;
         * `table --solid F --before F --after F`: the signed errors of the via effect against the 3D solid (0.1 mm, 8 slabs).
         Run from the repository root, for example
         `.venv/bin/python research/via-star-coupling/scripts/study_reference_set.py layered --tree . --out research/via-star-coupling/out/ref_after.json`.
"""

import argparse
import copy
import json
import logging
import os
import sys
import time

W, C = 10.0, 5.0                                                     # board side and board centre in mm


def setup(tree):
    """!
    @brief Put a program tree on the import path and return its modules.
    @param tree Root of the program tree.
    @return Tuple (Problem, fvm, fdm, solid3d, load_project).
    """
    sys.path.insert(0, os.path.abspath(tree))   # the tree is the repository root of this checkout
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    logging.disable(logging.WARNING)
    from pcbthermal import Problem, fdm, fvm, model, solid3d
    from pcbthermal.project import load_project
    model.reload_libraries()
    return Problem, fvm, fdm, solid3d, load_project


def make_cases(Problem):
    """!
    @brief The fifteen boards of the set, as functions of with_via.
    @param Problem The Problem class of the tree.
    @return dict name -> function(with_via: bool) -> Problem.
    """

    def base(layers=2):
        """!
        @brief Empty board of the set.
        @param layers Number of copper layers.
        @return Problem.
        """
        return Problem.new(W, W, layers, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)

    def full(d, layers, v):
        """!
        @brief Full copper on every layer, a 1 x 1 mm, 0.5 W heater over a lone via at the centre.
        @param d Drill in mm.
        @param layers Copper layers.
        @param v With the via.
        @return Problem.
        """
        p = base(layers)
        for layer in range(1, layers + 1):
            p.add_zone(layer, rect=(0, 0, W, W))
        p.add_heater(1, 0.5, rect=(C - 0.5, C - 0.5, C + 0.5, C + 0.5), name="Q")
        if v:
            p.add_via(C, C, d)
        return p

    def array(pitch, v):
        """!
        @brief Full copper, 3 x 3 vias of 0.3 mm under a 3 x 3 mm, 1 W heater.
        @param pitch Via pitch in mm.
        @param v With the vias.
        @return Problem.
        """
        p = base()
        for layer in (1, 2):
            p.add_zone(layer, rect=(0, 0, W, W))
        p.add_heater(1, 1.0, rect=(C - 1.5, C - 1.5, C + 1.5, C + 1.5), name="Q")
        if v:
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    p.add_via(C + i * pitch, C + j * pitch, 0.3)
        return p

    def quarter(v):
        """!
        @brief Top copper is the quadrant x <= C, y <= C (a quarter of the barrel touches it), heater on it; full bottom plane.
        @param v With the via.
        @return Problem.
        """
        p = base()
        p.add_zone(2, rect=(0, 0, W, W))
        p.add_zone(1, rect=(1, 1, C, C))
        p.add_heater(1, 0.3, rect=(C - 2.5, C - 2.5, C - 0.5, C - 0.5), name="Q")
        if v:
            p.add_via(C, C, 0.3)
        return p

    def track(v):
        """!
        @brief A 2 x 2 mm heater pad and a 0.25 mm track 1.5 mm long ending at the via centre; full bottom plane.
        @param v With the via.
        @return Problem.
        """
        p = base()
        p.add_zone(2, rect=(0, 0, W, W))
        xp = C - 1.5
        p.add_zone(1, rect=(xp - 2, C - 1, xp, C + 1))
        p.add_zone(1, rect=(xp, C - 0.125, C, C + 0.125))
        p.add_heater(1, 0.3, rect=(xp - 2, C - 1, xp, C + 1), name="Q")
        if v:
            p.add_via(C, C, 0.3)
        return p

    def bareout(g, v):
        """!
        @brief Top copper ends g mm before the via (the via is on bare laminate), a 2 x 2 mm, 0.5 W heater on the copper at its edge; full bottom plane.
        @param g Gap from the copper edge to the via centre in mm.
        @param v With the via.
        @return Problem.
        """
        p = base()
        p.add_zone(2, rect=(0, 0, W, W))
        p.add_zone(1, rect=(1, 1, C - g, W - 1))
        p.add_heater(1, 0.5, rect=(C - g - 2, C - 1, C - g, C + 1), name="Q")
        if v:
            p.add_via(C, C, 0.3)
        return p

    def edgevia(corner, v):
        """!
        @brief Full copper, a 1 x 1 mm, 0.5 W heater at the left edge (or the corner) over a via 0.35 mm from the edge (both edges at the corner).
        @param corner True for the corner.
        @param v With the via.
        @return Problem.
        """
        p = base()
        for layer in (1, 2):
            p.add_zone(layer, rect=(0, 0, W, W))
        y0 = 0.0 if corner else C - 0.5
        p.add_heater(1, 0.5, rect=(0, y0, 1.0, y0 + 1.0), name="Q")
        if v:
            p.add_via(0.35, 0.35 if corner else C, 0.3)
        return p

    out = {f"full d{d}": (lambda v, d=d: full(d, 2, v)) for d in (0.2, 0.3, 0.6, 1.0, 1.5)}
    out["full4 d0.3"] = lambda v: full(0.3, 4, v)
    out["arr3 p1.0"] = lambda v: array(1.0, v)
    out["arr3 p0.6"] = lambda v: array(0.6, v)
    out["quarter"] = quarter
    out["track 0.25"] = track
    for g in (0.3, 0.6, 1.0):
        out[f"bareout g{g}"] = (lambda v, g=g: bareout(g, v))
    out["edge 0.35"] = lambda v: edgevia(False, v)
    out["corner 0.35"] = lambda v: edgevia(True, v)
    return out


def layered_max(p, fvm, fdm, kind, cell):
    """!
    @brief Maximum rise over the copper layers of one layered solve.
    @param p Problem.
    @param fvm The fvm module of the tree.
    @param fdm The fdm module of the tree.
    @param kind "fvm" or "fdm".
    @param cell Cell in mm.
    @return float rise in K.
    """
    b = p.board
    net = fdm.Network(p, cell) if kind == "fdm" else fvm.Network(p, max(int(round(b.width * 1e3 / cell)), 2), max(int(round(b.height * 1e3 / cell)), 2))
    theta, _ = net.solve_steady()
    return float(theta[:b.layers].max())


def load(path):
    """!
    @brief Read a JSON result file, empty when it does not exist.
    @param path File.
    @return dict.
    """
    return json.load(open(path)) if path and os.path.exists(path) else {}


def save(path, data):
    """!
    @brief Write a JSON result file (the folder is created).
    @param path File.
    @param data dict.
    @return None.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)


def table(solid, before, after):
    """!
    @brief Print the signed error of the via effect against the 3D solid at 0.1 mm and 8 slabs, before -> after, per model and cell.
    @param solid dict of the solid runs.
    @param before dict of the layered runs on the tree before.
    @param after dict of the layered runs on the tree after.
    @return None.
    """
    names = list(dict.fromkeys(k.split("|")[0] for k in before))
    for kind in ("fvm", "fdm"):
        print(f"== {kind}: signed error of the via effect, per cent, before -> after")
        for n in names:
            ref = solid.get(f"{n}|solid|0.1|8", solid.get(f"{n}|solid|0.1|4"))
            row = f"{n:14s} 3D {ref:7.3f} K "
            for c in ("2.0", "1.0", "0.5", "0.25", "0.125"):
                e0, e1 = before[f"{n}|{kind}|{c}"], after[f"{n}|{kind}|{c}"]
                row += f"| {c}: {100 * (e0 / ref - 1):+5.0f} -> {100 * (e1 / ref - 1):+5.0f} "
            print(row)


def main():
    """!
    @brief Command line (see the file header).
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("mode", choices=("layered", "solid", "dead", "table"))
    ap.add_argument("--tree", default=os.getcwd(), help="root of the program tree")
    ap.add_argument("--out", help="JSON file (results are merged into it)")
    ap.add_argument("--cell", type=float, default=0.1, help="plan cell of the 3D solid in mm")
    ap.add_argument("--ndiel", type=int, default=8, help="dielectric slabs of the 3D solid")
    ap.add_argument("--cases", help="comma-separated case names (solid mode)")
    ap.add_argument("--solid", help="table: JSON of the solid runs")
    ap.add_argument("--before", help="table: JSON of the layered runs before")
    ap.add_argument("--after", help="table: JSON of the layered runs after")
    a = ap.parse_args()
    if a.mode == "table":
        table(load(a.solid), load(a.before), load(a.after))
        return
    Problem, fvm, fdm, solid3d, load_project = setup(a.tree)
    res = load(a.out)
    if a.mode == "dead":
        p = load_project(os.path.join(os.path.abspath(a.tree), "examples", "example_board.pcbt.json")).problem
        for kind in ("fvm", "fdm"):
            for cell in (2.0, 1.0, 0.5, 0.25):
                bare = copy.deepcopy(p)
                bare.vias = []
                dead = copy.deepcopy(p)
                dead.board.via_plating = 1e-9                     # a barrel that carries no heat (and no fill that conducts)
                for v in dead.vias:
                    if hasattr(v, "fill_k"):
                        v.fill_k = 0.0
                t0, t1, t2 = (layered_max(x, fvm, fdm, kind, cell) for x in (bare, dead, p))
                print(f"{kind} {cell}: dead-via effect {t0 - t1:.3f} K, real via effect {t0 - t2:.3f} K", flush=True)
        return
    cases = make_cases(Problem)
    if a.mode == "layered":
        for name, f in cases.items():
            for kind in ("fvm", "fdm"):
                for cell in (2.0, 1.0, 0.5, 0.25, 0.125):
                    e = layered_max(f(False), fvm, fdm, kind, cell) - layered_max(f(True), fvm, fdm, kind, cell)
                    res[f"{name}|{kind}|{cell}"] = e
                    print(name, kind, cell, round(e, 4), flush=True)
    else:
        for name in (a.cases.split(",") if a.cases else list(cases)):
            t = time.time()
            e = solid3d.solve_steady(cases[name](False), a.cell, n_diel=a.ndiel).t_max - solid3d.solve_steady(cases[name](True), a.cell, n_diel=a.ndiel).t_max
            res[f"{name}|solid|{a.cell}|{a.ndiel}"] = e
            print(name, a.cell, a.ndiel, round(e, 4), f"{time.time() - t:.1f} s", flush=True)
            if a.out:
                save(a.out, res)
    if a.out:
        save(a.out, res)


if __name__ == "__main__":
    main()
