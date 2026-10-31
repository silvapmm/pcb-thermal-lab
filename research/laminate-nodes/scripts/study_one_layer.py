#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_one_layer.py
@brief The laminate under the copper of a one-layer board (laminate.py): two nodes everywhere against the one rule (nodes only where the copper is partly absent, a single link elsewhere).
@details Question answered: laminate.py gives every cell two laminate nodes (-0.0 to -0.3 % with full copper, -2.5 % with a 20 mm pad, 5.5 to 13.6 % cool on real windows, gerber-models R2). Does
         the mask (A11, first measured on multilayer boards in bare-spot-under-source) work on a one-layer board? Boards: full copper, pads 6 to 40 mm, windows 2 to 12 mm, a track (a 2 mm
         strip) and an island pad of 4 mm under a 3 mm part, board 30 mm (60 mm for the 40 mm pad), 1.6 mm and 0.8 mm laminate. Treatments: the program (2 nodes everywhere); the ladder with n = 1, 2, 4, 8 in
         every cell (mask all: must equal laminate.py at n = 2, an invariance check); the ladder with the default law and the mask bare + margin (n = 4 for 1.565 mm); n = 8. Printed: error against the
         reference, ragged and dense unknown ratio against the program's 3 per cell. Full copper has an empty mask (every cell is a single link): its error is the one-link error of the
         laminate (to compare with the 2-node values quoted in laminate.py). Output: out/one_layer.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_one_layer.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import report as RP
import rule as RU
import runner as RN


def main():
    """!
    @brief Run the one-layer boards.
    @return None.
    """
    specs = [BD.Spec("1L full", layers=1, shapes=[("full",)])]
    specs += [BD.Spec(f"1L pad {s}", layers=1, shapes=[("pad", s)]) for s in (6, 10, 20)]
    specs += [BD.Spec("1L pad 40 (board 60)", layers=1, size=60.0, shapes=[("pad", 40)])]
    specs += [BD.Spec(f"1L window {s}", layers=1, shapes=[("window", s)]) for s in (2, 4, 6, 12)]
    specs += [BD.Spec("1L track 2 mm", layers=1, shapes=[("rects", [(0, 14, 30, 16)])]), BD.Spec("1L island 4 under 3", layers=1, part=3.0, shapes=[("pad", 4)])]
    specs += [BD.Spec("1L 0.8 mm pad 10", layers=1, thickness=0.8, shapes=[("pad", 10)])]
    rules = {"program (2 nodes)": RU.PRESETS["program"], "ladder n=1 all": RU.Rule(n_fixed=1, mask="all", vert=False, face=-1.0), "ladder n=2 all": RU.Rule(n_fixed=2, mask="all", vert=False, face=-1.0),
             "n=4 all": RU.Rule(n_fixed=4, mask="all", vert=False, face=-1.0), "proposed (mask)": RU.Rule(), "proposed n=8": RU.Rule(n_fixed=8)}
    rows = []
    for s in specs:
        r = RN.row(s, rules)
        row = {"board": s.name, "ref K": (".2f", r["ref"])}
        for k in rules:
            row[k] = r[k]["err"]
        row["unk x (mask)"] = (".2f", r["proposed (mask)"]["ratio"])
        rows.append(row)
    RP.table(rows, list(rows[0]), title="One-layer boards: error of the peak against the resolved 3D face value, percent (cell 0.5 mm)")
    RP.save("one_layer", rows)


if __name__ == "__main__":
    main()
