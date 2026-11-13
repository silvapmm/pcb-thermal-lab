#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_synthetic.py
@brief Questions 3 and 4: signal vias through planes with an antipad on a small synthetic imported board, the program as it is and with the rim read from the masks, against an independent 3D reference.
@details A 10 mm square board, 2 or 4 copper layers, a 3 x 3 mm heater (1 W) over a 4 x 4 array of 0.3 mm vias at 0.7 mm pitch; the layer patterns around the vias are 'solid'
         (plane touching the barrel), 'anti' (pad island radius 0.25 mm, bare to 0.55 mm, plane beyond: a signal via) and 'relief' (four 0.25 mm spokes). The board is given to the program as
         imported copper (masks at 0.05 mm) with the vias as plated holes; the reference is `lib/truth_via.py` (cells 0.1 mm, real copper slabs, laminate in sub-slabs, via blocks), which
         shares nothing with the program. Compared: the heater's hottest rise from the program today (every via in full contact with every layer), with the drill-circle rim test from the masks (the
         program's rule for drawn boards applied to a mask), and with the ray test (copper continuous from the drill circle out to `reach`); also the same board without vias.
         Run (from the repository root): .venv/bin/python research/imported-via-rim/scripts/study_synthetic.py [layers] [cells mm comma list] [reach mm]
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import rimmask                                                  # noqa: E402  (also puts the repository root on the path)
import truth_via                                                # noqa: E402
from pcbthermal import api, copper                              # noqa: E402
from pcbthermal.model import Problem                            # noqa: E402

PITCH = 0.7e-3
CENTRE = 5.1e-3
HEATER = (3.6e-3, 3.6e-3, 6.6e-3, 6.6e-3)
CASES = {2: {"solid": ["solid", "solid"], "anti": ["solid", "anti"], "relief": ["solid", "relief"]},
         4: {"solid": ["solid"] * 4, "anti": ["solid", "anti", "anti", "solid"], "relief": ["solid", "relief", "relief", "solid"], "mixed": ["solid", "anti", "solid", "solid"]}}


def via_centres(nv=4):
    """!
    @brief Centres of the nv x nv via array in m.
    @param nv Vias per side.
    @return list of (x, y).
    """
    o = (np.arange(nv) - (nv - 1) / 2.0) * PITCH
    return [(CENTRE + a, CENTRE + b) for a in o for b in o]


def program_problem(kinds, centres, cell_pix=0.05, vias=True):
    """!
    @brief The same board as imported copper with the vias as plated holes.
    @param kinds Layer patterns.
    @param centres Via centres in m.
    @param cell_pix Pixel in mm.
    @param vias False: no vias.
    @return Problem.
    """
    n = 100
    rasters = []
    for k in kinds:
        m = truth_via.layer_pattern(n, 0.1e-3, centres, k, 0.25e-3, 0.55e-3, 0.25e-3)
        up = np.kron(m, np.ones((2, 2), bool))                          # 0.05 mm pixels
        rasters.append(np.flipud(up).astype(np.uint8) * 255)            # rows from the top edge
    p = Problem.new(10.0, 10.0, layers=len(kinds), thickness_mm=1.6, copper_um=35.0, name="synthetic")
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", 10.0, 10.0, None
    p.imported = copper.imported_from_rasters(rasters, cell_pix, names=[f"L{i + 1}" for i in range(len(kinds))])
    if vias:
        for (x, y) in centres:
            p.add_via(x * 1e3, y * 1e3, diameter=0.3)
    p.add_heater(1, 1.0, rect=tuple(v * 1e3 for v in HEATER))
    return p


def program_rise(p, cell, model="fvm"):
    """!
    @brief Hottest rise of the program.
    @param p Problem.
    @param cell Cell in mm.
    @param model Model key.
    @return float K.
    """
    r = api.simulate(p, api.SolverOptions(models=(model,), cell_mm=cell)).results[model]
    return r.t_max - p.board.ambient


def main(argv):
    """!
    @brief Run the cases.
    @param argv layers, cells, reach.
    @return int.
    """
    layers = int(argv[1]) if len(argv) > 1 else 4
    cells = [float(c) for c in (argv[2] if len(argv) > 2 else "1.0,0.5,0.25").split(",")]
    reach = float(argv[3]) if len(argv) > 3 else 0.5
    centres = via_centres()
    out = {}
    for name, kinds in CASES[layers].items():
        t = truth_via.solve(kinds, centres, HEATER, nlam=6 if layers > 2 else 12)
        t0 = truth_via.solve(kinds, centres, HEATER, nlam=6 if layers > 2 else 12, with_vias=False)
        row = {"truth_max": t["max"], "truth_mean": t["mean"], "truth_novia": t0["max"], "balance": t["balance"]}
        print("%dL %-7s truth: max %.3f mean %.3f K, no vias %.3f K, balance %.1e" % (layers, name, t["max"], t["mean"], t0["max"], t["balance"]), flush=True)
        # no vias at all in the program
        pn = program_problem(kinds, centres, vias=False)
        for cell in cells:
            res = {}
            p = program_problem(kinds, centres)
            for label, inst in (("today", None), ("drill rim", 0.0), ("ray %.1f" % reach, reach)):
                if inst is None:
                    rimmask.uninstall()
                else:
                    rimmask.install(0.5, inst)
                res[label] = program_rise(p, cell)
            rimmask.uninstall()
            res["no vias"] = program_rise(pn, cell)
            row[str(cell)] = res
            print("   cell %.2f  " % cell + "  ".join("%s %.3f (%+.1f %%)" % (k, v, 100 * (v / t["max"] - 1)) for k, v in res.items()), flush=True)
        out[name] = row
    (HERE.parent / "out").mkdir(exist_ok=True)
    json.dump(out, open(HERE.parent / "out" / f"synthetic_{layers}L.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
