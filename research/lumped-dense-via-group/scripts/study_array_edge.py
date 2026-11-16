#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_array_edge.py
@brief Study 6: the zoned Lumped when the via array reaches the edge of the footprint (part side from a little under to well over the array's side), against the FVM at 0.5 mm.
@details A 5 x 5 array at pitch 2.0 mm (8 mm square) and one at 1.5 mm (6 mm), a 3 W part of side 5 to 11 mm: per case the zoned decision, the core share, the number of vias with their
         centre in the footprint, and the errors of the zoned and the one-node Lumped against the FVM on the part peak and mean (percent of the FVM rise; the no-via baseline of the same
         part is printed once per part size).
Usage: python research/lumped-dense-via-group/scripts/study_array_edge.py   (from the repository root; ONE process)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| pitch | part | vias in footprint | core share | zoned? | zoned peak % | zoned mean % | one-node peak % | one-node mean % | no-via baseline % | zoned peak minus baseline % |")
    print("| --: | --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: |")
    for pitch in (2.0, 1.5):
        for part in (5.0, 6.0, 7.0, 7.5, 7.9, 8.0, 8.1, 8.5, 9.0, 10.0, 11.0):
            p = v.board(2, 5, pitch, 0.3, part)
            p0 = v.board(2, 0, pitch, 0.3, part)
            ref, z, o = v.run(p, "fvm", 0.5), v.run(p, "lumped", 0.5), v.run(p, "lumped1", 0.5)
            r0, l0 = v.run(p0, "fvm", 0.5), v.run(p0, "lumped1", 0.5)
            amb = ref["amb"]
            c = v.core_info(p)
            ez, eo = v.pct(z["parts"][0]["peak"], ref["parts"][0]["peak"], amb), v.pct(o["parts"][0]["peak"], ref["parts"][0]["peak"], amb)
            base = v.pct(l0["parts"][0]["peak"], r0["parts"][0]["peak"], amb)
            print(f"| {pitch} | {part} | {c['vias_in']} | {c['share']:.2f} | {c['zoned']} | {ez:+.1f} | {v.pct(z['parts'][0]['mean'], ref['parts'][0]['mean'], amb):+.1f} | {eo:+.1f} | "
                  f"{v.pct(o['parts'][0]['mean'], ref['parts'][0]['mean'], amb):+.1f} | {base:+.1f} | {ez - base:+.1f} |", flush=True)


if __name__ == "__main__":
    main()
