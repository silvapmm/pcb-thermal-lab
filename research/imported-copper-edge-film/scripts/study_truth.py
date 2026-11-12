#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_truth.py
@brief The 3D truth (`lib/truth3d.py`) of the heater rise of the 20 mm board for the edge coefficients and layer counts of the study, extrapolated in the cell and in the laminate slabs.
@details For every (layers, inset, h_side) three solves (cell mm, sub-slabs per gap): (0.2, nz/2), (0.1, nz/2), (0.1, nz) with nz = 24 (2 layers) or 12 (4 layers; the gaps are 0.49 mm).
         Extrapolation (a geometric series whose ratio was measured on the 2-layer board at 200 W/m2K: the cell steps 0.4, 0.2, 0.1 mm gave -0.382, -0.142 K, ratio 0.37, the slab counts
         4, 6, 12, 24 gave -0.231, -0.199, -0.077 K with the last ratio 0.39): truth = T(0.1, nz) + 0.64 (T(0.1, nz) - T(0.1, nz/2)) + 0.59 (T(0.1, nz/2) - T(0.2, nz/2)). The size of the
         two corrections is printed with the values, so the reader sees the uncertainty (about 0.1 to 0.15 % of the rise).
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_truth.py <layers> <inset mm> <h_side list>`; writes/merges `lib/truth_values.json`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "lib")
sys.path.insert(0, LIB)

import truth3d                                                                 # noqa: E402


def truth(layers, inset_mm, h_side):
    """!
    @brief Extrapolated 3D truth of the mean heater rise.
    @param layers Copper layers.
    @param inset_mm Copper inset from the wall in mm.
    @param h_side Edge coefficient W/m2K.
    @return Dict with the three solves, the estimate and the balance errors.
    """
    nz = 24 if layers == 2 else 12
    a = truth3d.solve(h_side, 0.2, nz // 2, inset=inset_mm * 1e-3, layers=layers)
    b = truth3d.solve(h_side, 0.1, nz // 2, inset=inset_mm * 1e-3, layers=layers)
    c = truth3d.solve(h_side, 0.1, nz, inset=inset_mm * 1e-3, layers=layers)
    est = c[0] + 0.64 * (c[0] - b[0]) + 0.59 * (b[0] - a[0])
    return {"solves": {"0.2/%d" % (nz // 2): a[0], "0.1/%d" % (nz // 2): b[0], "0.1/%d" % nz: c[0]}, "truth": est, "dz": 0.64 * (c[0] - b[0]), "dxy": 0.59 * (b[0] - a[0]),
            "balance": max(abs(a[2]), abs(b[2]), abs(c[2]))}


def main():
    """!
    @brief Compute and store the truths asked for.
    @return None.
    """
    layers, inset = int(sys.argv[1]), float(sys.argv[2])
    path = os.path.join(LIB, "truth_values.json")
    data = json.load(open(path)) if os.path.exists(path) else {}
    for h in [float(x) for x in sys.argv[3].split(",")]:
        r = truth(layers, inset, h)
        data[f"{layers}|{inset}|{h}"] = r
        print(layers, inset, h, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
        json.dump(data, open(path, "w"), indent=1)


if __name__ == "__main__":
    main()
