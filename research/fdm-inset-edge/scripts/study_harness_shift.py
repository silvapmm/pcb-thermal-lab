#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_shift.py
@brief Which FDM numbers of the 17 harness boards would move with the face-fill correction (README 6)?
@details Runs the FDM of the program with `face_fill=False` (the harmonic mean, as the study found it) and as adopted (`face_fill=True`; the base `Network` is wrapped in
         the place of `pcbthermal.fdm.Network`, so that the steady solve, the profile runner and the step responses all use it) on the boards of `tests/regression/regress_boards.py` at 2, 1 and 0.5 mm (FDM above 120 000 unknowns skipped
         to keep the memory under 3 GB) and prints, per board and cell, the shift of the hottest temperature, the mean and the first part's hottest and mean rise in percent of the
         rise, and the time to 63 % at the transient cell. Run from the repository root:
         `.venv/bin/python research/fdm-inset-edge/scripts/study_harness_shift.py [board,board,...]`. Output also in `research/fdm-inset-edge/out/harness_shift.json`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(2, os.path.join(HERE, "..", "lib"))

import regress_boards as RB                                  # noqa: E402
import regress_harness as RH                                 # noqa: E402
from pcbthermal import fdm                                   # noqa: E402

OUT = os.path.join(HERE, "..", "out", "harness_shift.json")
CELLS = (2.0, 1.0, 0.5)
CAP = 120_000


def pct(a, b, amb):
    """!
    @brief Shift of a value in percent of the rise over the ambient.
    @param a New value.
    @param b Old value.
    @param amb Ambient temperature.
    @return float.
    """
    return 100.0 * (a - b) / (b - amb)


def main():
    """!
    @brief Run the comparison and print the table.
    @return None.
    """
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else RB.board_names()
    base_net = fdm.Network

    def harm_net(*a, **k):
        # The program's network with the adopted face fill switched off
        k["face_fill"] = False
        return base_net(*a, **k)

    res = {}
    for name in names:
        for cell in CELLS:
            p = RB.build(name)
            recs = {}
            for tag, net in (("base", harm_net), ("face", base_net)):
                fdm.Network = net
                try:
                    recs[tag] = RH.run_one(p, name, "fdm", cell, max_unknowns=CAP)
                finally:
                    fdm.Network = base_net
            a, b = recs["base"], recs["face"]
            if a["status"] != "ok" or b["status"] != "ok":
                print(f"{name:20s} {cell:4} {a['status']} {a.get('reason', '')[:60]}", flush=True)
                continue
            amb = a["ambient"]
            row = {"tmax": pct(b["t_max"], a["t_max"], amb), "tmean": pct(b["t_mean"], a["t_mean"], amb), "balance": b["balance_error"],
                   "unknowns": a["unknowns"], "t_max_base": a["t_max"], "t_max_face": b["t_max"]}
            if a.get("parts") and b.get("parts"):
                row["part_max"] = max(abs(pct(y["t_max"], x["t_max"], amb)) for x, y in zip(a["parts"], b["parts"]))
                row["part_mean"] = max(abs(pct(y["t_mean"], x["t_mean"], amb)) for x, y in zip(a["parts"], b["parts"]))
            res[f"{name}|{cell}"] = row
            print(f"{name:20s} {cell:4} unk {a['unknowns']:7d} tmax {row['tmax']:+7.3f} % tmean {row['tmean']:+7.3f} % part max {row.get('part_max', float('nan')):6.3f} "
                  f"mean {row.get('part_mean', float('nan')):6.3f}  bal {row['balance']:.1e}", flush=True)
            json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
