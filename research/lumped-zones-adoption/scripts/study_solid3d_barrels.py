#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d_barrels.py
@brief Study 9b: the program's own 3D solid (real slabs per copper layer and gap, the via by its footprint rule) at a fine cell on the six boards of study 9, as a second 3D view next to the independent solver.
@details The 3D solid of the program (`solid3d`, key `solid3d`) is not independent of the program but it is a different discretisation (the planes have their thickness, the gaps are sub-slabs, the barrel is
         a footprint of cells with the copper of the barrel). It is run at cells of 0.25 and 0.16 mm (16 slabs: 0.125 mm would be 262 144 unknowns, above the limit of 250 000, which stays; the number of unknowns is printed) on the same boards,
         with and without vias. Quantities: the via effect E and the hottest rise, compared with the independent 3D solver of study 9 (`out/barrels_3d.json`, read here), `P245` and `Z_none`.
         Success criterion (fixed before running): the 3D solid within 15 % of the independent 3D solver in E on the five boards that are not off centre (the two 3D views agree), so that either can
         stand for the 3D truth; where they differ the table says so and no claim is made from the 3D solid alone.
Usage: python research/lumped-zones-adoption/scripts/study_solid3d_barrels.py   (after study_3d_barrels.py; from the repository root; one process, under 3 GB)
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import zref                                                                  # noqa: E402
import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import study_3d_barrels as s3                                                # noqa: E402
from pcbthermal import solid3d                                               # noqa: E402


def main():
    """!
    @brief Run the solid3d at the fine cells and print the table.
    @return None.
    """
    pc.load_libraries()
    base = json.load(open(os.path.join(zref.OUT, "barrels_3d.json")))
    k = 0
    out = []
    print("| board | fill | cell mm | unknowns | solid3d E K | solid3d rise K | independent 3D E | independent 3D rise | E diff % | rise diff % | P245 E vs solid3d % | Z_none E vs solid3d % | seconds |\n"
          "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for label, spec, centred in s3.BOARDS:
        for fill in (385.0, 0.0):
            s = {**s3.BASE, **spec, "fill": fill}
            p = zref.refs.make_problem(s)
            q0 = hz.no_vias(p)
            b = base[k]
            k += 1
            for cell in (0.25, 0.16):
                t0 = time.time()
                n = solid3d.unknowns(p, cell)[0]
                try:
                    t1 = pc.max_rise(p, "solid3d", cell)
                    t0v = pc.max_rise(q0, "solid3d", cell)
                except ValueError as exc:
                    print(f"| {label} | {'Cu' if fill else 'open'} | {cell} | {n} | refused: {str(exc)[:50]} |")
                    continue
                e = t0v - t1
                row = dict(label=label, fill=fill, cell=cell, unknowns=int(n), e=e, t=t1, e3=b["e3"], t3=b["t3"], seconds=time.time() - t0)
                out.append(row)
                print(f"| {label} | {'Cu' if fill else 'open'} | {cell} | {n} | {e:.3f} | {t1:.2f} | {b['e3']:.3f} | {b['t3']:.2f} | {100 * (e / b['e3'] - 1):+.1f} | {100 * (t1 / b['t3'] - 1):+.1f} | "
                      f"{100 * (b['e_p'] / e - 1):+.1f} | {100 * (b['e_z'] / e - 1):+.1f} | {row['seconds']:.0f} |", flush=True)
    print("written", zref.save_json("barrels_solid3d.json", out))


if __name__ == "__main__":
    main()
