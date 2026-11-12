#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_references.py
@brief The finite-volume references of the repository and the program (this tree) on the canonical boards of `study_fem_cases.py`.
@details `fv`: `research/strong-edge-laminate/lib/ref3d.py` (cell-centred finite volumes, harmonic means) at 1/4 and 1/8 mm with 8 slabs per gap, plate and resolved-cylinder via, written to
         `out/fv.json`; the stored truths of `research/imported-copper-edge-film/lib/truth_values*.json` are read by `report`.
         `prog`: the program's FVM (and FDM) on the strong-edge board with the simple and the physical stack-up, default and 8 sub-gaps, cells 0.5 and 0.25 mm, and on the 20 mm squares and the
         T outline turned by 0 .. 45 degrees and shifted by 0 and 0.3 of a cell (the ten boards of `study_drawn_film.py`), cells 1 and 0.5 mm, written to `out/prog.json`.
         Run: `.venv/bin/python research/independent-fem-edge/scripts/study_references.py fv|prog`. Under 1.5 GB.
"""

import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(FOLDER, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "research", "strong-edge-laminate", "lib"))
sys.path.insert(2, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
OUT = os.path.join(FOLDER, "out")
logging.disable(logging.WARNING)

H_STRONG = (10.0, 200.0, 1000.0)


def fv():
    """!
    @brief Run the cell-centred finite-volume reference ref3d (8 slabs per gap).
    @return None.
    """
    import ref3d
    res = {}
    os.makedirs(OUT, exist_ok=True)
    for dx in (0.25e-3, 0.125e-3):
        for h in H_STRONG:
            for d in (None, 0.16e-3, 3.0e-3):
                kw = dict(via="none") if d is None else dict(via="cyl", via_dist=d)
                if d is not None and h == 10.0:
                    continue
                r = ref3d.solve(h, 8, dx, **kw)
                key = f"{h}|{d}|{dx}"
                res[key] = r
                print(key, round(r["tmax"], 4), r["balance"], r["n"], flush=True)
                json.dump(res, open(os.path.join(OUT, "fv.json"), "w"))


def prog():
    """!
    @brief Run the program on the boards.
    @return None.
    """
    import numpy as np
    import prog as sprog                                                        # strong-edge-laminate/lib/prog.py
    from pcbthermal.model import Dielectric
    import study_drawn_film as sd
    res = {}
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "prog.json")
    if os.path.exists(path):
        res = json.load(open(path))

    def physical(p):
        """!
        @brief Advanced stack-up of three equal gaps (the physical slabs of the reference).
        @param p Problem.
        @return Problem.
        """
        p.board.dielectrics = [Dielectric(thickness=sprog.GAP_MM * 1e-3, k_through=0.3, k_inplane=0.3) for _ in range(3)]
        return p
    for h in H_STRONG:
        for d in (None, 0.16, 3.0):
            if d is not None and h == 10.0:
                continue
            for cell in (0.5, 0.25):
                for n in (None, 8):
                    for phys in (False, True):
                        for model in ("fvm", "fdm"):
                            key = f"strong|{h}|{d}|{cell}|{n}|{phys}|{model}"
                            if key in res or (model == "fdm" and (d is not None or n is not None)):
                                continue
                            p = sprog.board(h, d)
                            res[key] = sprog.run(physical(p) if phys else p, cell, n, model=model)
                            print(key, round(res[key], 4), flush=True)
                            json.dump(res, open(path, "w"))
    for name, hs in (("sq_in", (10.0, 200.0, 1000.0)), ("sq_wall", (200.0, 1000.0)), ("T_wall", (200.0,))):
        spec = sd.CASES[name]
        for h in hs:
            for cell in (1.0, 0.5):
                key = f"{name}|{h}|{cell}"
                if key in res:
                    continue
                vals = []
                for sh in sd.SHIFTS:
                    for ang in sd.ANGLES:
                        vals.append(sd.heater_rise(sd.build(spec, h, ang, sh * cell), cell)[0])
                res[key] = vals
                tr = sd.truth_of(name, h)
                e = 100 * (np.array(vals) / tr - 1)
                print(key, "mean %+.2f worst %.2f" % (e.mean(), np.abs(e).max()), flush=True)
                json.dump(res, open(path, "w"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fv":
        fv()
    elif cmd == "prog":
        prog()
    else:
        raise SystemExit(__doc__)
