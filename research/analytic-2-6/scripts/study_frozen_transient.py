#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_transient.py
@brief Which frozen Analytic times to 63 % the local modal transient would move: the boards of the regression harness with vias or a heatsink, first part alone, cell 1 mm.

@details For every harness board with vias or heatsinks and no outline or block (the Analytic transient has none of those), the unit-step response of the first part (the
         other parts at zero power, which is what the program's per-part modal systems do) of the FVM (2 mm, as the API), the Analytic as in the program and the
         local modal prototype K 16. Prints the three times to 63 % and the changes.
         Run from the repository root: .venv/bin/python research/analytic-2-6/scripts/study_frozen_transient.py
"""

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(REPO, "tests", "regression"))
sys.path.insert(0, REPO)

import boards26 as B                   # noqa: E402
import local_modal as LM               # noqa: E402
import regress_boards as RB            # noqa: E402
from pcbthermal import analytic, blocks, fvm   # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print(f"{'board':20s} {'vias':>4s} {'sinks':>5s} {'FVM s':>8s} {'program s':>10s} {'local K16 s':>12s} {'program/FVM':>11s} {'local/FVM':>10s} {'local/program':>13s}")
    for name in RB.board_names():
        p = RB.build(name, os.path.join(REPO, "examples"))
        outline = getattr(p.board, "outline", None)
        if (outline is not None and len(outline) > 0) or blocks.has_blocks(p) or not (p.vias or p.heatsinks) or not p.heaters:
            continue
        solo = copy.deepcopy(p)
        for k, h in enumerate(solo.heaters):
            h.power = 1.0 if k == 0 else 0.0
            h.profile = None
        t, z, r = fvm.step_responses(solo, cell_mm=2.0)
        f = B.t63(t, z[:1], r[:1])[0]
        ta, za, ra = analytic.step_responses(solo, 1.0)
        a = B.t63(ta, za[:1], ra[:1])[0]
        tl, zl, rl, _ = LM.step_local(solo, 1.0, 300, 16)
        l = B.t63(tl, zl, rl)[0]
        print(f"{name:20s} {len(p.vias):4d} {len(p.heatsinks):5d} {f:8.2f} {a:10.2f} {l:12.2f} {100 * (a / f - 1):+10.1f}% {100 * (l / f - 1):+9.1f}% {100 * (l / a - 1):+12.1f}%", flush=True)


if __name__ == "__main__":
    main()
