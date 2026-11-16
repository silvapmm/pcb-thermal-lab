#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_outline_boards.py
@brief Boards with an outline: the turned and shifted squares, T and L of validation 40 with the copper drawn, the program as it is against the copy that reads the zones as an import.
@details Reuses the cases, builders and the independent 3D truths of `research/imported-copper-edge-film/scripts/study_drawn_film.py` (ten boards per case: five turns, two shifts against
         the grid). For every case, edge film and cell the mean, spread and worst error of the FVM heater mean against the truth, before and inside `lib/patched.use('faces')`.
         Run: `.venv/bin/python research/drawn-copper-faces/scripts/study_outline_boards.py [case,...]`. Cache `out/outline_skip.json`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "imported-copper-edge-film", "scripts"))
import numpy as np                                                        # noqa: E402
import study_drawn_film as S                                              # noqa: E402
import patched as P                                                       # noqa: E402

OUT = os.path.join(HERE, "..", "out", "outline_skip.json")
DEFAULT = ("sq_in", "sq_wall", "sq_4l", "sq_pad", "sq_stripes", "T_in", "T_wall", "L_in", "L_wall")


def board_values(spec, h, cell):
    """!
    @brief Heater means of the ten boards.
    @param spec Case spec.
    @param h Edge film.
    @param cell Cell mm.
    @return list of float.
    """
    out = []
    for sh in S.SHIFTS:
        for ang in S.ANGLES:
            out.append(S.heater_rise(S.build(spec, h, ang, sh * cell, spec.get("imported", ())), cell)[0])
    return out


def main():
    """!
    @brief Run and print the table.
    @return None.
    """
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    print("case|h|cell: error of the heater mean against the 3D truth, mean / spread / worst %, program -> zones read as an import")
    for name in names:
        spec = S.CASES[name]
        for h in spec["hs"]:
            for cell in spec["cells"]:
                key = f"{name}|{h:g}|{cell:g}"
                if key not in res:
                    a = board_values(spec, h, cell)
                    with P.use("faces"):
                        b = board_values(spec, h, cell)
                    res[key] = {"base": a, "new": b}
                    json.dump(res, open(OUT, "w"))
                tr = S.truth_of(name, h)
                ea, eb = (100 * (np.array(res[key][k]) / tr - 1) for k in ("base", "new"))
                print(f"{key:24s} {ea.mean():+6.2f} / {np.ptp(ea):5.2f} / {np.abs(ea).max():5.2f}  ->  {eb.mean():+6.2f} / {np.ptp(eb):5.2f} / {np.abs(eb).max():5.2f}", flush=True)


if __name__ == "__main__":
    main()
