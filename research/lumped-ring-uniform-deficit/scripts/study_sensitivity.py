#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sensitivity.py
@brief Which term of the Lumped ring network causes the deficit on a uniform sheet: one thing at a time on a 100 x 80 mm board, and the conditions (layers, fill, film, edge, position) with and without the proposed first ring.
@details Table 1: a centred source of 1, 3 and 10 mm on a two-layer full-copper 100 x 80 mm board; the Lumped as the program runs it, then with one change each: first ring 1.5 cells wide, 6, 20 and
         40 rings, ring merge off or at two cells, vertical-loss factors of the link set to 1, footprint peak off, cell 1 mm. Error = Lumped / FVM - 1 on the hottest node, the FVM at 0.25 mm
         (1 and 3 mm sources) or 0.5 mm (cached by lib/runner.py). Table 2: the conditions the maintainer asked for, program against the two candidates: 1, 2 and 4 layers, fill 1 and 0.6, h on both faces
         10/15, 50 and 200 W/m2K, with and without edge convection, source of 2, 6 and 10 mm, board 30 x 20, 60 x 40 and 100 x 80 mm. Output: tables on the screen and out/sensitivity.json.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_sensitivity.py (about 10 minutes, peak under 1 GB).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import runner as R  # noqa: E402
import simple as S  # noqa: E402

# name -> (configure arguments, rings, cell)
ONE_AT_A_TIME = {
    "program": (("strip", 0.04, 1.5, None), 10, 0.5),
    "first ring 1.5 cells": (("strip", 0.0, 1.5, None), 10, 0.5),
    "first ring cap 1 a": (("strip", 0.04, 1.5, 1.0), 10, 0.5),
    "6 rings": (("strip", 0.04, 1.5, None), 6, 0.5),
    "20 rings": (("strip", 0.04, 1.5, None), 20, 0.5),
    "40 rings": (("strip", 0.04, 1.5, None), 40, 0.5),
    "no ring merge": (("strip", 0.04, 1.5, None, True, True, 0.0), 10, 0.5),
    "merge at 2 cells": (("strip", 0.04, 1.5, None, True, True, 2.0), 10, 0.5),
    "vertical-loss factors = 1": (("strip", 0.04, 1.5, None, False, True), 10, 0.5),
    "footprint peak off": (("strip", 0.04, 1.5, None, True, False), 10, 0.5),
    "cell 1 mm": (("strip", 0.04, 1.5, None), 10, 1.0),
    "log link, first ring 1.5 cells": (("log", 0.0, 1.5, None), 10, 0.5),
}


def err(p, key, side, pos, args, rings, cell, ref_cell):
    """!
    @brief Error of the Lumped hottest node against the (cached) FVM.
    @param p Problem.
    @param key Cache key of the FVM case.
    @param side Source side in mm.
    @param pos Source centre in mm.
    @param args Arguments of lumped_log.configure.
    @param rings Rings.
    @param cell Lumped cell in mm.
    @param ref_cell FVM cell in mm.
    @return float per cent.
    """
    fh = R.fvm_reference(key, p, ref_cell, side, pos)[1]
    R.LL.configure(*args)
    lh = R.readout(p, "lumped", cell, side, pos, lumped_rings=rings)[1]
    return 100.0 * (lh / fh - 1.0), fh


def main():
    """!
    @brief Run both tables.
    @return None.
    """
    out = {"one_at_a_time": [], "conditions": []}
    w, h = 100, 80
    names = list(ONE_AT_A_TIME)
    print("Table 1: Lumped hottest node against the FVM, 100 x 80 mm, two layers full copper, centred source (per cent)\n")
    print("| source (mm) | FVM (K) | " + " | ".join(names) + " |")
    print("| --: | --: | " + " | ".join("--:" for _ in names) + " |")
    for side in (1.0, 3.0, 10.0):
        pos = (w / 2.0, h / 2.0)
        p = S.board(w_mm=w, h_mm=h, layers=2, fill=1.0, side_mm=side, pos=pos)
        key = f"b{w}x{h}|s{side}|L2|f1|h10"
        ref_cell = 0.25 if side <= 3.0 else 0.5
        vals = []
        for n in names:
            a, r, c = ONE_AT_A_TIME[n]
            e, fh = err(p, key, side, pos, a, r, c, ref_cell)
            vals.append(e)
        out["one_at_a_time"].append({"side": side, "fvm": fh, **dict(zip(names, vals))})
        print(f"| {side:g} | {fh:.2f} | " + " | ".join(f"{v:+.1f}" for v in vals) + " |", flush=True)

    print("\nTable 2: conditions, program / cap 1 a / first ring 1.5 cells (per cent of the FVM rise at 0.5 mm; 0.25 mm for sources up to 3 mm on boards up to 100 x 80)\n")
    print("| board | layers | fill | h top/bottom | edge | source | FVM (K) | program | cap 1 a | first 1.5 cells |")
    print("| :-- | --: | --: | :-- | :-- | --: | --: | --: | --: | --: |")
    for (bw, bh) in ((30, 20), (60, 40), (100, 80)):
        for layers, fill, htb, hs in ((2, 1.0, (10.0, 15.0), 10.0), (1, 1.0, (10.0, 15.0), 10.0), (4, 1.0, (10.0, 15.0), 10.0), (2, 0.6, (10.0, 15.0), 10.0),
                                      (2, 1.0, (50.0, 50.0), 10.0), (2, 1.0, (200.0, 200.0), 10.0), (2, 1.0, (10.0, 15.0), None)):
            if (bw, bh) != (100, 80) and (layers, fill, htb, hs) != (2, 1.0, (10.0, 15.0), 10.0):
                continue                                             # the conditions are swept on the big board, the board size on the base case
            for side in (2.0, 6.0, 10.0):
                if side > 0.5 * min(bw, bh):
                    continue
                pos = (bw / 2.0, bh / 2.0)
                p = S.board(w_mm=bw, h_mm=bh, layers=layers, fill=fill, side_mm=side, pos=pos, h_top=htb[0], h_bot=htb[1], h_side=hs)
                key = f"b{bw}x{bh}|s{side}|L{layers}|f{fill}|h{htb[0]}-{htb[1]}|e{hs}"
                ref_cell = 0.25 if (side <= 3.0 and bw * bh <= 8000) else 0.5
                e0, fh = err(p, key, side, pos, ONE_AT_A_TIME["program"][0], 10, 0.5, ref_cell)
                e1, _ = err(p, key, side, pos, ONE_AT_A_TIME["first ring 1.5 cells"][0], 10, 0.5, ref_cell)
                e2, _ = err(p, key, side, pos, ONE_AT_A_TIME["first ring cap 1 a"][0], 10, 0.5, ref_cell)
                out["conditions"].append({"board": [bw, bh], "layers": layers, "fill": fill, "h": htb, "h_side": hs, "side": side, "fvm": fh, "program": e0, "cap 1 a": e2, "first 1.5 cells": e1})
                print(f"| {bw}x{bh} | {layers} | {fill:g} | {htb[0]:g}/{htb[1]:g} | {'none' if hs is None else 'h=%g' % hs} | {side:g} | {fh:.2f} | {e0:+.1f} | {e2:+.1f} | {e1:+.1f} |", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "sensitivity.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
