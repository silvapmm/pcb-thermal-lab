#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cluster_in_cell.py
@brief The simplest board of the group term: an n x n cluster of vias at 1 mm pitch in the middle of an 8 mm cell that is heated everywhere (the footprint is the whole board).
@details The same boards as `lumped-analytic-vias/scripts/study_causes.py` part 3 (2 and 4 layers, open and copper, 1 to 16 vias), for `L_prog`, the micro well only (`L_nn`), the series
         group term (`L_grp0`), the zone model of this folder in its first version (`L_zone0`) and as proposed (`L_zone`). Here the footprint has no ring outside it: the zone model has
         two nodes per layer and nothing else, so it is a direct test of the lateral link A-C, the core-internal resistance and the micro peak against the fine-grid reference.
Usage: python research/lumped-via-groups/scripts/study_cluster_in_cell.py   (from the repository root; about 5 minutes)
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
import study_causes as sc                                                    # noqa: E402

NAMES = ["L_prog", "L_nn", "L_grp0", "L_zone0", "L_zone_r", "L_zone"]


def main():
    """!
    @brief Run the boards and print the table.
    @return None.
    """
    pc.load_libraries()
    print("| layers | fill | vias | E_ref K | " + " | ".join(NAMES) + " |\n| --: | :-- | --: | --: |" + " --: |" * len(NAMES))
    for layers in (2, 4):
        for fill in (0.0, 385.0):
            for n in (1, 2, 3, 4):
                prob = sc.cluster_board(n, fill=fill, layers=layers)
                e_ref = hz.reference_uniform(prob, 1.0 / 16)[0]
                q0 = hz.no_vias(prob)
                err = {k: 100.0 * (hz.effect(prob, "lumped", refs.VARIANTS[k], 0.5, q0) / e_ref - 1.0) for k in NAMES}
                print(f"| {layers} | {'Cu' if fill else 'open'} | {n * n} | {e_ref:.2f} | " + " | ".join(f"{err[k]:+.1f}" for k in NAMES) + " |", flush=True)


if __name__ == "__main__":
    main()
