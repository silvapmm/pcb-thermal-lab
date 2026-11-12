#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_slabs.py
@brief Review: is the 'converged residual' of the plate and of the via effect at a strongly cooled edge the simple stack-up's equal slabs (each of the four layer nodes stands for 0.4 mm)?
@details The board of `lib/prog.py` is built with the simple stack-up (`Problem.new` with a thickness and no dielectrics), where `Board.slab_thicknesses` gives every layer node T / L =
         0.4 mm, while the gaps are the real 0.487 mm: the outer copper nodes hold 0.365 mm of laminate (physically 0.243 mm) and carry the edge film of it at the copper temperature.
         The same board with the advanced stack-up of three equal gaps (FR-4 0.3 W/mK both ways, the board of `lib/ref3d.py`) has the physical slabs 0.278 / 0.522 / 0.522 / 0.278 mm.
         Runs the FVM (and the FDM and the 3D solid as checks with other discretisations) both ways against the stored 3D reference (`out/ref_cache.jsonl`, 1/8 mm, 8 slabs, resolved
         copper cylinder; 1/16 mm where stored) and writes `out/review_slabs.json` (read by `make_figures.py` for figure 2). About 1 minute, under 1 GB.
         Run: `.venv/bin/python research/strong-edge-laminate/scripts/study_review_slabs.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
import prog                                                         # noqa: E402
from pcbthermal.model import Dielectric                             # noqa: E402

REF = {}
for line in open(os.path.join(FOLDER, "out", "ref_cache.jsonl")):
    rec = json.loads(line)
    REF[rec["key"]] = rec["tmax"]


def ref(h, d=None, inset=0.0, dx=8):
    """!
    @brief Stored hottest rise of the 3D reference (8 slabs per gap, resolved copper cylinder for the via).
    @param h Edge coefficient in W/m2K.
    @param d Via distance from the wall in mm (None: no via).
    @param inset Copper inset in mm.
    @param dx Plan cells per mm (8 or 16).
    @return float rise in K.
    """
    return REF[f"h{h}|n8|dx{dx}|{'none' if d is None else 'cyl'}|d{0 if d is None else d}|i{'0' if inset == 0 else inset}"]


def physical(problem):
    """!
    @brief Give the board the advanced stack-up of three equal gaps, so that every layer node holds its copper and half of each adjacent gap (the board of the 3D reference).
    @param problem Problem built by prog.board (simple stack-up).
    @return The same Problem, changed in place.
    """
    problem.board.dielectrics = [Dielectric(thickness=prog.GAP_MM * 1e-3, k_through=0.3, k_inplane=0.3) for _ in range(3)]
    return problem


def run(h, d, cell, n, phys, inset=0.0, model="fvm"):
    """!
    @brief Hottest rise of one program run.
    @param h Edge coefficient in W/m2K.
    @param d Via distance from the wall in mm (None: no via).
    @param cell Cell in mm.
    @param n Sub-gaps (None: the default, 2 on this board).
    @param phys True: physical slabs (advanced stack-up); False: the simple stack-up.
    @param inset Copper inset in mm.
    @param model Model key.
    @return float rise in K.
    """
    p = prog.board(h, d, inset_mm=inset)
    return prog.run(physical(p) if phys else p, cell, n, model=model)


def main():
    """!
    @brief Print and store the plate and via-effect errors for both stack-ups.
    @return None.
    """
    out = {"plate": {}, "via": {}, "checks": {}}
    print("plate, error % against 3D 1/8 mm (simple default / physical default / simple 8 / physical 8)")
    for h in (10, 200, 500, 1000, 2000):
        for cell in (0.5, 0.25, 0.125):
            row = [100 * (run(h, None, cell, n, ph) / ref(h) - 1) for n in (None, 8) for ph in (False, True)]
            out["plate"][f"{h}|{cell}"] = row
            print(f"  h {h:5d} cell {cell}: " + " / ".join(f"{v:+.1f}" for v in row), flush=True)
    print("via effect E, error % against the 3D cylinder 1/8 mm (same columns)")
    for h, ds in ((10, (0.16,)), (200, (0.16, 0.5, 1, 3)), (500, (0.16,)), (1000, (0.16, 0.5, 1, 3)), (2000, (0.16,))):
        for d in ds:
            e_ref = ref(h) - ref(h, d)
            for cell in (0.5, 0.25):
                row = []
                for n in (None, 8):
                    for ph in (False, True):
                        row.append(100 * ((run(h, None, cell, n, ph) - run(h, d, cell, n, ph)) / e_ref - 1))
                out["via"][f"{h}|{d}|{cell}"] = row
                print(f"  h {h:5d} d {d} cell {cell} (E 3D {e_ref:.3f} K): " + " / ".join(f"{v:+.1f}" for v in row), flush=True)
    print("checks with other discretisations, h 1000, no via, against 3D 1/16 mm (24.538 K)")
    r16 = ref(1000, dx=16)
    for cell in (0.25, 0.125):
        for model, n in (("fdm", None), ("fdm", 8), ("solid3d", None)):
            a, b = (run(1000, None, cell, n, ph, model=model) for ph in (False, True))
            out["checks"][f"{model}|{n}|{cell}"] = [100 * (a / r16 - 1), 100 * (b / r16 - 1)]
            print(f"  {model:7s} n {n} cell {cell}: simple {100 * (a / r16 - 1):+.1f} %  physical {100 * (b / r16 - 1):+.1f} %", flush=True)
    for cell in (0.25, 0.125):
        a = run(1000, None, cell, 8, True)
        out["checks"][f"fvm|8|{cell}|vs16"] = 100 * (a / r16 - 1)
        print(f"  fvm     n 8 cell {cell}: physical {100 * (a / r16 - 1):+.1f} % against 1/16 mm", flush=True)
    with open(os.path.join(FOLDER, "out", "review_slabs.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
