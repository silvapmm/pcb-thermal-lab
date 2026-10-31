#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_outside.py
@brief Vias that lie outside the footprint (a row of five and a lone via beside a 3 mm source): the group term outside the footprint, tested again with this folder's variants.
@details The question: the two-zone model changes only the footprint; for vias in the rings outside it the group term of `lumped-analytic-vias` stays. This script repeats the boards of its
         `study_arrays.py` (row of five at 1 mm pitch on a 16 mm board; a lone via 2, 4 and 8 mm from the source on a 30 mm board; 2 and 4 layers; drill 0.3 and 0.6 mm; open and copper fill)
         for `L_prog`, `L_ring` (micro well only), `L_grp0` (with the group term; identical to the "outside only" variant here, because no via is in the footprint), the lossy macro cell
         (`L_loss`) and the zone model, and prints the mean and maximum error of E (both fills) per board kind. The fine-grid layered reference is the one of that investigation.
Usage: python research/lumped-via-groups/scripts/study_outside.py   (from the repository root; about 10 minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-analytic-vias", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-analytic-vias", "scripts"))

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import refs                                                                  # noqa: E402
import study_arrays as sa                                                    # noqa: E402

NAMES = ["L_prog", "L_ring", "L_grp0", "L_loss", "L_zone"]


def main():
    """!
    @brief Run the boards and print the table.
    @return None.
    """
    pc.load_libraries()
    rows = []
    for layers in (2, 4):
        for dia in (0.3, 0.6):
            tasks = [("lone", (layers, dia, d)) for d in (2.0, 4.0, 8.0)] + [("row", (layers, dia))]
            for kind, params in tasks:
                for fill in (0.0, 385.0):
                    prob = sa.build(kind, params, fill)
                    e_ref = hz.reference_uniform(prob, 1.0 / 16)[0]
                    q0 = hz.no_vias(prob)
                    e = {n: hz.effect(prob, "lumped", refs.VARIANTS[n], 0.5, q0) for n in NAMES}
                    rows.append({"kind": kind, "params": params, "fill": fill, "E_ref": e_ref, "E": e})
                    print(kind, params, fill, f"E_ref {e_ref:.3f}", " ".join(f"{n} {100 * (e[n] / e_ref - 1):+.1f}" for n in NAMES), flush=True)
    for kind in ("lone", "row"):
        sel = [r for r in rows if r["kind"] == kind]
        print(f"\n{kind} ({len(sel)} cases)\n\n| variant | E mean | E max |\n| :-- | --: | --: |")
        for n in NAMES:
            v = [abs(100 * (r["E"][n] / r["E_ref"] - 1)) for r in sel]
            print(f"| {n} | {sum(v) / len(v):.1f} | {max(v):.1f} |")


if __name__ == "__main__":
    main()
