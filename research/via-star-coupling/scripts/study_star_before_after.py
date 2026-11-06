#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_star_before_after.py
@brief Does the star coupling of the via (viawell.py) keep what the mean-potential via got right and fix what it got wrong? The same cases run on two program trees.
@details The program tree is chosen with `--tree` (a checkout of the commit before the star coupling for "before", the repository root for "after"); each run writes one JSON
         file, and `--compare before.json after.json` prints the tables side by side. The cases:
         * `doc`: the 30 x 30 mm board of docs/theory.md 2.2 (copper ending through the via), cold spot, via effect and positive entries of K, FVM and FDM at 1 to 0.125 mm;
         * `ten`: the 10 x 10 mm boards of research/via-partial-copper (copper edge through, past and before the via, tracks, island, via on bare laminate): via effect of the FVM
           against the 3D solid at 1/20 mm (the tabulated references of that folder's README 3, not re-run here);
         * `array`: the dense 10 x 10 array of 0.3 mm vias of tests/test_maximum_principle.py and the 3 x 3 board of tests/test_point_via.py (copper-fill gain, -4.51 K resolved);
         * `example`: the example board, FVM and FDM, 1, 0.5 and 0.25 mm: maximum temperature and positive off-diagonal entries of K;
         * `solvers`: direct, CG and block SOR on the documented board and the example board;
         * `cost`: seconds to build the network and non-zeros of K for a lone-via board, the example board and a board with 8500 vias.
         Run from the repository root:
         `.venv/bin/python research/via-star-coupling/scripts/study_star_before_after.py --tree . --out out/after.json`
         `.venv/bin/python research/via-star-coupling/scripts/study_star_before_after.py --compare out/before.json out/after.json`
"""

import argparse
import json
import logging
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

# 3D solid at 1/20 mm (research/via-partial-copper README 3 and 9.2): the via effect in K of the ten-millimetre boards
REFERENCE_3D = {"edge d=0.0": 7.39, "edge d=0.3": 8.86, "edge d=-0.3": 0.94, "track w=0.4": 22.62, "track w=1.0": 25.80, "island s=1.2": 38.79, "bare": 9.81}
PLAN = [("edge d=0.0", "edge", dict(delta=0.0)), ("edge d=0.3", "edge", dict(delta=0.3)), ("edge d=-0.3", "edge", dict(delta=-0.3)), ("track w=0.4", "track", dict(width=0.4)),
        ("track w=1.0", "track", dict(width=1.0)), ("island s=1.2", "island", dict(side=1.2)), ("bare", "bare", dict()), ("bare h=2000", "bare", dict(h=2000.0, power=2.0))]


def setup(tree):
    """!
    @brief Put the program tree on the import path and load the helpers of its tests and of the research folder.
    @param tree Root of the program tree to measure.
    @return Tuple of modules (np, cases, tmp, tpv, fvm, fdm, simulate, SolverOptions, load_project, model, Problem).
    """
    tree = os.path.abspath(tree)
    for p in (os.path.join(tree, "research", "via-partial-copper", "lib"), os.path.join(tree, "tests"), tree):
        sys.path.insert(0, p)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    logging.disable(logging.WARNING)
    import numpy as np
    import cases
    import test_maximum_principle as tmp
    import test_point_via as tpv
    from pcbthermal import Problem, SolverOptions, fdm, fvm, model, simulate
    from pcbthermal.project import load_project
    model.reload_libraries()
    return np, cases, tmp, tpv, fvm, fdm, simulate, SolverOptions, load_project, model, Problem


def rise_max(problem, kind, cell, tmp):
    """!
    @brief Maximum rise over the copper layers, the number of positive off-diagonal entries of K and the cold spot of one layered solve.
    @param problem Problem.
    @param kind "fvm" or "fdm".
    @param cell Cell in mm.
    @param tmp The module tests/test_maximum_principle (network, positive_entries, cold_spot).
    @return dict tmax, pos, cold.
    """
    net = tmp.network(problem, kind, cell)
    theta, _ = net.solve_steady()
    return dict(tmax=float(theta[:problem.board.layers].max()), pos=tmp.positive_entries(net)[0], cold=float(tmp.cold_spot(problem, net, theta)) if problem.vias else 0.0)


def effect(make, kind, cell, tmp):
    """!
    @brief Via effect (rise without the via minus rise with it), K.
    @param make Function (with_via) -> Problem.
    @param kind "fvm" or "fdm".
    @param cell Cell in mm.
    @param tmp The module tests/test_maximum_principle.
    @return tuple (effect, with-via result dict).
    """
    a, b = rise_max(make(False), kind, cell, tmp), rise_max(make(True), kind, cell, tmp)
    return a["tmax"] - b["tmax"], b


def measure(tree, quick):
    """!
    @brief Run every case on the program tree.
    @param tree Root of the program tree.
    @param quick True: fewer cells.
    @return dict key -> value (JSON friendly).
    """
    np, cases, tmp, tpv, fvm, fdm, simulate, SolverOptions, load_project, model, Problem = setup(tree)
    out = {}
    cells = [1.0, 0.5, 0.25] if quick else [1.0, 0.5, 0.25, 0.125]

    for kind in ("fvm", "fdm"):
        for cell in cells:
            def make(v):
                p = tmp.copper_edge_board()
                if not v:
                    p.vias = []
                return p
            e, r = effect(make, kind, cell, tmp)
            out[f"doc|{kind}|{cell}"] = dict(effect=e, cold=r["cold"], pos=r["pos"], tmax=r["tmax"])
            print("doc", kind, cell, out[f"doc|{kind}|{cell}"], flush=True)

    for label, name, kw in PLAN:
        f = cases.CASES[name]
        for kind, cs in (("fvm", cells), ("fdm", [0.5, 0.25])):
            for cell in cs:
                e, r = effect(lambda v: f(with_via=v, **kw), kind, cell, tmp)
                ref = REFERENCE_3D.get(label)
                out[f"ten|{label}|{kind}|{cell}"] = dict(effect=e, ref=ref, err_pct=None if ref is None else 100.0 * (e / ref - 1.0), cold=r["cold"], pos=r["pos"])
                print("ten", label, kind, cell, out[f"ten|{label}|{kind}|{cell}"], flush=True)

    for cell in ([2.0, 1.0, 0.5] if quick else [2.0, 1.0, 0.5, 0.25]):
        e, r = effect(lambda v: (lambda p: (p if v else (setattr(p, "vias", []) or p)))(tmp.dense_via_board()), "fvm", cell, tmp)
        out[f"array10|fvm|{cell}"] = dict(effect=e, pos=r["pos"], cold=r["cold"])
        print("array10", cell, out[f"array10|fvm|{cell}"], flush=True)
    for kind in ("fvm", "fdm"):
        for cell in cells:
            g = tpv.gain(tpv.array_board(0.0), tpv.array_board(385.0), kind, cell)
            out[f"gain3x3|{kind}|{cell}"] = dict(gain=g)
            print("gain3x3", kind, cell, g, flush=True)

    example = load_project(os.path.join(os.path.abspath(tree), "examples", "example_board.pcbt.json")).problem
    for kind in ("fvm", "fdm"):
        for cell in (2.0, 1.0, 0.5, 0.25):
            r = rise_max(example, kind, cell, tmp)
            t_max = float(simulate(example, SolverOptions(models=(kind,), cell_mm=cell)).results[kind].t_max)
            out[f"example|{kind}|{cell}"] = dict(t_max=t_max, pos=r["pos"], cold=r["cold"])
            print("example", kind, cell, out[f"example|{kind}|{cell}"], flush=True)

    for name, make_problem, cell in (("documented", tmp.copper_edge_board, 0.5), ("example", lambda: example, 1.0)):
        p = make_problem()
        b = p.board
        net = fvm.Network(p, max(int(round(b.width * 1000.0 / cell)), 2), max(int(round(b.height * 1000.0 / cell)), 2))
        ref, _ = net.solve_steady("direct")
        row = {}
        for method in ("cg", "sor"):
            n2 = fvm.Network(p, net.nx, net.ny)
            if method == "sor":
                th, _res, _info = n2.solve_sor(omega=None, tol=1e-12)
            else:
                th, _res = n2.solve_steady("cg")
            row[method] = float(np.abs(th - ref).max())
        out[f"solvers|{name}|{cell}"] = row
        print("solvers", name, cell, row, flush=True)

    # Cost: the network build (the via blocks) and the size of K
    lone = tpv.small_board([(5.0, 5.0, 0.3)])
    many = tmp.dense_via_board()
    big = Problem.new(120, 80, 4)
    for layer in (1, 2, 3, 4):
        big.add_zone(layer, rect=(2, 2, 118, 78))
    big.add_heater(1, 5.0, rect=(50, 30, 70, 50))
    rng = np.random.default_rng(3)
    for x, y in zip(rng.uniform(3, 117, 8500), rng.uniform(3, 77, 8500)):
        big.add_via(float(x), float(y), 0.3)
    for name, p, cell in (("lone via 10 mm", lone, 0.25), ("array10 60 mm", many, 0.25), ("8500 vias 120 x 80 mm", big, 0.5)):
        b = p.board
        t0 = time.perf_counter()
        net = fvm.Network(p, max(int(round(b.width * 1000.0 / cell)), 2), max(int(round(b.height * 1000.0 / cell)), 2))
        build = time.perf_counter() - t0
        t1 = time.perf_counter()
        net.solve_steady()
        out[f"cost|{name}|{cell}"] = dict(build_s=build, solve_s=time.perf_counter() - t1, unknowns=int(net.K.shape[0]), nnz=int(net.K.nnz), vias=len(p.vias))
        print("cost", name, out[f"cost|{name}|{cell}"], flush=True)
    return out


def compare(a_path, b_path):
    """!
    @brief Print the cases of two runs side by side.
    @param a_path JSON of the "before" run.
    @param b_path JSON of the "after" run.
    @return None.
    """
    a, b = json.load(open(a_path)), json.load(open(b_path))
    for key in sorted(set(a) | set(b)):
        x, y = a.get(key), b.get(key)
        print(f"{key:44s}", "before", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in (x or {}).items()})
        print(f"{'':44s}", "after ", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in (y or {}).items()})


def main():
    """!
    @brief Command line: measure a tree or compare two runs.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tree", default=REPO, help="root of the program tree to measure")
    ap.add_argument("--out", help="JSON file to write")
    ap.add_argument("--quick", action="store_true", help="skip the finest cells")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args()
    if a.compare:
        compare(*a.compare)
        return
    result = measure(a.tree, a.quick)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump(result, fh, indent=1)


if __name__ == "__main__":
    main()
