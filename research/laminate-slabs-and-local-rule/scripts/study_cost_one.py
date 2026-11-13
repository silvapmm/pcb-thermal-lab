#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cost_one.py
@brief Wall time and peak resident memory of ONE run of a thick-laminate case with a given rule, in a fresh process (item A cost, README 3.4).
@details Usage (repository root): .venv/bin/python research/laminate-slabs-and-local-rule/scripts/study_cost_one.py S t pad rule   with rule one of default, g16, l6.
         Prints one line: unknowns, seconds, peak resident GB (ru_maxrss), R'. Run each rule in its own process; do not run it above 2 GB while a battery runs.
"""

import resource
import sys

import _boot26

import s2board as B


def main(argv=None):
    """!
    @brief Run one case and print the cost.
    @param argv S (mm), t (mm), pad (0 or 1), rule.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    S, t, pad, rule = float(argv[0]), float(argv[1]), bool(int(argv[2])), argv[3]
    kw = {"default": {}, "g16": dict(s_max=0.1, n_max=16), "l6": dict(local=dict(trigger=0.05, target=0.05, n_cap=16))}[rule]
    r, n, dt = B.run(B.case(S, t), pad, 0.25, **kw)
    gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9               # bytes on macOS
    print(f"S{S:g} t{t:g} {'pad' if pad else 'bare'} {rule:8s} unknowns {n:7d}  {dt:6.2f} s  peak {gb:5.2f} GB  R' {r:.3f}")


if __name__ == "__main__":
    main()
