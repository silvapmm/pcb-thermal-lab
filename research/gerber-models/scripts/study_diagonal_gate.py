#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_diagonal_gate.py
@brief A detector of the cells that should get diagonal faces: the hybrid network of README 4.44 adds the diagonal conduction a fixed share alpha in every cell; here the share is decided cell by cell from the cell's own conductance tensor, and the result is compared with the fixed shares on the track study and on the 42 real windows.
@details The cell tensor (kxx, kyy, kxy) comes from the cell problem (diagonal.cell_tensor). Coherence is |kxy| / mean(kxx, kyy): zero for a uniform cell, a crossing of two diagonals or an axis-aligned conductor, large when one diagonal conductor dominates (a track at 45 degrees). The principal axis lies between 22.5 and 67.5 degrees of the x axis when |2 kxy| exceeds |kxx - kyy|. The gates tried: a smooth ramp of the coherence between two thresholds, with and without the principal-axis condition. The references are those of study_diagonal.py (the pixel network with the five-point and the nine-point stencil on the 0.025 mm pixel for the tracks and on the 0.1 mm pixel for the windows). Part A uses the widths and the angles 0 and 45 degrees of the track study; part B the 42 windows. Writes out/diagonal_gate.json.
         Run: PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_gate.py (from the repository root; about 15 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json

import numpy as np

import conduction as cd
import diagonal as dg
import scenarios as sc
import study_diagonal as sd
import study_track_width_angle as st
import windows
from paths import OUT

GATES = {
    "fixed 1.0": lambda kxx, kyy, kxy: np.ones_like(kxx),
    "fixed 0.5": lambda kxx, kyy, kxy: np.full_like(kxx, 0.5),
    "coherence ramp 0.05 to 0.25": lambda kxx, kyy, kxy: np.clip((np.abs(kxy) / (0.5 * (kxx + kyy)) - 0.05) / 0.20, 0, 1),
    "coherence ramp 0.10 to 0.40": lambda kxx, kyy, kxy: np.clip((np.abs(kxy) / (0.5 * (kxx + kyy)) - 0.10) / 0.30, 0, 1),
    "ramp 0.05 to 0.25, axis 22.5 to 67.5": lambda kxx, kyy, kxy: np.clip((np.abs(kxy) / (0.5 * (kxx + kyy)) - 0.05) / 0.20, 0, 1) * (np.abs(2 * kxy) > np.abs(kxx - kyy)),
    "ramp 0.10 to 0.40, axis 22.5 to 67.5": lambda kxx, kyy, kxy: np.clip((np.abs(kxy) / (0.5 * (kxx + kyy)) - 0.10) / 0.30, 0, 1) * (np.abs(2 * kxy) > np.abs(kxx - kyy)),
}


def gated_runs(S, pix, n, power_px, fixed_px, heater):
    """!
    @brief The mean heater rise of the flow-based network without diagonals and of the hybrid with every gate.
    @param S Pixel sheet conductances.
    @param pix Pixel (mm).
    @param n Pixels per cell side.
    @param power_px Heat per pixel (W).
    @param fixed_px Fixed pixels.
    @param heater Heater block (y0, y1, x0, x1) in pixels.
    @return dict name -> mean temperature rise (K).
    """
    y0, y1, x0, x1 = heater
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power_px[:cy * n, :cx * n].reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed_px, n).mean(axis=(2, 3)) >= 0.5
    out = {}
    gx, gy = cd.dual_faces(S, n, 0)
    T = dg.solve9(*dg.faces5_as9(gx, gy), pix * n, pw, 10.0, fx)
    out["flow-based, no diagonals"] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    for name, gate in GATES.items():
        T = dg.solve9(*dg.hybrid_faces(S, n, gate=gate), pix * n, pw, 10.0, fx)
        out[name] = T[y0 // n:y1 // n, x0 // n:x1 // n].mean()
    return out


def part_a():
    """!
    @brief The track study at 0 and 45 degrees: the share of the track's cooling each variant reproduces against the nine-point pixel reference.
    @return dict width/angle -> variant -> share (%).
    """
    res = {}
    St0 = np.full((int(st.SIZE / st.PIX_TRUTH),) * 2, cd.S_LAM)
    p_t, f_t, _ = sc.box_scenario(St0.shape, st.PIX_TRUTH, 6.0)
    ref_none = st.heater_mean(dg.pixel_reference9(St0, st.PIX_TRUTH, p_t, 10.0, f_t))
    S0 = np.full((int(st.SIZE / 0.1),) * 2, cd.S_LAM)
    p0, f0, h0 = sc.box_scenario(S0.shape, 0.1, 6.0)
    none = gated_runs(S0, 0.1, 10, p0, f0, h0)
    for w in st.WIDTHS:
        for th in (0, 45):
            layer = st.ng.Layer(st.track_text(w, th))
            _, ct = st.masks(layer, st.PIX_TRUTH)
            ref = st.heater_mean(dg.pixel_reference9(st.sheet(ct), st.PIX_TRUTH, p_t, 10.0, f_t))
            _, c01 = st.masks(layer, 0.1)
            runs = gated_runs(st.sheet(c01), 0.1, 10, p0, f0, h0)
            res[f"{w}/{th}"] = {m: 100 * (1 - runs[m] / none[m]) / (1 - ref / ref_none) for m in runs}
        print(f"track width {w} mm done", flush=True)
    return res


def part_b():
    """!
    @brief The 42 real windows: error of the mean heater rise of every variant against the nine-point pixel reference.
    @return dict variant -> list of errors (%).
    """
    masks, meta = windows.load()
    res = {}
    for i, mask in enumerate(masks):
        S, power, fixed, heater = sc.window_scenario(mask)
        y0, y1, x0, x1 = heater
        ref9 = dg.pixel_reference9(S, windows.PIX, power, 10.0, fixed)[y0:y1, x0:x1].mean()
        for m, v in gated_runs(S, windows.PIX, 10, power, fixed, heater).items():
            res.setdefault(m, []).append(100 * (v / ref9 - 1))
        if i % 10 == 9:
            print(f"window {i + 1} of {len(masks)}", flush=True)
    return res


def main():
    """!
    @brief Run both parts, print the tables and write the results.
    @return None.
    """
    b = part_b()
    print("\nPart B, 42 windows, error of the mean heater rise against the nine-point reference: mean absolute error (bias)")
    for m, v in b.items():
        print(f"  {m:40s} {np.mean(np.abs(v)):5.2f} ({np.mean(v):+5.2f})   worst {np.max(np.abs(v)):5.1f}")
    a = part_a()
    print("\nPart A, share of the track's cooling reproduced (%), widths " + str(list(st.WIDTHS)) + ", at 0 / 45 degrees")
    for m in next(iter(a.values())):
        print(f"  {m:40s} " + "  ".join(f"{a[f'{w}/0'][m]:4.0f}/{a[f'{w}/45'][m]:4.0f}" for w in st.WIDTHS))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagonal_gate.json").write_text(json.dumps({"a": a, "b": b}, indent=1))


if __name__ == "__main__":
    main()
