#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_coverage_real.py
@brief The coverage mask against the binary mask on real copper: 20 mm windows of the downloaded boards, truth = the 0.025 mm mask solved pixel by pixel.
@details Same protocol as study_coverage.py (border held at 0 K, 1 W in a 6 x 6 mm block, h = 10 W/m2K, 1 mm cells) but the copper is the real top layer of the boards of the other studies:
         three windows per board whose heater block has between 15 % and 90 % of copper. Run: .venv/bin/python research/gerber-models/scripts/study_coverage_real.py (from the repository root) (about 20 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import numpy as np

import conduction as cd
import native_gerber as ng
import readers
import scenarios as sc

SIZE, HEATER, FINE = 20.0, 6.0, 0.025
BOARDS = ["storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz"]


def pick(board, rng, count=3):
    """!
    @brief Random window positions of a board with enough copper under the heater.
    @param board Board key.
    @param rng Random generator.
    @param count Windows wanted.
    @return List of (layer, x_left, y_top).
    """
    files = readers.board_files(board)
    layer = ng.Layer(files["F"].read_text(errors="replace"))
    x0, y0, x1, y1 = readers.box(files.get("edge"), files["F"])
    out = []
    for _ in range(400):
        if len(out) == count:
            break
        xl, yt = rng.uniform(x0, x1 - SIZE), rng.uniform(y0 + SIZE, y1)
        cov = ng.render_coverage(layer, xl, yt, SIZE, SIZE, 0.1, supersample=1)
        c = cov[int(7 / 0.1):int(13 / 0.1), int(7 / 0.1):int(13 / 0.1)].mean()
        if 0.15 < c < 0.9 and cov.mean() > 0.15:
            out.append((layer, xl, yt))
    return out


def main():
    """!
    @brief Run the windows and print the table.
    @return None.
    """
    rng = np.random.default_rng(5)
    res = {}
    for b in BOARDS:
        for layer, xl, yt in pick(b, rng):
            fine = ng.render_coverage(layer, xl, yt, SIZE, SIZE, FINE, supersample=1) > 0.5
            Sf = cd.sheet_of(fine[::-1])
            power, fixed, _ = sc.box_scenario(Sf.shape, FINE, HEATER)
            ref = sc.pixel_reference(Sf, FINE, power, 10.0, fixed)
            for label, pix, cover in (("binary 0.1 mm", 0.1, False), ("coverage 0.1 mm", 0.1, True)):
                if cover:
                    cov = ng.render_coverage(layer, xl, yt, SIZE, SIZE, pix, supersample=4)
                    S = (cd.S_LAM + cov * (cd.S_CU - cd.S_LAM))[::-1]
                else:
                    S = cd.sheet_of((ng.render_coverage(layer, xl, yt, SIZE, SIZE, pix, supersample=1) > 0.5)[::-1])
                pw, fx, ht = sc.box_scenario(S.shape, pix, HEATER)
                _, em, _ = sc.compare(S, pix, int(round(1.0 / pix)), pw, fx, 10.0, ht, a=cd.S_CU, b=cd.S_LAM, reference=(ref, FINE))
                for name, e in em.items():
                    res.setdefault((label, name), []).append(e)
    print(f"{len(next(iter(res.values())))} real windows of 20 mm, truth = the 0.025 mm mask solved pixel by pixel; error of the mean rise over the heater, MAE % (bias)")
    names = list(dict.fromkeys(n for _, n in res))
    print(f"{'mask':18s}" + "".join(f"{n:>26s}" for n in names))
    for lab in ("binary 0.1 mm", "coverage 0.1 mm"):
        row = f"{lab:18s}"
        for n in names:
            e = np.array(res[(lab, n)])
            row += f"{np.abs(e).mean():12.1f} ({e.mean():+7.1f})  "
        print(row)


if __name__ == "__main__":
    main()
