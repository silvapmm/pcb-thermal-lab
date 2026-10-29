#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sampson_boundary.py
@brief Does the mapping hold in the regime where Sampson (2017) found smearing to fail: heat that must cross copper-free regions to fixed-temperature posts, with little or no convection?
@details (1) Stripes: a block of copper stripes (0.5 or 0.3 mm wide, 1 mm pitch) in a 36 mm laminate board, posts of 3 x 6 mm held at 0 K at the middle of two opposite edges, across or along
         the stripes, no convection, in two set-ups: a 34 mm block whose stripes run under the posts (README 4.25 and `tests/test_claims.py`) and a 24 mm block that stops 3 mm short of them
         (a keep-out, Sampson's case). (2) The 42 real windows of the other studies with their whole border held at 0 K and a convection coefficient of 0 or 10 W/m2K. For each scenario the reference is the mask solved pixel by pixel and the error is that of the mean rise over the heater
         block for the fill fraction (smearing, what the program does today), the geometric mean, the tile method (Blackmore's lower bound), lambda 0.5 and the flow-based faces.
         Run: .venv/bin/python research/gerber-models/scripts/study_sampson_boundary.py [--stripes] (from the repository root; about 1 minute on a quiet machine; --stripes runs part (1) only, 10 s).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import sys

import numpy as np

import scenarios as sc
import windows


def report(title, rows):
    """!
    @brief Print one table of mean absolute errors.
    @param title Heading.
    @param rows List of dicts name -> error % (one dict per case).
    @return None.
    """
    print(f"\n{title}")
    for name in rows[0]:
        e = np.array([r[name] for r in rows])
        print(f"  {name:26s} MAE {np.abs(e).mean():6.1f} %  (bias {e.mean():+6.1f} %, worst {np.abs(e).max():6.1f} %)")


def main():
    """!
    @brief Run both scenario families and print the tables.
    @return None.
    """
    # the 34 mm block reaches under the 3 mm deep posts (the case of the README table and of the claim test); the 24 mm block leaves 3 mm of bare laminate before them
    for block_mm, setup in ((34.0, "stripes under the posts (34 mm block)"), (24.0, "stripes stopping 3 mm short of the posts (24 mm block)")):
        for stripe_px in (5, 3):
            for across in (True, False):
                for pix, n in ((0.1, 10), (0.1, 5)):
                    S, power, fixed, heater = sc.stripes(pix_mm=pix, across=across, copper_mm=block_mm, stripe_px=stripe_px, pitch_px=10)
                    ref, em, ex = sc.compare(S, pix, n, power, fixed, 0.0, heater)
                    print(f"\n{setup}, {stripe_px * pix:.1f} mm stripes, posts {'across' if across else 'along'} the stripes, no convection, cells {pix * n:.1f} mm: reference mean rise {ref:.1f} K")
                    for k in em:
                        print(f"  {k:26s} mean rise error {em[k]:+7.1f} %   max rise error {ex[k]:+7.1f} %")
    if "--stripes" in sys.argv:
        return
    masks, meta = windows.load()
    for h in (0.0, 10.0):
        rm, rx = [], []
        for m in masks:
            S, power, fixed, heater = sc.window_scenario(m)
            ref, em, ex = sc.compare(S, 0.1, 10, power, fixed, h, heater)
            rm.append(em); rx.append(ex)
        report(f"42 real windows, border held at 0 K, h = {h} W/m2K, 1 mm cells: error of the mean rise over the heater", rm)
        report(f"  same, error of the maximum rise", rx)


if __name__ == "__main__":
    main()
