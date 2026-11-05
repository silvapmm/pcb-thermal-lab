#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_multigroup.py
@brief Study 11: several via groups under one footprint (two clusters, clusters of different pitch, a cluster and a lone row), the case the design cuts into ONE core C and the rest A, against the fine-grid layered solver.
@details The zone model has one core per footprint: the union of the cells within 0.7071 nearest-neighbour distances of the vias of every group with two or more vias in the footprint. Two clusters far apart
         make a core that is mostly bare laminate between them, so the lateral link A-C is a poor description. The review of the earlier folders left this untested (README 8.9). Boards (30 mm, 4 planes of 35 um, a
         20 mm source, 3 W, `refs.make_problem` spec with `clusters`): (a) two 3 x 3 clusters at 1.0 mm pitch 5 mm either side of the centre (x = -5, +5); (b) two 3 x 3 clusters at 1.0 mm, 8 mm apart in x
         and in y (four clusters of 3 x 3 at the corners of a square of side 8 mm, `clusters` with four entries); (c) a 4 x 4 cluster at 1.0 mm and a 3 x 3 cluster at 2.0 mm, 5 mm apart; (d) one 5 x 5 cluster
         at 1.2 mm for scale. Copper-filled and open. Variants `P245`, `Z_none`, `Z_cap`; errors of E against the reference and of the hottest rise. Success criterion (fixed before running): the zones within
         20 % of E and within 7 % of the hottest rise on every board of (a) to (c), and not worse than the program on the hottest rise; where they are not, the board is a limit to be warned about (a group
         count above one in a footprint).
Usage: python research/lumped-zones-adoption/scripts/study_multigroup.py   (from the repository root, with the program's .venv; references at 1/8 mm, about 1 GB, one process)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402

BASE = dict(layers=4, side=30.0, src=20.0, power=3.0, dia=0.3, n=3, pitch=1.0)
BOARDS = [("(a) two 3x3 @ 1.0, 10 mm apart", [(-5.0, 0.0, 3, 1.0), (5.0, 0.0, 3, 1.0)]),
          ("(b) four 3x3 @ 1.0 at the corners of an 8 mm square", [(-4.0, -4.0, 3, 1.0), (4.0, -4.0, 3, 1.0), (-4.0, 4.0, 3, 1.0), (4.0, 4.0, 3, 1.0)]),
          ("(c) 4x4 @ 1.0 and 3x3 @ 2.0, 5 mm apart", [(-3.0, 0.0, 4, 1.0), (3.0, 0.0, 3, 2.0)]),
          ("(d) one 5x5 @ 1.2 (for scale)", [(0.0, 0.0, 5, 1.2)])]


def main():
    """!
    @brief Run the boards and print the table.
    @return None.
    """
    zref.pc.load_libraries()
    rows = []
    print("| board | fill | ref E K | ref rise K | P245 E % | Z_none E % | Z_cap E % | P245 rise % | Z_none rise % | Z_cap rise % | core share | warnings |\n| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | :-- |")
    for label, clusters in BOARDS:
        for fill in (385.0, 0.0):
            spec = {**BASE, "fill": fill, "clusters": clusters}
            ref = zref.refs.reference(spec)
            p = zref.refs.make_problem(spec)
            e = {n: zref.lumped_E(spec, n, 0.5) for n in ("P245", "Z_none", "Z_cap")}
            t = {n: zref.lumped_tmax(p, n, 0.5) for n in ("P245", "Z_none", "Z_cap")}
            with zref.VARIANTS["Z_none"]():
                zref.pc.max_rise(p, "lumped", 0.5)
                warn = list(zl.LAST.get("warnings", []))
                core = zl.LAST.get("core")
                share = float(core.sum()) / max(float((zl.LAST["cnt"][:2]).sum()), 1.0) if core is not None else 0.0
            row = dict(label=label, fill=fill, e_ref=ref["E"], t_ref=ref["t_with"], err_e={k: zref.error_pct(v, ref["E"]) for k, v in e.items()},
                       err_t={k: 100 * (v / ref["t_with"] - 1) for k, v in t.items()}, core_share=share, warnings=warn)
            rows.append(row)
            print(f"| {label} | {'Cu' if fill else 'open'} | {ref['E']:.2f} | {ref['t_with']:.2f} | " + " | ".join(f"{row['err_e'][k]:+.1f}" for k in e) + " | " + " | ".join(f"{row['err_t'][k]:+.1f}" for k in t) +
                  f" | {share:.2f} | {len(warn)} |", flush=True)
    print("written", zref.save_json("multigroup.json", rows))


if __name__ == "__main__":
    main()
