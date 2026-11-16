#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_pixels.py
@brief How many pixels per cell does the exact-fill, flow-faces reading of drawn zones need?
@details The stripes board and the plain inset board (200 and 1000 W/m2K) at cells 1, 0.5 and 0.25 mm in the FVM inside `lib/patched.use('faces')` with 2, 4, 6, 10 and 16 pixels per cell
         side, error of the heater mean against the finite-element reference of `out/fem.json` (`study_decomposition.fem_ref`) and the build-and-solve seconds.
         Run: `.venv/bin/python research/drawn-copper-faces/scripts/study_pixels.py`.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, HERE)
import dc_cases as D                                                      # noqa: E402
import patched as P                                                       # noqa: E402
import study_decomposition as SD                                          # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    for name, hs in (("stripes", 200), ("stripes", 1000), ("plain_inset", 200), ("plain_inset", 1000), ("ell", 200)):
        ref = SD.fem_ref(name, hs, 2)[1]
        p = D.problem(D.case(name, float(hs)))
        print(f"{name} h_side {hs}: reference {ref:.3f} K; error %% / seconds, pixels per cell side")
        t0 = time.time()
        row = ["program " + "  ".join(f"{c:g}mm {100 * (D.heater_mean_fvm(p, c)[0] / ref - 1):+6.2f}" for c in SD.CELLS)]
        print("   ", row[0], f"({time.time() - t0:.1f} s)")
        for n in (2, 4, 6, 10, 16):
            P.STATE["pix"] = n
            out = []
            t0 = time.time()
            with P.use("faces"):
                for c in SD.CELLS:
                    out.append(100 * (D.heater_mean_fvm(p, c)[0] / ref - 1))
            print(f"    n={n:2d}    " + "  ".join(f"{c:g}mm {e:+6.2f}" for c, e in zip(SD.CELLS, out)), f"({time.time() - t0:.1f} s)", flush=True)
        P.STATE["pix"] = P.PIX_PER_CELL


if __name__ == "__main__":
    main()
