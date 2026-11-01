#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_3d_barrels.py
@brief Study 9: the zone model against a 3D conduction solver with the barrels drawn, on three small boards (dense array, sparse array, array off the centre of a long footprint), copper-filled and open.
@details The references of studies 1 to 4 are layered (one node per copper layer and cell), so they can show the error of the lumping and not that of the layered idealisation. Here the same boards (16 mm, four
         35 um planes, FR-4 0.3 W/mK, h_top 10 and h_bottom 200 W/m2K, insulated edges) are solved by the independent 3D solver `layered3d` (a test helper of the program, imports nothing of the program) with the barrels
         drawn as the area share of the copper ring and of the fill in the gap cells (`resolved_boards.board_3d`: the planes are whole, as in the program), at cell 1/8 mm and, for the two centred boards (a quadrant,
         symmetry), at 1/16 mm too; the layer parameters come from the program's own no-via network. The table gives, for every board: the via effect E and the hottest rise of the 3D solver, of the layered fine-grid
         solver (1/16 mm), of the program (`P245`), of the zones (`Z_none`) and of the program's FVM at 0.25 mm, and the errors against the 3D solver in percent of E and of the hottest rise.
         Success criterion (fixed before running): the zones are within 15 % of E of the 3D solver on the two centred boards and within 25 % on the off-centre one; the hottest rise of the zones within 7 % of the 3D one
         on all six; the zones are better than the program on at least five of the six on the hottest rise; and the layered reference is within 10 % of the 3D one in E (if it is not, the 3 percentages of studies 1 to 4
         are errors against a layered reference that the 3D check does not support, and they are reported so).
         Not verified: a 30 mm board (a 3D solve at 1/16 mm of 480 x 480 cells is above the 3 GB budget; the boards here are 16 mm), irregular groups, a block, a real barrel with plating thickness (the barrel is the area share
         of a ring of the program's plating).
Usage: python research/lumped-zones-adoption/scripts/study_3d_barrels.py [--fine]   (from the repository root, with the program's .venv; --fine adds the 1/16 mm quadrant solves, about 3 GB: ONE process)
"""

import argparse
import contextlib
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import resolved_boards as rb                                                 # noqa: E402

BASE = dict(layers=4, side=16.0, power=3.0, dia=0.3)
BOARDS = [("dense 5x5 @ 1.2 under 8 mm", dict(n=5, pitch=1.2, src=8.0), True),
          ("sparse 3x3 @ 3.0 under 10 mm", dict(n=3, pitch=3.0, src=10.0), True),
          ("5x5 @ 1.2 off centre 1.5 mm under 10 x 6 mm", dict(n=5, pitch=1.2, src=10.0, offset=(1.5, 0.0), src_wh=(10.0, 6.0)), False)]


def e_3d(problem, dx_mm, centred, n_sub=2):
    """!
    @brief Via effect and hottest rise of the 3D solver with the barrels drawn.
    @param problem The Problem.
    @param dx_mm Cell in mm.
    @param centred True: the board is symmetric about both centre lines (a quadrant is solved); False: the whole board.
    @param n_sub Sub-slabs per dielectric gap.
    @return tuple (E, t_with, t_without) in K.
    """
    par = pc.layer_parameters(problem)
    h = problem.heaters[0]
    xs = [q[0] for q in h.polygon]
    ys = [q[1] for q in h.polygon]
    dx = dx_mm * 1e-3
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])]
    if centred:
        half = par["width"] / 2
        n = int(round(half / dx))
        sh_x, sh_y = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
        quad = [(x, y, k) for x, y, k in vias if x <= half + 1e-9 and y <= half + 1e-9]
        rect = (half - sh_x, half - sh_y, half, half)
        t_with = rb.board_3d(par, dx, quad, n, rect, h.power / 4, n_sub)
        t_without = rb.board_3d(par, dx, [], n, rect, h.power / 4, n_sub)
    else:
        rect = (min(xs), min(ys), max(xs), max(ys))
        t_with = rb.full_board_3d(par, dx, vias, h.power, rect, n_sub)
        t_without = rb.full_board_3d(par, dx, [], h.power, rect, n_sub)
    return t_without - t_with, t_with, t_without


def main():
    """!
    @brief Run the three boards, copper-filled and open, and print the table and the verdicts.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--fine", action="store_true", help="also the 1/16 mm quadrant solves of the two centred boards")
    args = ap.parse_args()
    pc.load_libraries()
    rows = []
    print("| board | fill | 3D E K (1/8) | 3D E K (1/16) | layered E | P245 E | Z_none E | FVM 0.25 mm E | 3D rise K | layered / P245 / Z_none / FVM rise K |\n| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :-- |")
    for label, spec, centred in BOARDS:
        for fill in (385.0, 0.0):
            s = {**BASE, **spec, "fill": fill}
            p = zref.refs.make_problem(s)
            t0 = time.time()
            e8, tw8, tn8 = e_3d(p, 0.125, centred)
            e16 = e_3d(p, 1.0 / 16, centred)[0] if (args.fine and centred) else float("nan")
            ref = zref.refs.reference(s, dx_mm=1.0 / 16)
            q0 = hz.no_vias(p)
            e_p = zref.lumped_E(s, "P245", 0.5)
            e_z = zref.lumped_E(s, "Z_none", 0.5)
            t_p, t_z = zref.lumped_tmax(p, "P245", 0.5), zref.lumped_tmax(p, "Z_none", 0.5)
            e_f = pc.max_rise(q0, "fvm", 0.25) - pc.max_rise(p, "fvm", 0.25)
            t_f = pc.max_rise(p, "fvm", 0.25)
            rows.append(dict(label=label, fill=fill, e3=e8, e3_fine=e16, t3=tw8, e_layered=ref["E"], t_layered=ref["t_with"], e_p=e_p, e_z=e_z, e_f=e_f, t_p=t_p, t_z=t_z, t_f=t_f, seconds=time.time() - t0))
            print(f"| {label} | {'Cu' if fill else 'open'} | {e8:.3f} | {e16:.3f} | {ref['E']:.3f} | {e_p:.3f} | {e_z:.3f} | {e_f:.3f} | {tw8:.2f} | {ref['t_with']:.2f} / {t_p:.2f} / {t_z:.2f} / {t_f:.2f} |", flush=True)
    print("\nErrors against the 3D solver (1/8 mm), percent of E and percent of the hottest rise (positive: the model is cooler / hotter than the 3D solver for E / rise)\n")
    print("| board | fill | layered E | P245 E | Z_none E | FVM E | layered rise | P245 rise | Z_none rise | FVM rise |\n| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for r in rows:
        eE = lambda x: 100.0 * (x / r["e3"] - 1.0)
        eT = lambda x: 100.0 * (x / r["t3"] - 1.0)
        r["err"] = dict(e_layered=eE(r["e_layered"]), e_p=eE(r["e_p"]), e_z=eE(r["e_z"]), e_f=eE(r["e_f"]), t_layered=eT(r["t_layered"]), t_p=eT(r["t_p"]), t_z=eT(r["t_z"]), t_f=eT(r["t_f"]))
        e = r["err"]
        print(f"| {r['label']} | {'Cu' if r['fill'] else 'open'} | {e['e_layered']:+.1f} | {e['e_p']:+.1f} | {e['e_z']:+.1f} | {e['e_f']:+.1f} | {e['t_layered']:+.1f} | {e['t_p']:+.1f} | {e['t_z']:+.1f} | {e['t_f']:+.1f} |")
    better = sum(abs(r["err"]["t_z"]) < abs(r["err"]["t_p"]) for r in rows)
    print(f"\nzones nearer the 3D hottest rise than the program on {better} of {len(rows)} boards; largest |error of the hottest rise| zones {max(abs(r['err']['t_z']) for r in rows):.1f} %, program {max(abs(r['err']['t_p']) for r in rows):.1f} %")
    print("written", zref.save_json("barrels_3d.json", rows))


if __name__ == "__main__":
    main()
