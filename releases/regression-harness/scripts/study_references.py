#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_references.py
@brief Question: what does an independent layered 3D conduction solver give on the four reference-capable boards? Writes `out/references.json` (it does not depend on the revision, so it is solved once).
@details Usage, from the repository root:

         .venv/bin/python releases/regression-harness/scripts/study_references.py                  # cells 2 and 1 mm (fast)
         .venv/bin/python releases/regression-harness/scripts/study_references.py --cells 2 1 0.5  # the 0.5 mm solves are slow (minutes each)

         The solver is `research/solid3d-verification/lib/layered3d.py` (imports nothing from the program). The boards are the entries of `regress_boards.REFERENCE_SPECS`; the compared
         number is the rise of the hottest top-copper cell under the source on the same cell size as the model (see `regress_refsolve.py`).
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_boards as B                                                  # noqa: E402
import regress_refsolve as R                                                # noqa: E402


def main(argv=None):
    """!
    @brief Solve the references and print them.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--cells", nargs="+", type=float, default=[2.0, 1.0])
    ap.add_argument("--out", default=str(ROOT / "out" / "references.json"))
    a = ap.parse_args(argv)
    ref = R.compute_references(B.REFERENCE_SPECS, a.cells, a.out, log=print)
    print("\n| Board | " + " | ".join(f"rise at {c:g} mm [K]" for c in a.cells) + " |")
    print("| :-- | " + " | ".join("--:" for _ in a.cells) + " |")
    for name in B.REFERENCE_SPECS:
        print(f"| {name} | " + " | ".join(f"{ref[name][f'{c:g}']:.4f}" for c in a.cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
