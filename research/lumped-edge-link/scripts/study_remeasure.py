#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_remeasure.py
@brief Re-measure the near-edge deficit of the Lumped part read-out (peak with peak, mean with mean) against the FVM at 0.5 mm, and the variants of the first link.
@details The part rows are read as the Results table gives them (analysis.heater_stats: the Lumped part row is max(painted field, its own peak), since fix/lumped-part-readout).
         Boards 60 x 40 and 100 x 80 mm, 2 layers (and 4 layers for the 6 mm part), full copper 35 um, 1.6 mm, faces 10 / 15 W/m2K, a square source of 3, 6 or 10 mm on layer 1 at a gap of
         0 to 25 mm from a side (centred along it) or from a corner, edge film 0, 10, 50, 200 W/m2K. Variants of lib/variants.py: program, expo_peak, img, pot, pot_first, pot_rings, delta, pot:0.8 (reflection 0.8), pot_first:0.8.
         Writes out/remeasure.json (and a cache of the FVM); REMEASURE_VARIANTS (comma list) and REMEASURE_OUT select other variants and file. Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-edge-link/scripts/study_remeasure.py [quick]
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402

VARIANTS = ("program", "expo_peak", "img", "pot", "pot_first", "pot_rings", "delta", "pot:0.8", "pot_first:0.8")
VARIANTS = tuple(os.environ["REMEASURE_VARIANTS"].split(",")) if os.environ.get("REMEASURE_VARIANTS") else VARIANTS      # a shorter list re-uses the cached FVM
GAPS = (0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0)


def cases(quick=False):
    """!
    @brief The case list.
    @param quick True for a short list (100 x 80 mm, 6 mm part, h_side 10 and 200).
    @return List of dicts.
    """
    out = []
    for W, H in (((100.0, 80.0),) if quick else ((60.0, 40.0), (100.0, 80.0))):
        for side in ((6.0,) if quick else (3.0, 6.0, 10.0)):
            for layers in ((2,) if (quick or side != 6.0) else (2, 4)):
                for place in ("edge", "corner"):
                    for d in GAPS:
                        cx = d + side / 2
                        cy = H / 2 if place == "edge" else d + side / 2
                        if cx > W / 2 + 1e-9 or cy > H / 2 + 1e-9:
                            continue
                        for hs in ((10.0, 200.0) if quick else (0.0, 10.0, 50.0, 200.0)):
                            out.append({"W": W, "H": H, "side": side, "layers": layers, "place": place, "d": d, "h_side": hs})
    return out


def run_case(c, cell=0.5):
    """!
    @brief FVM and the variants for one case.
    @param c Case dict.
    @param cell Cell in mm.
    @return Dict with the case, the FVM (mean, peak) and per variant the errors in % (mean, peak).
    """
    side = c["side"]
    pos = (c["d"] + side / 2, c["H"] / 2 if c["place"] == "edge" else c["d"] + side / 2)
    p = B.board(c["W"], c["H"], side, pos, layers=c["layers"], h_side=c["h_side"])
    key = f"{c['W']}|{c['H']}|{side}|{c['layers']}|{c['place']}|{c['d']}|{c['h_side']}"
    fm, fx, _ = B.fvm_part(key, p, cell)
    res = dict(c, fvm_mean=fm, fvm_peak=fx)
    for v in VARIANTS:
        V.install(v)
        m, x, _ = B.part_read(p, "lumped", cell)
        res[v] = [100 * (m / fm - 1), 100 * (x / fx - 1)]
    return res


def main():
    """!
    @brief Run the sweep.
    @return None.
    """
    quick = "quick" in sys.argv
    rows = []
    cs = cases(quick)
    for i, c in enumerate(cs):
        rows.append(run_case(c))
        r = rows[-1]
        print(i, len(cs), c["W"], c["side"], c["layers"], c["place"], c["d"], c["h_side"], f"fvm {r['fvm_peak']:.2f}", *[f"{v} {r[v][0]:+.1f}/{r[v][1]:+.1f}" for v in VARIANTS], flush=True)
        if i % 25 == 0:
            B.OUT.mkdir(exist_ok=True)
            (B.OUT / ("remeasure_quick.json" if quick else os.environ.get("REMEASURE_OUT", "remeasure.json"))).write_text(json.dumps(rows, indent=1))
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / ("remeasure_quick.json" if quick else os.environ.get("REMEASURE_OUT", "remeasure.json"))).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
