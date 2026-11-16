#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_a4_near_edge.py
@brief Audit A4 R4: the 180-case near-edge sweep of validation 35.1 on the program of 2.7.1 (Lumped and FVM at 0.5 mm through api.simulate, the boards of
       research/lumped-near-edge/lib/boards.py); hottest rise (board maximum = the part's own peak, one part) and footprint mean; and the warning rule gap <= max(side, 5 mm).
@details Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_a4_near_edge.py $PWD out.json (releases/2.8.0/audit/REVIEW_A4.md).
"""
import sys, json, numpy as np
root = sys.argv[1]; sys.path.insert(0, root); sys.path.insert(0, root + "/research/lumped-near-edge/lib")
import boards as B
rows = []
for W, H in ((40.0, 40.0), (100.0, 80.0)):
    for side in (2.0, 5.0, 10.0):
        for place in ("edge", "corner"):
            for d in (0.0, 2.0, 5.0, 10.0, 20.0, 30.0):
                cx = d + side / 2; cy = H / 2 if place == "edge" else d + side / 2
                if cx > W / 2 + 1e-9 or cy > H / 2 + 1e-9:
                    continue
                for hs in (10.0, 50.0, 200.0):
                    p = B.board(W, H, side, (cx, cy), h_side=hs)
                    fm, fh = B.readout(p, "fvm", 0.5, side, (cx, cy))
                    lm, lh = B.readout(p, "lumped", 0.5, side, (cx, cy))
                    r = dict(W=W, side=side, place=place, d=d, hs=hs, hot=100 * (lh / fh - 1), mean=100 * (lm / fm - 1), flag=d <= max(side, 5.0))
                    rows.append(r); print(json.dumps(r), flush=True)
json.dump(rows, open(sys.argv[2], "w"))
def summ(sel, name):
    """!
    @brief Print the mean and range of a set of cases.
    @param sel List of case dicts.
    @param name Label.
    """
    h = np.array([r["hot"] for r in sel]); m = np.array([r["mean"] for r in sel])
    print(f"{name:18s} n {len(sel):3d} hot {h.mean():+6.1f} [{h.min():+6.1f}, {h.max():+5.1f}] mean {m.mean():+6.1f} [{m.min():+6.1f}, {m.max():+5.1f}]")
summ(rows, "all")
for place in ("edge", "corner"):
    for d in (0.0, 5.0, 30.0):
        summ([r for r in rows if r["place"] == place and r["d"] == d], f"{place} gap {d:.0f}")
bad = [r for r in rows if r["hot"] < -8]; print("bad", len(bad), "flagged&bad", sum(r["flag"] for r in bad), "false alarms", sum(r["flag"] and r["hot"] >= -8 for r in rows))
f = [r["hot"] for r in rows if r["flag"]]; o = [r["hot"] for r in rows if not r["flag"]]
print(f"flagged mean {np.mean(f):+.1f} others {np.mean(o):+.1f}")
