"""!
@file study_coverage.py
@brief Does a grey-level (coverage) mask help the conduction mapping when the copper has thin tracks, compared with a binary mask at the same pixel?
@details Random boards of thin tracks (0.08 to 0.3 mm, any angle) and pads, 20 mm square, border held at 0 K, 1 W in a 6 x 6 mm block, h = 10 W/m2K. The truth is the mask drawn at 0.025 mm
         solved pixel by pixel. Candidates, all mapped to 1 mm cells: the binary mask at 0.1 mm and at 0.05 mm (centre sampling), the coverage mask at 0.1 mm (each pixel the fraction of copper from a
         4 x 4 sub-sampling, its sheet conductance the arithmetic mix of copper and laminate) and the binary mask at 0.025 mm itself. Mappings: fill fraction, geometric mean, lambda 0.5, flow-based faces.
         Run: .venv/bin/python research/gerbers/scripts/study_coverage.py (from the repository root) (about 15 minutes).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import numpy as np

import boards_synthetic as bs
import conduction as cd
import native_gerber as ng
import scenarios as sc

SIZE = 20.0
HEATER = 6.0
FINE = 0.025
SEEDS = (3, 4, 5, 6)


def mask_of(layer, pix):
    """!
    @brief Binary mask of the whole window at a pixel size.
    @param layer Parsed layer.
    @param pix Pixel size (mm).
    @return Boolean array (rows from the top).
    """
    cv = ng.Canvas(0.0, SIZE, SIZE, SIZE, pix)
    layer.draw(cv)
    return cv.mask


def main():
    """!
    @brief Run the candidates on several boards and print the tables.
    @return None.
    """
    for kind, tracks, pads, pour in (("sparse", 110, 40, False), ("dense with a pour", 320, 120, True)):
        run(kind, tracks, pads, pour)


def run(kind, tracks, pads, pour):
    """!
    @brief One family of boards.
    @param kind Label.
    @param tracks Tracks per board.
    @param pads Pads per board.
    @param pour True to add a ground pour on the left third.
    @return None (prints).
    """
    results = {}
    areas = {}
    fracs = []
    for seed in SEEDS:
        text = bs.random_board_text(seed=seed, tracks=tracks, pads=pads, size=SIZE, widths=(0.08, 0.1, 0.15, 0.3), pour=pour, max_len=8.0, holes=10)
        layer = ng.Layer(text)
        fine = mask_of(layer, FINE)
        fracs.append(fine.mean())
        Sf = cd.sheet_of(fine[::-1])
        power, fixed, heater = sc.box_scenario(Sf.shape, FINE, HEATER)
        ref = sc.pixel_reference(Sf, FINE, power, 10.0, fixed)
        for label, pix in (("binary 0.1 mm", 0.1), ("binary 0.05 mm", 0.05), ("binary 0.025 mm", 0.025), ("coverage 0.1 mm", 0.1)):
            if label.startswith("coverage"):
                cov = ng.render_coverage(layer, 0.0, SIZE, SIZE, SIZE, pix, supersample=4)
                S = cd.S_LAM + cov * (cd.S_CU - cd.S_LAM)
                area = cov.sum() * pix * pix
            else:
                m = mask_of(layer, pix)
                S = cd.sheet_of(m)
                area = m.sum() * pix * pix
            S = S[::-1] if label.startswith("coverage") else S[::-1]
            n = int(round(1.0 / pix))
            n -= n % 2
            pw, fx, ht = sc.box_scenario(S.shape, pix, HEATER)
            _, em, _ = sc.compare(S, pix, int(round(1.0 / pix)), pw, fx, 10.0, ht, a=cd.S_CU, b=cd.S_LAM, reference=(ref, FINE))
            for name, e in em.items():
                results.setdefault((label, name), []).append(e)
            areas.setdefault(label, []).append(area / (fine.sum() * FINE ** 2) - 1)
    print(f"\n{kind}: {len(SEEDS)} random thin-track boards, mean copper fraction {100 * np.mean(fracs):.1f} %, truth = the 0.025 mm mask solved pixel by pixel; error of the mean rise over the heater (MAE % and bias)")
    labels = list(dict.fromkeys(k[0] for k in results))
    names = list(dict.fromkeys(k[1] for k in results))
    print(f"{'mask':20s}" + "".join(f"{n:>26s}" for n in names) + f"{'copper area vs 0.025':>24s}")
    for lab in labels:
        row = f"{lab:20s}"
        for nm in names:
            e = np.array(results[(lab, nm)])
            row += f"{np.abs(e).mean():14.1f} ({e.mean():+7.1f})  "
        row += f"{100 * np.mean(areas[lab]):+14.1f} %"
        print(row)


if __name__ == "__main__":
    main()
