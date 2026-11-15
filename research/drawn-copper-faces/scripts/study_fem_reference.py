#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_reference.py
@brief Question: what is the heater mean rise of the synthetic boards of the drawn-copper study, with the copper resolved, in an independent finite-element solution?
@details Run from the repository root with the interpreter of the scratch environment that holds scikit-fem and pyamg (see `research/independent-fem-edge/README.md`; the
         environment is NOT in git): `<fem-python> research/drawn-copper-faces/scripts/study_fem_reference.py <case> <h_side> <layers> <hf mm>`. Results are cached in
         `research/drawn-copper-faces/out/fem.json` (git-ignored) under the key `case|h_side|layers|hf`. One solve at a time, each under 2 GB.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import dc_cases as D                                                      # noqa: E402
import dc_fem                                                             # noqa: E402

OUT = os.path.join(HERE, "..", "out", "fem.json")


def main():
    """!
    @brief Solve one case and add it to the cache.
    @return None.
    """
    name, hs, layers, hf = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
    key = f"{name}|{hs:g}|{layers}|{hf:g}"
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if key in res:
        print(key, "cached", res[key])
        return
    t0 = time.time()
    r = dc_fem.solve(D.case(name, hs, layers), hf)
    if r is None:
        print(key, "refused: above 2 GB")
        return
    r["seconds"] = time.time() - t0
    res[key] = r
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print(key, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)


if __name__ == "__main__":
    main()
