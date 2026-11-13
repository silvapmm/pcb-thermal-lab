#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fv_refs.py
@brief The cell-centred finite-volume references of the repository on the boards of the comparison: `research/strong-edge-laminate/lib/ref3d.py` (plate, copper inset,
       resolved-cylinder via) at 1/4 and 1/8 mm with 8 slabs per gap, and the stored truths of `research/imported-copper-edge-film/lib/truth_values.json` and
       `truth_values_drawn.json` (squares and T).
@details Run from the repository root: `.venv/bin/python research/independent-fem-edge/scripts/study_fv_refs.py`. The reference code is imported as it is (nothing modified). Results in
         `research/independent-fem-edge/out/fv.json`. The 1/8 mm solves have 89 600 unknowns (7-point stencil, direct solver, about 1.5 GB); one at a time.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research", "strong-edge-laminate", "lib"))
OUT = os.path.join(os.path.dirname(HERE), "out", "fv.json")
TRUTH = os.path.join(ROOT, "research", "imported-copper-edge-film", "lib")


def main():
    """!
    @brief Run ref3d and copy the stored truths.
    @return None.
    """
    import ref3d
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for dx in (0.25e-3, 0.125e-3):
        for h in (10.0, 200.0, 1000.0):
            for d, inset in ((None, 0.0), (None, 0.5e-3), (0.16e-3, 0.0), (3.0e-3, 0.0)):
                if d is not None and h == 10.0:
                    continue
                key = f"{h}|{d}|{inset}|{dx}"
                if key in res:
                    continue
                t = time.time()
                kw = dict(via="none") if d is None else dict(via="cyl", via_dist=d)
                r = ref3d.solve(h, 8, dx, inset=inset, **kw)
                res[key] = r
                print(key, round(r["tmax"], 5), r["balance"], r["n"], f"{time.time() - t:.0f} s", flush=True)
                json.dump(res, open(OUT, "w"), indent=1)
    tv = json.load(open(os.path.join(TRUTH, "truth_values.json")))
    for h in (10.0, 200.0, 1000.0):
        res[f"truth|sq_in|{h}"] = tv[f"2|1.2|{h}"]["truth"]
    tc = json.load(open(os.path.join(TRUTH, "truth_values_drawn.json")))
    for name in ("sq_wall|200.0", "sq_wall|1000.0", "T_wall|200.0"):
        res[f"truth|{name}"] = tc[name]["truth"]
    json.dump(res, open(OUT, "w"), indent=1)
    print({k: v for k, v in res.items() if k.startswith("truth")})


if __name__ == "__main__":
    main()
