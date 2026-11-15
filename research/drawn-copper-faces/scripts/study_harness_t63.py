#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_t63.py
@brief The times to 63 % of the frozen-number boards (FVM and FDM, 1 mm) with the program as it is and with the zones read as an import (the copy of `lib/patched.py`).
@details Uses `regress_harness.t63` (the same short transient as the frozen numbers). Prints the boards whose time or steady resistance moves by more than 1e-6 relative.
         Run: `.venv/bin/python research/drawn-copper-faces/scripts/study_harness_t63.py`.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)


def main():
    """!
    @brief Run and print.
    @return None.
    """
    import regress_boards as B
    import regress_harness as H
    import patched as P
    n = moved = 0
    for name in B.board_names():
        prob = B.build(name)
        if not prob.heaters:
            continue
        for model in ("fvm", "fdm"):
            a = H.t63(prob, model)
            with P.use("faces"):
                b = H.t63(prob, model)
            if a["status"] != "ok" or b["status"] != "ok":
                print(f"{name}|{model}: {a['status']} / {b['status']}")
                continue
            for pa, pb in zip(a["parts"], b["parts"]):
                n += 1
                if pa["t63_s"] is None or pb["t63_s"] is None:
                    continue
                dt, dr = pb["t63_s"] / pa["t63_s"] - 1, pb["rth"] / pa["rth"] - 1
                if abs(dt) > 1e-6 or abs(dr) > 1e-6:
                    moved += 1
                    print(f"{name}|{model} part {pa['name']}: t63 {pa['t63_s']:.3f} -> {pb['t63_s']:.3f} s ({100 * dt:+.3f} %), rth {pa['rth']:.4f} -> {pb['rth']:.4f} K/W ({100 * dr:+.3f} %)", flush=True)
    print(f"{n} part curves compared, {moved} move by more than 1e-6 relative")


if __name__ == "__main__":
    main()
