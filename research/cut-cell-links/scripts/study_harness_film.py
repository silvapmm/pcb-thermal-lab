#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_film.py
@brief What the boundary film would move in the 17 boards of the frozen-number harness (also the rectangles), and how the film behaves at a stiff edge (README 6 and 7).
@details harness  every board of `tests/regression/regress_boards.py` at 2, 1 and 0.5 mm: hottest temperature of the program (which already has the exact cover) and of
                  `aperture+film` with the film on the rectangles too (`film_rect=True`); boards with a metal block or imported copper are refused by the prototype and listed;
         floor    the 20 mm square turned 0 to 45 degrees at h_side 2e3, 1e4 and 1e5 W/m2K (the limit of `Board.validate`), cell 1 and 0.5 mm: spread of the peak over the turns
                  for `program`, `aperture` and `aperture+film` with the floor of the film denominator at 0.25 (the prototype), 0.1 and 0.5; the number of node layers cells
                  where the floor is active; the frame reference at that h_side.
Usage: .venv/bin/python research/cut-cell-links/scripts/study_harness_film.py [harness|floor|all]   (from the repository root; about 10 minutes, below 1.5 GB)
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


def study_harness():
    """!
    @brief Shift of the hottest temperature by the film on every harness board.
    @return dict.
    """
    import regress_boards as rb
    out = {}
    print("\n### harness: hottest temperature (degC) of the program and the shift by aperture+film with the film on the rectangles too (K, per cent of the rise)\n")
    print("| board | outline | cell | program | shift (K) | % of the rise |\n| :-- | :-: | --: | --: | --: | --: |")
    for name in rb.board_names():
        for cell in (2.0, 1.0, 0.5):
            p = rb.build(name, os.path.join(ROOT, "examples"))
            try:
                a = cl.tmax(p, cell, "program")
            except Exception as e:                      # a board the program itself cannot run at this cell
                print(f"| {name} | | {cell:g} | not run: {e} | | |")
                continue
            try:
                b = cl.tmax(rb.build(name, os.path.join(ROOT, "examples")), cell, "aperture+film", film_rect=True)
            except ValueError as e:
                print(f"| {name} | | {cell:g} | {a:.3f} | refused: {e} | |", flush=True)
                continue
            rise = a - p.board.ambient
            out[f"{name}|{cell:g}"] = [a, b]
            print(f"| {name} | {'yes' if p.board.has_outline() else 'no'} | {cell:g} | {a:.3f} | {b - a:+.3f} | {100 * (b - a) / rise:+.2f} |", flush=True)
    return out


def study_floor():
    """!
    @brief Stiff edges: spread over the turns and the use of the floor of the film denominator.
    @return dict.
    """
    out = {}
    print("\n### floor: spread of the peak over the turns 0..45 (K) of the 20 mm square, part 3.5 mm off centre\n")
    print("| h_side | cell | frame ref spread (K, of the reference itself) | program | aperture | film floor 0.5 | film floor 0.25 | film floor 0.1 | cells at the floor (0.25) |")
    print("| --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for hs in (2000.0, 1.0e4, 1.0e5):
        for cell in (1.0, 0.5):
            res = {k: [] for k in ("program", "aperture", "f0.5", "f0.25", "f0.1")}
            ref = []
            for a in range(0, 50, 15):
                kw = dict(angle=float(a), h_side=hs, off=3.5, pc=cell / 2)
                ref.append(bd.frame_reference(lambda p, c: cl.tmax(p, c), kw)[0])
                res["program"].append(cl.tmax(bd.edge_board(**kw), cell, "program") - ref[-1])
                res["aperture"].append(cl.tmax(bd.edge_board(**kw), cell, "aperture") - ref[-1])
                for fl in (0.5, 0.25, 0.1):
                    res[f"f{fl:g}"].append(cl.tmax(bd.edge_board(**kw), cell, "aperture+film", film_floor=fl) - ref[-1])
            p = bd.edge_board(angle=20.0, h_side=hs, off=3.5, pc=cell / 2)
            p.validate()
            with cl.using("aperture+film"):
                n = int(round(p.board.width * 1000 / cell))
                net = cl.CutLinkNetwork(p, n, n)
            at_floor = int((net.film_factor <= 0.25 + 1e-12).sum())
            out[f"{hs:g}|{cell:g}"] = {k: [float(x) for x in v] for k, v in res.items()}
            print(f"| {hs:g} | {cell:g} | {np.ptp(ref):.2f} | " + " | ".join(f"{np.ptp(res[k]):.2f}" for k in ("program", "aperture", "f0.5", "f0.25", "f0.1")) + f" | {at_floor} |", flush=True)
    return out


def main():
    """!
    @brief Run the studies named on the command line and save the numbers.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("harness", study_harness), ("floor", study_floor)):
        if which in (name, "all"):
            with open(os.path.join(OUT, f"harness_film_{name}.json"), "w") as f:
                json.dump(fn(), f)


if __name__ == "__main__":
    main()
