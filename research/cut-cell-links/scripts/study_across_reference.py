#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_across_reference.py
@brief The harness board `part_across_outline` (outline edge at x = 37.3 mm between the cell edges of 2, 1 and 0.5 mm, a part across it) against the same board at finer cells (README 5.4).
@details The edge lies at 37.3 mm, so on cells of 0.25, 0.125 and 0.0625 mm it is cut at every step (37.3 / 0.125 = 298.4): the finest values are the program's and the scheme's own
         convergence, printed for 2 to 1/16 mm, with the difference between the two at the finest cell as the uncertainty of the reference.
Usage: .venv/bin/python research/cut-cell-links/scripts/study_across_reference.py   (from the repository root; about 1 minute, below 1 GB)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))

import cutlinks as cl         # noqa: E402
import regress_boards as rb   # noqa: E402


def main():
    """!
    @brief Print the hottest temperature of the program and of the two link schemes against the cell.
    @return None.
    """
    cells = (2.0, 1.0, 0.5, 0.25, 0.125, 0.0625)
    print("| scheme | " + " | ".join(f"{c:g} mm" for c in cells) + " |\n| :-- | " + " | ".join("--:" for _ in cells) + " |")
    for s in ("program", "aperture", "aperture+film", "links"):
        print(f"| {s} | " + " | ".join(f"{cl.tmax(rb.build('part_across_outline'), c, s):.3f}" for c in cells) + " |", flush=True)


if __name__ == "__main__":
    main()
