#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_sweep.py
@brief How much too cool is the Lumped model for a part near a board edge or corner, and do the candidate corrections help?
@details Two-layer full-copper boards (40 x 40 and 100 x 80 mm, 35 um copper, 1.6 mm, h 10 / 15 W/m2K on the faces), a square source of 2, 5 or 10 mm on layer 1 at a gap d
         (0 to 30 mm, source edge to board edge) from one edge (centred along it) or from two (corner), edge film 10, 50 or 200 W/m2K. Reference: the FVM at 0.5 mm (cached);
         the Lumped at 0.5 mm as the program has it ("program"), with the image potentials ("image") and with image potentials and potential links ("potlinks").
         Error = Lumped / FVM - 1 on the footprint mean and on the hottest node. Writes out/edge_sweep.json. Run from the repository root:
         PCBT_TREE=<checkout of feature/integration-260> QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-near-edge/scripts/study_edge_sweep.py [quick]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402

VARIANTS = ("program", "image", "potlinks")


def cases(quick=False):
    """!
    @brief The list of cases.
    @param quick True for a short list.
    @return List of dicts (board, side, place, d, h_side).
    """
    out = []
    boards = ((100.0, 80.0),) if quick else ((40.0, 40.0), (100.0, 80.0))
    for W, H in boards:
        for side in (2.0, 5.0, 10.0):
            for place in ("edge", "corner"):
                for d in (0.0, 2.0, 5.0, 10.0, 20.0, 30.0):
                    cx = d + side / 2
                    cy = H / 2 if place == "edge" else d + side / 2
                    if cx > W / 2 + 1e-9 or cy > H / 2 + 1e-9:
                        continue
                    for hs in ((10.0, 200.0) if quick else (10.0, 50.0, 200.0)):
                        out.append({"W": W, "H": H, "side": side, "place": place, "d": d, "h_side": hs})
    return out


def run_case(c, cell=0.5):
    """!
    @brief FVM and the variants for one case.
    @param c Case dict.
    @param cell Cell in mm.
    @return Dict with the case, fvm (mean, max) and per variant the errors in %.
    """
    side = c["side"]
    cx = c["d"] + side / 2
    cy = c["H"] / 2 if c["place"] == "edge" else c["d"] + side / 2
    pos = (cx, cy)
    p = B.board(c["W"], c["H"], side, pos, h_side=c["h_side"])
    key = f"sweep|{c['W']}|{c['H']}|{side}|{c['place']}|{c['d']}|{c['h_side']}"
    fm, fx = B.fvm(key, p, cell, side, pos)
    res = dict(c, fvm_mean=fm, fvm_max=fx)
    for v in VARIANTS:
        V.install(v)
        m, x = B.readout(p, "lumped", cell, side, pos)
        res[v] = [100 * (m / fm - 1), 100 * (x / fx - 1)]
    return res


def main():
    """!
    @brief Run the sweep and print a summary table per variant.
    @return None.
    """
    quick = "quick" in sys.argv
    rows = []
    for i, c in enumerate(cases(quick)):
        rows.append(run_case(c))
        r = rows[-1]
        print(i, c["W"], c["side"], c["place"], c["d"], c["h_side"], f"fvm {r['fvm_max']:.2f}", *[f"{v} {r[v][0]:+.1f}/{r[v][1]:+.1f}" for v in VARIANTS], flush=True)
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / ("edge_sweep_quick.json" if quick else "edge_sweep.json")).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
