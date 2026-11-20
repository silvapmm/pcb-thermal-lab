#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_copper_slabs.py
@brief Before and after of the copper slabs of the 3D solid (`feature/solid3d-copper-slabs`): the frozen boards, the thick-plate set and a copper-thickness sweep.
@details Question: what does cutting a copper layer thicker than 105 um into ceil(t / 70 um) slabs (at most 8) move in the 3D solid, and is the new number closer to an independent
         reference? Two trees are run with the same script, the one before the change (`--tree` of a checkout of `development`) and the one after, each writing a JSON file; `compare`
         prints the tables of the two.

             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/study_copper_slabs.py run --tree <checkout> --out <file.json> [--dry-run]
             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/study_copper_slabs.py compare before.json after.json

         Sets (all steady, ambient as the board's):
         * `boards`: the 20 boards of the frozen set at 2 mm (and 1 mm below 150 000 unknowns), the 3D solid only: expected bit-identical, every copper layer is 35 um.
         * `plates`: the eight plates of `research/surface-readout-models/lib/plates.py` (case 2 of Muzychka and others, thick Cu and Al plates, a copper plate on FR-4, with a via) at 0.5 mm
           against the independent solver `tests/helpers/layered3d.py` (8 sub-slabs through the thick metal, 0.5 mm in the plane): the column read-out (the mean over the thickness of the top
           layer, maximum over the cells of the source) of the 3D solid, before and after, and the temperature of its outer copper slab (the cell centre, below the face by half a slab).
         * `sweep`: the reference board (2 layers) and the example board (4 layers) with the copper of every layer set to 35 ... 420 um (the gaps kept), 3D solid, FVM and FEM at 2 mm.
         SI units inside; the tables are in kelvin (rise over the ambient) and degC where stated.
"""

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SWEEP_UM = (35.0, 70.0, 105.0, 140.0, 210.0, 350.0, 420.0)
BOARDS_SKIP_ABOVE = 150000                      # unknowns of the harness cap of the 3D solid


def load_tree(tree):
    """!
    @brief Put a checkout first on sys.path and import its pcbthermal (so that the study runs against that tree).
    @param tree Path of the checkout (the folder that holds `pcbthermal/`).
    @return The imported pcbthermal module.
    @throws RuntimeError If pcbthermal was imported from somewhere else.
    """
    tree = str(Path(tree).resolve())
    sys.path.insert(0, tree)
    sys.path.insert(1, str(Path(tree) / "tests" / "helpers"))
    sys.path.insert(2, str(Path(tree) / "tests" / "regression"))
    import pcbthermal
    if not str(Path(pcbthermal.__file__).resolve()).startswith(tree):
        raise RuntimeError(f"pcbthermal came from {pcbthermal.__file__}, not from {tree}")
    return pcbthermal


def load_plates(tree):
    """!
    @brief Import `research/surface-readout-models/lib/plates.py` of a tree by its path (the plates and their independent 3D reference).
    @param tree Path of the checkout.
    @return The plates module.
    """
    path = REPO / "research" / "surface-readout-models" / "lib" / "plates.py"
    spec = importlib.util.spec_from_file_location("plates_study", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def source_mask(problem, nx, ny):
    """!
    @brief Cells whose centre lies under the first heater (a rectangle), for the read-out of the part.
    @param problem A Problem.
    @param nx Cells along x, count.
    @param ny Cells along y, count.
    @return Boolean array (ny, nx).
    """
    xy = np.asarray(problem.heaters[0].polygon, float)
    b = problem.board
    xs = (np.arange(nx) + 0.5) * b.width / nx
    ys = (np.arange(ny) + 0.5) * b.height / ny
    return (xs[None, :] > xy[:, 0].min()) & (xs[None, :] < xy[:, 0].max()) & (ys[:, None] > xy[:, 1].min()) & (ys[:, None] < xy[:, 1].max())


def run_solid(problem, cell):
    """!
    @brief One 3D solid run with the read-outs of the study.
    @param problem A Problem.
    @param cell Cell in mm.
    @return dict with the unknowns, the slabs, seconds, peak and mean of the column of every layer, the balance and (when it exists) the outer slab temperature of the heater layer.
    """
    from pcbthermal import solid3d
    t0 = time.perf_counter()
    net = solid3d.Solid(problem, cell)
    theta, res = net.solve()
    sec = time.perf_counter() - t0
    amb = problem.board.ambient
    layers = [theta[net.copper_slabs[l]].mean(axis=0) if hasattr(net, "copper_slabs") else theta[net.board_slab[l]] for l in range(problem.board.layers)]
    m = source_mask(problem, net.nx, net.ny)
    hl = problem.heaters[0].layer
    cs = net.copper_slabs[hl] if hasattr(net, "copper_slabs") else [net.board_slab[hl]]
    outer = theta[cs[0] if hl == 0 else cs[-1]]
    pin = float(net.Q.sum())
    lost = sum(float((g * theta.ravel()).sum()) for g in net.g.values()) + float((net.g_leak * theta.ravel()).sum())
    return {"unknowns": int(net.n), "slabs": int(net.ns), "seconds": sec, "col_max": float(layers[hl][m].max() + amb), "col_mean_src": float(layers[hl][m].mean() + amb),
            "t_max": float(max(l[net.active].max() for l in layers) + amb), "layer_mean": [float(l[net.active].mean() + amb) for l in layers],
            "outer_max": float(outer[m].max() + amb), "balance": (pin - lost) / pin if pin > 0 else 0.0, "residual": res}


def set_copper(problem, um):
    """!
    @brief Set every copper layer to the same thickness and widen the board so that the dielectric gaps stay as they were.
    @param problem A Problem (modified).
    @param um Copper thickness in micrometres.
    @return None.
    """
    b = problem.board
    old = np.asarray(b.copper_thickness, float).copy()
    b.copper_thickness = [um * 1e-6] * b.layers
    if b.dielectrics is None:
        b.thickness = float(b.thickness + (um * 1e-6 - old).sum())


def run_other(problem, model, cell):
    """!
    @brief The FVM or FEM column of the heater layer (maximum under the part) at one cell.
    @param problem A Problem.
    @param model "fvm" or "fem".
    @param cell Cell in mm.
    @return dict with col_max (degC), unknowns, seconds.
    """
    t0 = time.perf_counter()
    if model == "fvm":
        from pcbthermal import fvm
        r = fvm.solve_steady(problem, cell)
    else:
        from pcbthermal import fem
        r = fem.solve_steady(problem, cell)
    T = np.asarray(r.T)
    m = source_mask(problem, T.shape[2], T.shape[1])
    return {"col_max": float(T[problem.heaters[0].layer][m].max()), "seconds": time.perf_counter() - t0}


def reference_with_laminate(plates, spec, dx_mm=0.5):
    """!
    @brief The independent 3D solution of a one-layer plate WITH the 1 um laminate that the program's board has under its copper (`plates.problem` makes thickness 1.0001 t).
    @details `plates.reference` leaves that laminate out (its slab list is the metal alone); under a film of 1000 W/m2K at 40 000 W/m2 the 1 um of FR-4 (3.3e-6 m2K/W) is worth 0.13 K, which is
             all of the gap between the 3D solid and `plates.reference` on the 10 mm aluminium plate. A plate with a real laminate (`kind` "two") already has it in `plates.reference`.
    @param plates The plates module.
    @param spec One entry of PLATES.
    @param dx_mm Plan cell in mm.
    @return dict with col (the hottest cell of the top layer mean, degC) and surf (the hottest surface cell, degC).
    """
    import layered3d as L3
    name, kind, t, k, a, P, h, via = spec
    if kind != "one":
        r = plates.reference(spec, dx_mm)
        return {"col": r["col"], "surf": r["surf"]}
    n = int(round(plates.W_MM / dx_mm))
    p = plates.problem(spec)
    t_lam = float(p.board.slab_thicknesses()[0] - p.board.copper_thickness[0])
    slabs = [(t * 1e-3, k, 8), (t_lam, p.board.materials.k_fr4_through, 4)]
    r = L3.solve(dx_mm * 1e-3, n, n, slabs, tuple(v * 1e-3 for v in plates.rect_mm(a)), P, 0.0, h)
    dz = np.array(r["dz"])
    w = dz[:8] / dz[:8].sum()
    col = np.tensordot(w, r["T"][:8], axes=(0, 0))
    m = r["mask_source"]
    return {"col": plates.AMB + float(col[m].max()), "surf": plates.AMB + float(r["surface_top"][m].max())}


def cmd_run(a):
    """!
    @brief Run the three sets on a tree and write the JSON.
    @param a Parsed arguments (tree, out, sets, dry_run).
    @return int exit code.
    """
    load_tree(a.tree)
    import regress_boards as B
    plates = load_plates(a.tree)
    out = {"tree": str(Path(a.tree).resolve()), "boards": {}, "plates": {}, "sweep": {}}
    jobs = []
    if "boards" in a.sets:
        jobs += [("boards", n, c) for n in B.board_names() for c in (2.0, 1.0)]
    if "plates" in a.sets:
        jobs += [("plates", s[0], c) for s in plates.PLATES for c in (0.5,)]
    if "sweep" in a.sets:
        jobs += [("sweep", f"{n}|{u:g}", 2.0) for n in ("reference_board", "example_board") for u in SWEEP_UM]
    if a.dry_run:
        for j in jobs:
            print("would run", j)
        print(len(jobs), "jobs")
        return 0
    from pcbthermal import solid3d
    for kind, name, cell in jobs:
        key = f"{name}|{cell:g}"
        if kind == "boards":
            p = B.build(name)
            n = solid3d.unknowns(p, cell)[0]
            if n > BOARDS_SKIP_ABOVE:
                out["boards"][key] = {"skipped": n}
                continue
            out["boards"][key] = run_solid(p, cell)
        elif kind == "plates":
            spec = next(s for s in plates.PLATES if s[0] == name)
            ref = plates.reference(spec, cell)
            out["plates"][key] = {"solid": run_solid(plates.problem(spec), cell), "ref": ref, "ref_lam": reference_with_laminate(plates, spec, cell)}
        else:
            bname, um = name.split("|")
            p = B.build(bname)
            set_copper(p, float(um))
            rec = {"solid3d": run_solid(p, cell)}
            for model in ("fvm", "fem"):
                try:
                    rec[model] = run_other(p, model, cell)
                except Exception as exc:                       # a model that refuses a board is a result
                    rec[model] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            out["sweep"][key] = rec
        print("done", kind, key, flush=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    return 0


def cmd_compare(a):
    """!
    @brief Print the before and after tables.
    @param a Parsed arguments (before, after).
    @return int exit code.
    """
    A, B = (json.loads(Path(f).read_text()) for f in (a.before, a.after))
    print("### Frozen boards, 3D solid (column peak under the part, degC, and the layer means)\n")
    print("| record | slabs before | slabs after | t_max before | t_max after | difference (K) |\n| :-- | --: | --: | --: | --: | --: |")
    worst = 0.0
    for k, va in A["boards"].items():
        vb = B["boards"].get(k, {})
        if "skipped" in va or "skipped" in vb:
            continue
        d = vb["t_max"] - va["t_max"]
        d2 = max(abs(x - y) for x, y in zip(va["layer_mean"], vb["layer_mean"]))
        worst = max(worst, abs(d), d2)
        print(f"| {k} | {va['slabs']} | {vb['slabs']} | {va['t_max']:.9f} | {vb['t_max']:.9f} | {d:+.3e} |")
    print(f"\nlargest difference of t_max or of a layer mean: {worst:.3e} K\n")
    print("### Plates at 0.5 mm: column maximum under the source against the independent 3D solver (degC)\n")
    print("| plate | slabs b/a | solid before | solid after | independent (with the 1 um laminate) | before - ref (K) | after - ref (K) | outer slab after (degC) | independent surface (degC) |\n| :-- | :-: | --: | --: | --: | --: | --: | --: | --: |")
    for k, va in A["plates"].items():
        vb = B["plates"][k]
        ref = va["ref_lam"]
        print(f"| {k.rsplit('|', 1)[0]} | {va['solid']['slabs']}/{vb['solid']['slabs']} | {va['solid']['col_max']:.3f} | {vb['solid']['col_max']:.3f} | {ref['col']:.3f} | "
              f"{va['solid']['col_max'] - ref['col']:+.3f} | {vb['solid']['col_max'] - ref['col']:+.3f} | {vb['solid']['outer_max']:.3f} | {ref['surf']:.3f} |")
    print("\n### Copper sweep at 2 mm: column maximum under the part (degC)\n")
    print("| board | Cu um | slabs b/a | solid before | solid after | FVM | FEM | after - FVM | after - FEM |\n| :-- | --: | :-: | --: | --: | --: | --: | --: | --: |")
    for k, va in A["sweep"].items():
        vb = B["sweep"][k]
        n, u, _ = k.split("|")
        fe = vb["fem"].get("col_max")
        fv = vb["fvm"].get("col_max")
        print(f"| {n} | {u} | {va['solid3d']['slabs']}/{vb['solid3d']['slabs']} | {va['solid3d']['col_max']:.3f} | {vb['solid3d']['col_max']:.3f} | "
              f"{fv:.3f} | {fe if fe is None else format(fe, '.3f')} | {vb['solid3d']['col_max'] - fv:+.3f} | {'' if fe is None else format(vb['solid3d']['col_max'] - fe, '+.3f')} |")
    return 0


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Arguments (default sys.argv[1:]).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tree", required=True, help="checkout whose pcbthermal is measured")
    r.add_argument("--out", help="JSON file written")
    r.add_argument("--sets", nargs="+", default=["boards", "plates", "sweep"], choices=["boards", "plates", "sweep"])
    r.add_argument("--dry-run", action="store_true", help="list the jobs and stop")
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else cmd_compare(a)


if __name__ == "__main__":
    sys.exit(main())
