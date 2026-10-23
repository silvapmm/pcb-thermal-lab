"""!
@file study_sampson_boundary.py
@brief Does the mapping hold in the regime where Sampson (2017) found smearing to fail: heat that must cross copper-free regions to fixed-temperature posts, with little or no convection?
@details (1) Stripes: a block of copper stripes in a laminate board, posts across or along the stripes, no convection. (2) The 42 real windows of the other studies with their whole border held
         at 0 K and a convection coefficient of 0 or 10 W/m2K. For each scenario the reference is the mask solved pixel by pixel and the error is that of the mean rise over the heater
         block for the fill fraction (smearing, what the program does today), the geometric mean, the tile method (Blackmore's lower bound), lambda 0.5 and the flow-based faces.
         Run: .venv/bin/python research/gerbers/scripts/study_sampson_boundary.py (from the repository root) (about 10 minutes, one core).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

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
    for across in (True, False):
        for pix, n in ((0.1, 10), (0.1, 5)):
            S, power, fixed, heater = sc.stripes(pix_mm=pix, across=across)
            ref, em, ex = sc.compare(S, pix, n, power, fixed, 0.0, heater)
            print(f"\nstripes, posts {'across' if across else 'along'} the stripes, no convection, cells {pix * n:.1f} mm: reference mean rise {ref:.1f} K")
            for k in em:
                print(f"  {k:26s} mean rise error {em[k]:+7.1f} %   max rise error {ex[k]:+7.1f} %")
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
