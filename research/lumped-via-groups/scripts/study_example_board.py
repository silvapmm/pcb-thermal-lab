#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_example_board.py
@brief The example board of the program (100 x 80 mm, partial top copper, a bottom heatsink, two parts) with its 9 vias and with 5 x 5, 7 x 7 and 20 x 20 arrays under U1: the Lumped variants against the corrected FVM.
@details Real boards after the simple ones: partial copper on the top layer, a heatsink under the parts, a second heater, h of 10 and 15 W/m2K, a 10 x 10 mm footprint. The reference is the FVM with the
         corrected via treatment of `research/point-via-convergence` (`FVM_fix`, 0.25 mm; it is the best the program has and is NOT independent of the layered idealisation: it is within 0.4 to
         1 % of the fine-grid layered reference on the simple boards of `lumped-analytic-vias`). Variants: `L_prog` (the program), `L_nn` (micro well only), `L_grp0` (the earlier group term),
         `L_out` (the group term outside the footprint only), `L_zone` (two zones, this folder). The via effect is E = T_max(no vias) - T_max(vias); error = 100 (E / E_ref - 1) %.
         The boards of `lumped-analytic-vias/scripts/study_real_boards.py` (`example`) are used unchanged. The reference is cached in `out/real_ref.json`.
Usage: python research/lumped-via-groups/scripts/study_example_board.py   (from the repository root; about 15 minutes)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(FOLDER), "lumped-analytic-vias", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(FOLDER), "lumped-analytic-vias", "scripts"))

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import refs                                                                  # noqa: E402
import study_real_boards as srb                                              # noqa: E402

NAMES = ["L_prog", "L_nn", "L_grp0", "L_out", "L_zone"]
BOARDS = [("example, 9 vias at 3.5 mm", 0, 3.5), ("5 x 5 at 1.2 mm", 5, 1.2), ("7 x 7 at 1.0 mm", 7, 1.0), ("20 x 20 at 1.0 mm", 20, 1.0)]
CACHE = os.path.join(FOLDER, "out", "real_ref.json")


def main():
    """!
    @brief Run the boards and print the tables.
    @return None.
    """
    pc.load_libraries()
    os.makedirs(os.path.join(FOLDER, "out"), exist_ok=True)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    rows = []
    for label, n, pitch in BOARDS:
        for fill in (0.0, 385.0):
            prob = srb.example(fill, n, pitch)
            q0 = hz.no_vias(prob)
            key = f"{n}_{pitch}_{fill}"
            if key not in cache:
                cache[key] = hz.effect(prob, "fvm", hz.VARIANTS["FVM_fix"][1], 0.25, q0)
                json.dump(cache, open(CACHE, "w"))
            e_ref = cache[key]
            e = {k: hz.effect(prob, "lumped", refs.VARIANTS[k], 0.5, q0) for k in NAMES}
            rows.append({"board": label, "fill": fill, "E_ref": e_ref, "E": e})
            print(f"{label} fill {fill}: E_ref {e_ref:.3f} K  " + "  ".join(f"{k} {100 * (e[k] / e_ref - 1):+.1f}%" for k in NAMES), flush=True)
    json.dump(rows, open(os.path.join(FOLDER, "out", "real_boards.json"), "w"), indent=1)
    print("\n| board | fill | E_ref K | " + " | ".join(NAMES) + " |\n| :-- | :-- | --: |" + " --: |" * len(NAMES))
    for r in rows:
        print(f"| {r['board']} | {'Cu' if r['fill'] else 'open'} | {r['E_ref']:.3f} | " + " | ".join(f"{100 * (r['E'][k] / r['E_ref'] - 1):+.1f}" for k in NAMES) + " |")
    print("\n| board | gain K (ref) | " + " | ".join(NAMES) + " |\n| :-- | --: |" + " --: |" * len(NAMES))
    for i in range(0, len(rows), 2):
        o, c = rows[i], rows[i + 1]
        g = c["E_ref"] - o["E_ref"]
        print(f"| {o['board']} | {g:.3f} | " + " | ".join(f"{100 * (((c['E'][k] - o['E'][k]) / g) - 1):+.1f}" for k in NAMES) + " |")


if __name__ == "__main__":
    main()
