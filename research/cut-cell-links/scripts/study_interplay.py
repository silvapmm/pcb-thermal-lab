#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_interplay.py
@brief Cut cells together with the vias, the laminate nodes of patterned copper and the transient, and the frozen-number boards whose outline cuts cells (README 5 and 6).
@details vias     the 20 mm square with a 3 x 3 via array under the part 7 mm towards the edge (vias 1.5 to 3.5 mm from it), turned and shifted as in the sweep, error of the peak
                  against the frame reference (the array turned with the part), h_side 200, cells 1 and 0.5;
         pattern  the top copper held 1.2 mm inside the outline (the laminate rule puts sub-gap nodes in the cut cells), the same positions;
         time     the time to 63 % of the steady rise of the turned square from the implicit transient of the program on each scheme's matrix;
         harness  the boards of the frozen-number harness whose outline cuts cells (`round_outline`, `t_outline`, `example_cut_to_T`, `part_across_outline`) at 2, 1 and 0.5 mm:
                  hottest temperature of every scheme and its shift from the program (the program already has the exact cover in this tree).
Usage: .venv/bin/python research/cut-cell-links/scripts/study_interplay.py [vias|pattern|time|harness|all]   (from the repository root; about 20 minutes, below 1.5 GB)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, LIB)
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
OUT = os.path.join(os.path.dirname(HERE), "out")

import cutlinks as cl         # noqa: E402
import boards as bd           # noqa: E402

ANGLES = (0, 10, 20, 30, 45)


def sweep(label, base, cells=(1.0, 0.5)):
    """!
    @brief Errors of every scheme against the frame reference over a few turns and shifts of a board option set.
    @param label Name of the study.
    @param base Options of `edge_board` / `frame_board` common to every position.
    @param cells Cells in mm.
    @return dict of the numbers.
    """
    out = {}
    for cell in cells:
        pos = [dict(angle=float(a)) for a in ANGLES] + [dict(sx=k / 8 * cell, sy=k / 8 * cell) for k in (2, 4, 6)]
        errs = {s: [] for s in cl.SCHEMES}
        for pk in pos:
            kw = dict(base, pc=cell / 2, **pk)
            ref = bd.frame_reference(lambda p, c: cl.tmax(p, c), kw)[0]
            for s in cl.SCHEMES:
                errs[s].append(cl.tmax(bd.edge_board(**kw), cell, s) - ref)
        out[str(cell)] = errs
        print(f"| {label} | {cell:g} | " + " | ".join(f"{np.mean(errs[s]):+.2f} / {np.ptp(errs[s]):.2f}" for s in cl.SCHEMES) + " |", flush=True)
    return out


def study_vias():
    """!
    @brief Via array near the cut edge.
    @return dict.
    """
    print("\n### vias near the cut edge: bias / spread of the error of the peak over 8 positions (K)\n")
    print("| case | cell | " + " | ".join(cl.SCHEMES) + " |\n| :-- | --: | " + " | ".join("--:" for _ in cl.SCHEMES) + " |")
    out = {}
    for hs in (10.0, 200.0):
        out[f"h{hs:g}"] = sweep(f"vias, part at 7 mm, h_side {hs:g}", dict(h_side=hs, off=7.0, vias=True, shape="square"))
    return out


def study_pattern():
    """!
    @brief Patterned copper (top copper inside the outline).
    @return dict.
    """
    print("\n### copper held 1.2 mm inside the outline: bias / spread of the error of the peak over 8 positions (K)\n")
    print("| case | cell | " + " | ".join(cl.SCHEMES) + " |\n| :-- | --: | " + " | ".join("--:" for _ in cl.SCHEMES) + " |")
    out = {}
    for hs in (10.0, 200.0):
        out[f"h{hs:g}"] = sweep(f"patterned, h_side {hs:g}", dict(h_side=hs, off=0.0, pattern=True, shape="square"))
    return out


def tau63(problem, cell, scheme, t_end=120.0):
    """!
    @brief Time to 63 % of the steady rise of the hottest point from the program's implicit transient on a scheme's network.
    @param problem Problem.
    @param cell Cell in mm.
    @param scheme One of the schemes.
    @param t_end Final time in seconds.
    @return Seconds (nan if not reached).
    """
    from pcbthermal import fvm
    if scheme == "current":                                     # the program of the tree (audit 2.7.0: `program` is the network before 2.6.0, lib/cutlinks.py)
        return float(fvm.solve_transient(problem, t_end, cell_mm=cell, n_out=60).time_constant())
    with cl.using(scheme):
        return float(fvm.solve_transient(problem, t_end, cell_mm=cell, n_out=60).time_constant())


def study_time():
    """!
    @brief Time to 63 % of the turned square for every scheme: spread over the turns and error against the frame problem at a fine cell.
    @return dict.
    """
    out = {}
    print("\n### time to 63 % (s) of the hottest point, 20 mm square turned 0..45 degrees, h_side 200, cell 1 mm; frame problem at 0.25 mm\n")
    print("| scheme | mean | spread over the turns | mean - frame (s) |\n| :-- | --: | --: | --: |")
    ref = []
    for a in ANGLES:
        ref.append(tau63(bd.frame_board(angle=float(a), h_side=200.0, pc=0.5), 0.25, "program"))
    r = float(np.mean(ref))
    out["frame"] = ref
    for s in cl.SCHEMES:
        v = [tau63(bd.edge_board(angle=float(a), h_side=200.0, pc=0.5), 1.0, s) for a in ANGLES]
        out[s] = v
        print(f"| {s} | {np.mean(v):.3f} | {np.ptp(v):.3f} | {np.mean(v) - r:+.3f} |", flush=True)
    return out


def study_harness():
    """!
    @brief The frozen-number boards with an outline: hottest temperature of every scheme and the shift from the program.
    @return dict.
    """
    import regress_boards as rb
    out = {}
    print("\n### harness boards with an outline: hottest temperature (degC) and the shift from the program (K, per cent of the rise)\n")
    print("| board | cell | program | " + " | ".join(f"{s}" for s in cl.SCHEMES[1:]) + " |\n| :-- | --: | --: | " + " | ".join("--:" for _ in cl.SCHEMES[1:]) + " |")
    for name in ("round_outline", "t_outline", "example_cut_to_T", "part_across_outline"):
        for cell in (2.0, 1.0, 0.5):
            p = rb.build(name)
            a = cl.tmax(p, cell, "program")
            rise = a - p.board.ambient
            row = []
            rec = {"program": a}
            for s in cl.SCHEMES[1:]:
                b = cl.tmax(rb.build(name), cell, s)
                rec[s] = b
                row.append(f"{b - a:+.3f} ({100 * (b - a) / rise:+.2f} %)")
            out[f"{name}|{cell:g}"] = rec
            print(f"| {name} | {cell:g} | {a:.3f} | " + " | ".join(row) + " |", flush=True)
    return out


def main():
    """!
    @brief Run the studies named on the command line and save the numbers.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("vias", study_vias), ("pattern", study_pattern), ("time", study_time), ("harness", study_harness)):
        if which in (name, "all"):
            res = fn()
            with open(os.path.join(OUT, f"interplay_{name}.json"), "w") as f:
                json.dump(res, f)


if __name__ == "__main__":
    main()
