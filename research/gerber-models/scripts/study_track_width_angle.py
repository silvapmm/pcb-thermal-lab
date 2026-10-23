"""!
@file study_track_width_angle.py
@brief What is the thinnest track the chain recognises, and does it handle any angle? One track of width w at angle theta crosses a 16 x 16 mm window under a 6 x 6 mm heater; the heater temperature from the 1 mm cells (four mappings, four input masks) against a resolved reference.
@details Reference: the track drawn as a coverage mask (sub-pixel area, 4 x 4 samples) on a 0.025 mm pixel and solved pixel by pixel (border ring of 1 mm held at 0 K, 1 W in the heater, 10 W/m2K on both faces). Inputs to the 1 mm cells: the binary mask and the coverage mask at 0.1 mm and at 0.05 mm.
         Mappings: the fill fraction (the program today), the geometric mean, lambda 0.5 and the flow-based faces. Widths 0.05 to 1.0 mm, angles 0, 15, 30 and 45 degrees (the board is symmetric, so 60, 75 and 90 repeat 30, 15 and 0).
         Also reported, for the binary mask at 0.1 mm and 0.05 mm: the copper area against the exact area and whether the track stays in one 8-connected piece (what the reader and the pixel "recognise").
         Writes out/track_width_angle.json (used by make_figures.py); `--report` prints the tables again from it. Run: PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_track_width_angle.py (from the repository root; about 5 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json
import math
import sys

import numpy as np
from scipy import ndimage

import native_gerber as ng
import scenarios as sc
import conduction as cd
from boards_synthetic import HEAD, mm
from paths import OUT

SIZE = 16.0
WIDTHS = (0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)
ANGLES = (0, 15, 30, 45)
METHODS = ("fill fraction (today)", "geometric mean", "lambda 0.5", "flow-based faces", "flow-based, margin 20 %")
PIX_TRUTH = 0.025


def track_text(w, theta):
    """!
    @brief Gerber text of one track of width w through the centre of the window at an angle.
    @param w Width (mm).
    @param theta Angle (degrees).
    @return str Gerber text.
    """
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    h = SIZE
    x0, y0, x1, y1 = SIZE / 2 - h * c, SIZE / 2 - h * s, SIZE / 2 + h * c, SIZE / 2 + h * s
    return HEAD + f"%ADD10C,{w}*%\nD10*\nX{mm(x0)}Y{mm(y0)}D02*\nX{mm(x1)}Y{mm(y1)}D01*\nM02*\n"


def masks(layer, pix):
    """!
    @brief Binary and coverage masks of the window at a pixel.
    @param layer Parsed layer.
    @param pix Pixel (mm).
    @return tuple (binary bool, coverage float), rows from the top.
    """
    cv = ng.Canvas(0.0, SIZE, SIZE, SIZE, pix)
    layer.draw(cv)
    return cv.mask, ng.render_coverage(layer, 0.0, SIZE, SIZE, SIZE, pix, 4)


def sheet(mask):
    """!
    @brief Pixel sheet conductance of a binary or coverage mask (copper over laminate, arithmetic inside a pixel).
    @param mask Mask in 0..1.
    @return numpy.ndarray Sheet conductance (W/K).
    """
    return cd.S_LAM + mask.astype(float) * (cd.S_CU - cd.S_LAM)


def heater_mean(field):
    """!
    @brief Mean of a pixel field over the 6 x 6 mm heater block at the centre of the window.
    @param field Temperature rise on the 0.025 mm pixel grid.
    @return float Mean (K).
    """
    k = int(round(6.0 / PIX_TRUTH))
    y0 = (field.shape[0] - k) // 2
    return float(field[y0:y0 + k, y0:y0 + k].mean())


def baseline():
    """!
    @brief The reference heater temperature with no copper at all (laminate only) and the error of the 1 mm cells on it: the grid itself, not the mapping.
    @return tuple (reference mean rise K, error % of the 1 mm cells).
    """
    St = np.full((int(SIZE / PIX_TRUTH),) * 2, cd.S_LAM)
    power, fixed, _ = sc.box_scenario(St.shape, PIX_TRUTH, 6.0)
    ref = sc.pixel_reference(St, PIX_TRUTH, power, 10.0, fixed)
    S = np.full((int(SIZE / 0.1),) * 2, cd.S_LAM)
    p, f, heater = sc.box_scenario(S.shape, 0.1, 6.0)
    _, em, _ = sc.compare(S, 0.1, 10, p, f, 10.0, heater, a=cd.S_CU, b=cd.S_LAM, reference=(ref, PIX_TRUTH))
    return heater_mean(ref), em["fill fraction (today)"]


def one(w, theta, ref_none):
    """!
    @brief One track: the reference and the errors of every mapping from each input mask.
    @param w Width (mm).
    @param theta Angle (degrees).
    @param ref_none Reference heater rise with no copper (K), from baseline().
    @return dict with "errors" (input -> method -> %), "area" (pix -> % error of the binary area) and "pieces" (pix -> number of 8-connected pieces).
    """
    layer = ng.Layer(track_text(w, theta))
    bt, ct = masks(layer, PIX_TRUTH)
    St = sheet(ct)
    power, fixed, _ = sc.box_scenario(St.shape, PIX_TRUTH, 6.0)
    ref = sc.pixel_reference(St, PIX_TRUTH, power, 10.0, fixed)
    exact = ct.sum() * PIX_TRUTH ** 2
    res = {"errors": {}, "area": {}, "pieces": {}, "effect": 100 * (heater_mean(ref) / ref_none - 1)}
    for pix in (0.1, 0.05):
        b, c = masks(layer, pix)
        n = int(round(1.0 / pix))
        for kind, m in (("binary", b), ("coverage", c)):
            S = sheet(m)
            p, f, heater = sc.box_scenario(S.shape, pix, 6.0)
            _, em, _ = sc.compare(S, pix, n, p, f, 10.0, heater, a=cd.S_CU, b=cd.S_LAM, reference=(ref, PIX_TRUTH))
            res["errors"][f"{kind} {pix}"] = {k: em[k] for k in METHODS}
        res["area"][str(pix)] = 100 * (b.sum() * pix ** 2 / exact - 1)
        res["pieces"][str(pix)] = int(ndimage.label(b, structure=np.ones((3, 3)))[1])
    return res


def capture(data, key, method, w, theta):
    """!
    @brief The share of the cooling that the track causes in the reference that the 1 mm cells reproduce.
    @details The reference heater rise falls by `effect` % when the track is added; the cells (whose laminate-only error is the grid error g) give T_cells = (1 + error) T_reference; the share is (1 - T_cells_track / T_cells_none) over the reference effect.
    @param data Results of main().
    @param key Input mask, for example "coverage 0.1".
    @param method Mapping name.
    @param w Width (mm).
    @param theta Angle (degrees).
    @return float Share in % (100 = the track is fully felt).
    """
    g = data["_baseline"]["grid_error_pct"] / 100
    r = data[f"{w}/{theta}"]
    eff = r["effect"] / 100
    t_cells = (1 + r["errors"][key][method] / 100) * (1 + eff)
    return 100 * (1 - t_cells / (1 + g)) / (-eff)


def report(data):
    """!
    @brief Print the tables of the study from its results.
    @param data Results of main() (also read from out/track_width_angle.json with --report).
    @return None.
    """
    for key in ("coverage 0.1", "binary 0.1", "coverage 0.05"):
        print(f"\nerror of the heater temperature (%) from the 1 mm cells, input {key}; rows = width, columns = angle 0 / 15 / 30 / 45 degrees")
        print(f"{'width mm':>9s}" + "".join(f"{m[:18]:>38s}" for m in METHODS))
        for w in WIDTHS:
            row = f"{w:9.3f}"
            for m in METHODS:
                row += "  " + " ".join(f"{data[f'{w}/{th}']['errors'][key][m]:+7.1f}" for th in ANGLES)
            print(row)
    print("\nwhat the track does to the heater (reference, % against no copper); columns = angle 0 / 15 / 30 / 45 degrees")
    for w in WIDTHS:
        print(f"{w:9.3f}  " + " ".join(f"{data[f'{w}/{th}']['effect']:+7.1f}" for th in ANGLES))
    print("\nbinary mask: copper area error (%) and 8-connected pieces (1 = the track is one piece), pixel 0.1 mm and 0.05 mm; angles 0 / 15 / 30 / 45")
    for w in WIDTHS:
        a1 = " ".join(f"{data[f'{w}/{th}']['area']['0.1']:+7.1f}" for th in ANGLES)
        p1 = "/".join(str(data[f"{w}/{th}"]["pieces"]["0.1"]) for th in ANGLES)
        a2 = " ".join(f"{data[f'{w}/{th}']['area']['0.05']:+7.1f}" for th in ANGLES)
        p2 = "/".join(str(data[f"{w}/{th}"]["pieces"]["0.05"]) for th in ANGLES)
        print(f"{w:9.3f}  0.1 mm: area {a1}  pieces {p1:>12s}   0.05 mm: area {a2}  pieces {p2:>12s}")

    print("\nshare of the cooling caused by the track that the 1 mm cells reproduce (%), coverage mask at 0.1 mm; columns = angle 0 / 15 / 30 / 45 degrees (100 = the track is fully felt)")
    print(f"{'width mm':>9s}" + "".join(f"{m[:18]:>38s}" for m in METHODS))
    for w in WIDTHS:
        row = f"{w:9.3f}"
        for m in METHODS:
            row += "  " + " ".join(f"{capture(data, 'coverage 0.1', m, w, th):7.0f}" for th in ANGLES)
        print(row)


def main():
    """!
    @brief Run all widths and angles, print the tables and save out/track_width_angle.json.
    @return None.
    """
    ref_none, grid_error = baseline()
    print(f"no copper: the heater rises {ref_none:.1f} K; the 1 mm cells overestimate it by {grid_error:.2f} % (the grid, not the mapping)")
    data = {"_baseline": {"ref_none_K": ref_none, "grid_error_pct": grid_error}}
    for w in WIDTHS:
        for th in ANGLES:
            data[f"{w}/{th}"] = one(w, th, ref_none)
        print(f"width {w} mm done", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "track_width_angle.json").write_text(json.dumps(data, indent=1))
    report(data)


if __name__ == "__main__":
    if sys.argv[1:] == ["--report"]:
        report(json.loads((OUT / "track_width_angle.json").read_text()))
    else:
        main()
