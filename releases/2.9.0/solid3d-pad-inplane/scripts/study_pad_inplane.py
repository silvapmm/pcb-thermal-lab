#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_pad_inplane.py
@brief Before and after of the in-plane conductivity of the interface pad of the 3D solid (`fix/solid3d-pad-inplane`, item e16 of 2.9.0): boards with a metal block against the independent solver, the FVM and the FEM.
@details Question: how far is the 3D solid from a pad that conducts across only (a contact resistance), and what does giving the pad slab the FEM's in-plane conductivity (`K_PAD_INPLANE` = 1e-3 W/mK) change?
         Two trees are run with the same script, the one before (a checkout of `development`) and the one after (this branch); each writes a JSON file and `compare` prints the tables.

             .venv/bin/python releases/2.9.0/solid3d-pad-inplane/scripts/study_pad_inplane.py run --tree <checkout> --out <file.json> [--cells 2,1]
             .venv/bin/python releases/2.9.0/solid3d-pad-inplane/scripts/study_pad_inplane.py compare before.json after.json

         Cases (two-layer 40 x 30 mm board, full copper, h 10 W/m2K on both faces, insulated edges, a 8 x 8 mm part of 3 W at (16, 10, 24, 18) on the top copper): a 5 mm aluminium block
         (204 W/mK, h_extra 0) at (12, 8, 28, 22) on the TOP face (directly over the part), the same block over the WHOLE board, and a 3 mm block on the BOTTOM face, with the contact resistance
         5e-4, 5e-3 and 5e-2 m2K/W. Reference: `tests/helpers/stack3d.py` (anisotropic cells, the pad with no in-plane conduction at all, the board slabs read once from the program's own slabs).
         SI units inside; temperatures are the rise over the ambient in kelvin.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RCS = (5.0e-4, 5.0e-3, 5.0e-2)
HEATER = (16.0, 10.0, 24.0, 18.0)
CASES = {"top_block": ("top", (12.0, 8.0, 28.0, 22.0), 5.0), "top_whole": ("top", (0.0, 0.0, 40.0, 30.0), 5.0), "bottom_block": ("bottom", (12.0, 8.0, 28.0, 22.0), 3.0)}


def load_tree(tree):
    """!
    @brief Put a checkout first on sys.path and import its pcbthermal; the reference solver always comes from this branch.
    @param tree Path of the checkout (the folder that holds `pcbthermal/`).
    @return The imported pcbthermal module.
    @throws RuntimeError If pcbthermal came from somewhere else.
    """
    tree = str(Path(tree).resolve())
    sys.path.insert(0, tree)
    sys.path.insert(1, str(REPO / "tests" / "helpers"))
    import pcbthermal
    if not str(Path(pcbthermal.__file__).resolve()).startswith(tree):
        raise RuntimeError(f"pcbthermal came from {pcbthermal.__file__}, not from {tree}")
    return pcbthermal


def make_problem(case, rc, power=3.0):
    """!
    @brief The board of one case.
    @param case Key of CASES.
    @param rc Contact resistance of the block in m2K/W.
    @param power Power of the part in W.
    @return Problem.
    """
    from pcbthermal import Problem
    face, rect, t_mm = CASES[case]
    p = Problem.new(width_mm=40.0, height_mm=30.0, layers=2, h_top=10.0, h_bottom=10.0, h_side=None)
    p.add_full_copper([1, 2])
    p.add_heater(1, power, rect=HEATER, name="U1")
    p.add_heatsink(1 if face == "top" else 2, 0.0, rect=rect, name="blk", thickness_mm=t_mm, contact_r=rc)
    return p


def mask_of(rect_mm, nx, ny, w_mm=40.0, h_mm=30.0):
    """!
    @brief Cells whose centre lies inside a rectangle.
    @param rect_mm (x0, y0, x1, y1) in mm.
    @param nx Cells along x.
    @param ny Cells along y.
    @param w_mm Board width in mm.
    @param h_mm Board height in mm.
    @return Boolean array (ny, nx).
    """
    xs = (np.arange(nx) + 0.5) * w_mm / nx
    ys = (np.arange(ny) + 0.5) * h_mm / ny
    return (xs[None, :] > rect_mm[0]) & (xs[None, :] < rect_mm[2]) & (ys[:, None] > rect_mm[1]) & (ys[:, None] < rect_mm[3])


def program_solid(problem, cell, face, rect, t_mm):
    """!
    @brief The 3D solid of the tree: the read-outs of the study and the slabs of the board (read once, for the reference).
    @param problem Problem.
    @param cell Cell in mm.
    @param face "top" or "bottom".
    @param rect Block rectangle in mm.
    @param t_mm Block thickness in mm.
    @return Tuple (dict of read-outs in K, list of the board slabs as (kind, dz, kx, kz) of cell [0, 0]).
    """
    from pcbthermal import solid3d
    net = solid3d.Solid(problem, cell)
    theta, res = net.solve()
    amb = problem.board.ambient
    m = mask_of(HEATER, net.nx, net.ny)
    cu = [theta[net.copper_slabs[l]].mean(axis=0) for l in range(2)]
    ids = [s for s, sl in enumerate(net.slabs) if sl["kind"] == "blk"]
    blk = theta[ids]
    bm = mask_of(rect, net.nx, net.ny)
    out = {"col_max": float(cu[0][m].max()), "col_mean_part": float(cu[0][m].mean()), "layer_mean_top": float(cu[0].mean()), "layer_mean_bottom": float(cu[1].mean()),
           "t_max": float(max(cu[0].max(), cu[1].max())), "block_max": float(blk[:, bm].max()), "block_mean": float(blk[:, bm].mean()), "unknowns": int(net.n), "slabs": int(net.ns),
           "residual": res, "amb": amb}
    first, last = net.first_board, net.last_board
    board = [(net.slabs[s]["kind"], float(net.slabs[s]["dz"][0, 0]), float(net.slabs[s].get("kphys", net.slabs[s]["kx"])[0, 0]), float(net.slabs[s]["kz"][0, 0])) for s in range(first, last + 1)]
    return out, board


def reference(problem, cell, face, rect, t_mm, rc, board):
    """!
    @brief The independent solve of the same board with the pad as a pure contact resistance.
    @param problem Problem (the block and the part are read from it).
    @param cell Cell in mm.
    @param face "top" or "bottom".
    @param rect Block rectangle in mm.
    @param t_mm Block thickness in mm.
    @param rc Contact resistance in m2K/W.
    @param board Board slabs (kind, dz, kx, kz) from `program_solid`.
    @return dict of the same read-outs as the program, in K.
    """
    import stack3d
    nx, ny = int(round(40.0 / cell)), int(round(30.0 / cell))
    dx = 0.040 / nx
    dy = 0.030 / ny
    hs = problem.heatsinks[0]
    bm = mask_of(rect, nx, ny)
    h = 10.0
    nb = 4 * max(int(round(t_mm)), 1)                          # finer than the program (it uses one slab per millimetre): the metal is not where the error is
    blk = [{"dz": hs.thickness / nb, "kx": np.where(bm, hs.k, 0.0), "kz": np.where(bm, hs.k, 0.0), "wall": h} for _ in range(nb)]
    pad = {"dz": rc, "kx": 0.0, "kz": np.where(bm, 1.0, 0.0)}
    bs = [{"dz": dz, "kx": kx, "kz": kz} for (_, dz, kx, kz) in board]
    slabs = (blk + [pad] + bs) if face == "top" else (bs + [pad] + blk[::-1])
    cu0 = len(blk) + 1 if face == "top" else 0
    m = mask_of(HEATER, nx, ny)
    r = stack3d.solve(dx, dy, slabs, cu0, m, problem.heaters[0].power, h, h)
    T = r["T"]
    bidx = range(0, nb) if face == "top" else range(len(slabs) - nb, len(slabs))
    cu_idx = [cu0] + [i for i, (kd, *_r) in enumerate(board) if kd == "cu" and i > 0]
    off = (len(blk) + 1) if face == "top" else 0
    cu_slabs = [off + i for i, (kd, *_r) in enumerate(board) if kd == "cu"]
    return {"col_max": float(T[cu_slabs[0]][m].max()), "col_mean_part": float(T[cu_slabs[0]][m].mean()), "layer_mean_top": float(T[cu_slabs[0]].mean()),
            "layer_mean_bottom": float(T[cu_slabs[1]].mean()), "t_max": float(max(np.nanmax(T[cu_slabs[0]]), np.nanmax(T[cu_slabs[1]]))),
            "block_max": float(np.nanmax(T[list(bidx)][:, bm])), "block_mean": float(np.nanmean(T[list(bidx)][:, bm])), "heat_out": r["heat_out"]}


def others(problem, cell):
    """!
    @brief The FVM and the FEM column under the part for the same board (context).
    @param problem Problem.
    @param cell Cell in mm.
    @return dict model -> col_max rise in K.
    """
    from pcbthermal import fem, fvm
    out = {}
    amb = problem.board.ambient
    for key, mod in (("fvm", fvm), ("fem", fem)):
        T = np.asarray(mod.solve_steady(problem, cell).T)
        m = mask_of(HEATER, T.shape[2], T.shape[1])
        out[key] = float(T[0][m].max() - amb)
    return out


def run(args):
    """!
    @brief Run every case on the tree and write the JSON file.
    @param args Parsed arguments (tree, out, cells).
    @return None.
    """
    load_tree(args.tree)
    import pcbthermal
    rows = []
    for cell in [float(c) for c in args.cells.split(",")]:
        for case, (face, rect, t_mm) in CASES.items():
            for rc in RCS:
                p = make_problem(case, rc)
                t0 = time.perf_counter()
                sol, board = program_solid(p, cell, face, rect, t_mm)
                ref = reference(p, cell, face, rect, t_mm, rc, board)
                rows.append({"cell": cell, "case": case, "rc": rc, "solid": sol, "ref": ref, "others": others(p, cell), "seconds": time.perf_counter() - t0})
                print(f"cell {cell} {case} rc {rc:g}: solid col_max {sol['col_max']:.4f} ref {ref['col_max']:.4f}", flush=True)
    Path(args.out).write_text(json.dumps({"tree": str(Path(args.tree).resolve()), "version": pcbthermal.__version__, "rows": rows}, indent=1))


def compare(args):
    """!
    @brief Print the Markdown tables of two runs (before, after).
    @param args Parsed arguments (before, after: JSON files).
    @return None.
    """
    a = json.loads(Path(args.before).read_text())["rows"]
    b = json.loads(Path(args.after).read_text())["rows"]
    keys = ("col_max", "col_mean_part", "layer_mean_top", "layer_mean_bottom", "t_max", "block_max", "block_mean")
    print("| cell | case | rc | read-out | independent | solid before | solid after | before - ref (%) | after - ref (%) | after - before (K) | FVM | FEM |")
    print("| --: | :-- | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for ra, rb in zip(a, b):
        for k in keys:
            ref, sa, sb = ra["ref"][k], ra["solid"][k], rb["solid"][k]
            extra = f"{ra['others']['fvm']:.3f} | {ra['others']['fem']:.3f}" if k == "col_max" else " | "
            print(f"| {ra['cell']:g} | {ra['case']} | {ra['rc']:g} | {k} | {ref:.4f} | {sa:.4f} | {sb:.4f} | {100 * (sa / ref - 1):+.3f} | {100 * (sb / ref - 1):+.3f} | {sb - sa:+.4f} | {extra} |")


def main():
    """!
    @brief Command line of the study.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tree", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--cells", default="2,1")
    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")
    args = ap.parse_args()
    run(args) if args.cmd == "run" else compare(args)


if __name__ == "__main__":
    main()
