#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_repeat.py
@brief Question: does a variant repeat itself, that is, do two runs of the same variant on the same matrix give the same field (README acceptance rule: 1e-8 K)?
@details Builds the case once, solves it twice with the variant (two separate hierarchies) and prints the largest difference between the two fields and the iteration counts. Light (2 mm board).
         Usage (repository root): .venv/bin/python research/fem-amg-thin-layers/scripts/study_repeat.py --case example_2mm --variants base colblock_amg
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))


def main():
    """!
    @brief Solve the case twice per variant and print the repeatability.
    @return int Exit code (1 if a difference reaches 1e-8 K).
    """
    import cases
    import variants
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", default="example_2mm")
    ap.add_argument("--variants", nargs="*", default=["base", "colblock", "colblock_amg"])
    a = ap.parse_args()
    c = cases.build(a.case)
    cols = variants.column_ids(c["model"])
    bad = 0
    for v in a.variants:
        xs, its = [], []
        for _ in range(2):
            M, _ = variants.make_preconditioner(c["A"], v, cols)
            x, info = variants.timed_cg(c["A"], c["rhs"], M)
            xs.append(x)
            its.append(info["iterations"])
        d = float(np.max(np.abs(xs[0] - xs[1])))
        bad += d >= 1e-8
        print(f"{a.case} {v:14s} iterations {its} max difference between two runs {d:.2e} K")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
