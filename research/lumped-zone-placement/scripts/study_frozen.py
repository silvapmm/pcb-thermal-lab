#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen.py
@brief Study 5: which frozen Lumped records of the 17 boards of `tests/regression` would move under the candidate rules, by how much (K), measured on a copy (monkeypatches), and which boards have a zoned part.
@details For every board of the harness, every cell of the frozen test (2, 1, 0.5 mm) the Lumped is run through `regress_harness.run_one` as the program is and under each candidate; the hottest point and the mean of
         every part and the board maximum are compared (largest absolute difference per record, K), and the time to 63 % of the step response (`regress_harness.t63`, cell 1 mm) is compared too. The set of records
         that move is the set the later fix would have to take out of `tests/regression/data/pending/lumped-part-readout.json`. No file of the test is edited.
Usage: python research/lumped-zone-placement/scripts/study_frozen.py   (from the repository root; ONE process; light; about 3 minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import placement as pl                                                        # noqa: E402,F401
import regress_boards as B                                                    # noqa: E402
import regress_harness as H                                                   # noqa: E402

RULES = {"robust@0.5": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote"),
         "robust@0.25": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", zone_cell=0.25),
         "robust@0.5, MAX_CORE 0.8": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", max_core=0.8),
         "robust@0.5, MAX_CORE 0.75": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", max_core=0.75)}


def numbers(rec):
    """!
    @brief The temperatures of a record that the frozen test compares: board maximum, mean, and the hottest point and mean of every part.
    @param rec Record of `run_one`.
    @return list of floats (empty when the record is not ok).
    """
    if rec["status"] != "ok":
        return []
    out = [rec["t_max"], rec["t_mean"]]
    for p in rec.get("parts") or []:
        out += [p["t_max"], p["t_mean"]]
    return out


def main():
    """!
    @brief Run and print the table of moved records.
    @return None.
    """
    print("| rule | record | largest change K | zoned parts in the program run |")
    print("| :-- | :-- | --: | :-- |")
    n_rec = 0
    moved = {k: [] for k in RULES}
    for name in B.board_names():
        prob = B.build(name)
        if len(prob.vias) < 2:
            continue                                                        # no pair of vias: no zone can exist, the rule cannot touch this board
        n_rec += 3
        for cell in H.CELLS:
            base = numbers(H.run_one(prob, name, "lumped", cell))
            for rule, opt in RULES.items():
                with pl.patched(**opt):
                    new = numbers(H.run_one(prob, name, "lumped", cell))
                d = max((abs(a - b) for a, b in zip(base, new)), default=0.0)
                if d > 0:
                    moved[rule].append(f"{name}|lumped|{cell:g}")
                    print(f"| {rule} | {name}|lumped|{cell:g} | {d:.4g} | |", flush=True)
        for rule, opt in RULES.items():
            a = H.t63(prob, "lumped")
            with pl.patched(**opt):
                b = H.t63(prob, "lumped")
            for pa, pb in zip(a["parts"], b["parts"]):
                if pa["t63_s"] != pb["t63_s"]:
                    print(f"| {rule} | {name}|lumped|time to 63 % | {pa['t63_s']:.4g} -> {pb['t63_s']:.4g} s | |", flush=True)
    print(f"\nboards with at least two vias: records checked {n_rec}")
    for rule, m in moved.items():
        print(f"{rule}: {len(m)} records move: {m}")


if __name__ == "__main__":
    main()
