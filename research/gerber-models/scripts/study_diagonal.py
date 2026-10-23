"""!
@file study_diagonal.py
@brief Do diagonal couplings fix the diagonal copper? The track study of README 4.42 and the 42 real windows of 4.4 with a nine-point network (lib/diagonal.py: a conductance tensor per cell from four local problems) against the five-point mappings, with a five-point and a nine-point reference.
@details Part A: one track of width 0.05 to 1 mm at 0, 15, 30 and 45 degrees across a 16 x 16 mm window under a 6 x 6 mm heater (border held, 10 W/m2K), coverage mask at 0.1 mm, 1 mm cells. References: the track as a coverage mask on a 0.025 mm pixel solved with the five-point stencil (the program's) and with the nine-point stencil.
         Methods: fill fraction, lambda 0.5, flow-based faces, the numerical cell problem (all five-point), the tensor with nine-point faces and the hybrid (flow-based axial faces plus the diagonal conduction they miss). Figure of merit: the share of the track's cooling that the cells reproduce, (1 - T_track / T_none) over (1 - T_ref_track / T_ref_none), with T_none from the same cells without copper.
         Part B: the 42 windows of seven real boards (windows.py), 1 mm cells, error of the mean heater rise against each reference. Writes out/diagonal.json (used by make_figures.py).
         Run: PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal.py (from the repository root; about 15 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json

import numpy as np

import conduction as cd
import diagonal as dg
import scenarios as sc
import study_track_width_angle as st
import windows
from paths import OUT

METHODS = ("fill fraction (today)", "lambda 0.5", "flow-based faces", "cell problem", "tensor, nine-point", "flow + diagonal", "flow + diagonal 0.5", "flow + diagonal 0.25")
ANGLES = (0, 15, 30, 45)


def coarse_runs(S, pix, n, power_px, fixed_px, heater):
    """!
    @brief Heater mean of every method on cells of n x n pixels.
    @param S Pixel sheet conductances.
    @param pix Pixel (mm).
    @param n Pixels per cell side.
    @param power_px Heat per pixel (W).
    @param fixed_px Fixed pixels.
    @param heater Heater block (y0, y1, x0, x1) in pixels.
    @return dict method -> mean temperature rise of the heater (K).
    """
    a, b = cd.S_CU, cd.S_LAM
    y0, y1, x0, x1 = heater
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power_px[:cy * n, :cx * n].reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed_px, n).mean(axis=(2, 3)) >= 0.5
    faces = sc.coarse_faces(S, n, a, b)
    out = {}
    for name in METHODS[:3]:
        T = sc.solve_general(*faces[name], pix * n, pw, 10.0, fx)
        out[name] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    kx, ky = cd.map_cell_problem(cd.cell_blocks(S, n))
    T = sc.solve_general(*cd.faces_from_cells(kx, ky), pix * n, pw, 10.0, fx)
    out["cell problem"] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    kxx, kyy, kxy = dg.cell_tensor(S, n)
    T = dg.solve9(*dg.faces_from_tensor(kxx, kyy, kxy), pix * n, pw, 10.0, fx)
    out["tensor, nine-point"] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    T = dg.solve9(*dg.hybrid_faces(S, n), pix * n, pw, 10.0, fx)
    out["flow + diagonal"] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    for alpha in (0.5, 0.25):
        T = dg.solve9(*dg.hybrid_faces(S, n, alpha), pix * n, pw, 10.0, fx)
        out[f"flow + diagonal {alpha}"] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    return out


def part_a():
    """!
    @brief The track study with the two references and the five methods.
    @return dict with "widths", per width/angle the share reproduced against each reference.
    """
    res = {}
    St0 = np.full((int(st.SIZE / st.PIX_TRUTH),) * 2, cd.S_LAM)
    p_t, f_t, _ = sc.box_scenario(St0.shape, st.PIX_TRUTH, 6.0)
    ref_none = {"5": st.heater_mean(sc.pixel_reference(St0, st.PIX_TRUTH, p_t, 10.0, f_t)), "9": st.heater_mean(dg.pixel_reference9(St0, st.PIX_TRUTH, p_t, 10.0, f_t))}
    S0 = np.full((int(st.SIZE / 0.1),) * 2, cd.S_LAM)
    p0, f0, h0 = sc.box_scenario(S0.shape, 0.1, 6.0)
    none = coarse_runs(S0, 0.1, 10, p0, f0, h0)
    for w in st.WIDTHS:
        for th in ANGLES:
            layer = st.ng.Layer(st.track_text(w, th))
            _, ct = st.masks(layer, st.PIX_TRUTH)
            Sc = st.sheet(ct)
            ref = {"5": st.heater_mean(sc.pixel_reference(Sc, st.PIX_TRUTH, p_t, 10.0, f_t)), "9": st.heater_mean(dg.pixel_reference9(Sc, st.PIX_TRUTH, p_t, 10.0, f_t))}
            _, c01 = st.masks(layer, 0.1)
            S = st.sheet(c01)
            runs = coarse_runs(S, 0.1, 10, p0, f0, h0)
            rec = {"effect5": 100 * (ref["5"] / ref_none["5"] - 1), "effect9": 100 * (ref["9"] / ref_none["9"] - 1)}
            for m in METHODS:
                cell = 1 - runs[m] / none[m]
                rec[m] = {k: 100 * cell / (1 - ref[k] / ref_none[k]) for k in ("5", "9")}
            res[f"{w}/{th}"] = rec
        print(f"width {w} mm done", flush=True)
    return res


def part_b():
    """!
    @brief The 42 windows: error of the mean heater rise of every method against the five-point and the nine-point reference.
    @return dict method -> {"5": [errors], "9": [errors]}.
    """
    masks, meta = windows.load()
    res = {m: {"5": [], "9": []} for m in METHODS}
    for i, mask in enumerate(masks):
        S, power, fixed, heater = sc.window_scenario(mask)
        y0, y1, x0, x1 = heater
        ref5 = sc.pixel_reference(S, windows.PIX, power, 10.0, fixed)[y0:y1, x0:x1].mean()
        ref9 = dg.pixel_reference9(S, windows.PIX, power, 10.0, fixed)[y0:y1, x0:x1].mean()
        runs = coarse_runs(S, windows.PIX, 10, power, fixed, heater)
        for m in METHODS:
            res[m]["5"].append(100 * (runs[m] / ref5 - 1))
            res[m]["9"].append(100 * (runs[m] / ref9 - 1))
        if i % 10 == 9:
            print(f"window {i + 1} of {len(masks)}", flush=True)
    return res


def main():
    """!
    @brief Run both parts, print the tables and save out/diagonal.json.
    @return None.
    """
    a = part_a()
    b = part_b()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagonal.json").write_text(json.dumps({"a": a, "b": b}, indent=1))
    report({"a": a, "b": b})


def report(d):
    """!
    @brief Print the tables from the results.
    @param d Dict with "a" and "b" (main() or out/diagonal.json).
    @return None.
    """
    a, b = d["a"], d["b"]
    for ref in ("9", "5"):
        print(f"\nPart A: share of the track's cooling reproduced by the 1 mm cells (%), reference with the {'nine' if ref == '9' else 'five'}-point stencil on the 0.025 mm pixel; columns = angle 0 / 15 / 30 / 45 degrees")
        print(f"{'width mm':>9s}" + "".join(f"{m[:22]:>40s}" for m in METHODS))
        for w in st.WIDTHS:
            print(f"{w:9.3f}" + "".join("  " + " ".join(f"{a[f'{w}/{th}'][m][ref]:6.0f}" for th in ANGLES) for m in METHODS))
    print("\nwhat the track does to the reference heater (%): five-point / nine-point, at 0 / 45 degrees")
    for w in st.WIDTHS:
        print(f"{w:9.3f}  0 deg {a[f'{w}/0']['effect5']:+6.1f} / {a[f'{w}/0']['effect9']:+6.1f}   45 deg {a[f'{w}/45']['effect5']:+6.1f} / {a[f'{w}/45']['effect9']:+6.1f}")
    print("\nPart B: 42 real windows, 1 mm cells, error of the mean heater rise (%): mean absolute error (bias) against the five-point reference and the nine-point reference")
    for m in METHODS:
        e5, e9 = np.array(b[m]["5"]), np.array(b[m]["9"])
        print(f"{m:24s} five-point {np.abs(e5).mean():5.2f} ({e5.mean():+5.2f})   nine-point {np.abs(e9).mean():5.2f} ({e9.mean():+5.2f})   worst {np.abs(e9).max():5.1f}")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--report"]:
        report(json.loads((OUT / "diagonal.json").read_text()))
    else:
        main()
