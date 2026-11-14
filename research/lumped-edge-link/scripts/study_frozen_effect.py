#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_effect.py
@brief Which Lumped records of the 17 frozen-number boards (2, 1 and 0.5 mm) and which times to 63 % a patched copy of the first link would move.
@details Runs the harness of tests/regression (regress_harness.run_one, t63) for the Lumped model with the program's lumped module and with a variant of lib/variants.py (installed
         where pcbthermal.api calls the Lumped model), both in this process, and lists every record whose hottest point, board mean or part rows differ by more than 1e-8 K.
         Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-edge-link/scripts/study_frozen_effect.py [variant ...]
"""

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "lib"))
os.environ.setdefault("PCBTHERMAL_CONFIG", tempfile.mkdtemp(prefix="pcbt-cfg-"))        # no user defaults
import boards as B  # noqa: E402,F401  (puts the checkout on sys.path)
import variants as V  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "tests" / "regression"))
import regress_boards as RB  # noqa: E402
import regress_harness as RH  # noqa: E402

TOL = 1e-8


def records(variant, cells, boards):
    """!
    @brief The Lumped records and times for one variant.
    @param variant Variant name of lib/variants.py.
    @param cells Cells in mm.
    @param boards Board names.
    @return dict {(board, cell): record}, dict {board: t63 record}.
    """
    V.install(variant)
    steady, times = {}, {}
    for b in boards:
        p = RB.build(b)
        for c in cells:
            steady[(b, c)] = RH.run_one(p, b, "lumped", c)
        if p.heaters:
            times[b] = RH.t63(p, "lumped")
    return steady, times


def main():
    """!
    @brief Compare the variants with the program and print the moved records.
    @return None.
    """
    variants = sys.argv[1:] or ["pot_first"]
    boards = RB.board_names()
    cells = (2.0, 1.0, 0.5)
    base_s, base_t = records("program", cells, boards)
    out = {}
    for v in variants:
        s, t = records(v, cells, boards)
        moved = []
        for k, r in s.items():
            b = base_s[k]
            if r["status"] != "ok" or b["status"] != "ok":
                continue
            d = {"t_max": r["t_max"] - b["t_max"], "t_mean": r["t_mean"] - b["t_mean"]}
            for pr, pb in zip(r.get("parts") or [], b.get("parts") or []):
                d["part_" + pr["name"]] = pr["t_max"] - pb["t_max"]
            big = {n: x for n, x in d.items() if abs(x) > TOL}
            if big:
                moved.append({"board": k[0], "cell": k[1], "rise": b["t_max"] - b["ambient"], "shifts_K": big})
        slow = []
        for bn, rec in t.items():
            for pr, pb in zip(rec.get("parts", []), base_t[bn].get("parts", [])):
                if pr.get("t63_s") is not None and pb.get("t63_s") and abs(pr["t63_s"] / pb["t63_s"] - 1) > 1e-6:
                    slow.append({"board": bn, "part": pr["name"], "t63_before": pb["t63_s"], "t63_after": pr["t63_s"]})
        out[v] = {"records_total": len(s), "records_moved": moved, "times_moved": slow}
        print(v, "records moved", len(moved), "of", len(s), "times moved", len(slow))
        for m in moved:
            print("  ", m["board"], m["cell"], "rise %.2f" % m["rise"], {k: round(x, 4) for k, x in m["shifts_K"].items()})
        for m in slow:
            print("  t63", m)
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "frozen_effect.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
