#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file onesheet.py
@brief Windows cut from the top copper of real boards and the one-sheet comparison of the copper mappings against a pixel reference (five-point and nine-point), at a finer pixel than the earlier studies.
@details The one-sheet physics is that of research/gerber-models (a conducting sheet of copper on laminate, both faces losing heat with h = 10 W/m2K, a held border, a square heater): it isolates the
         MAPPING from the rest of the program. The earlier studies used a 0.1 mm pixel; here the pixel is 0.05 mm for the reference (so that tracks of 0.1 mm are 2 pixels wide and the 0.1 mm clearances of
         modern boards are resolved) and the cells are 0.5 and 1.0 mm. The nine-point reference (axial 2/3 and diagonal 1/6 weights) is closer to the continuum than the five-point one on tilted thin copper
         (research/gerber-models README 4.44). The window selection copies research/gerber-models windows.py (36 mm, a 6 mm heater block 15 to 90 % copper, window at least 15 % copper).
         The program's multilayer physics is NOT in this module (see boardrun.py).
"""

import numpy as np

import conduction as cd
import diagonal as dg
import native_gerber as ng
import scenarios as sc

H_FACE = 10.0            # W/m2K on each face
HEATER_MM = 6.0          # square heater side
WINDOW_MM = 36.0         # window side


def cut_windows(copper_path, box, per_board=6, seed=7, pix=0.05, window=WINDOW_MM, heater=HEATER_MM, max_tries=400):
    """!
    @brief Cut windows of the top copper layer of a board whose heater block and window have a usable amount of copper.
    @param copper_path Top copper Gerber file.
    @param box Board box (x0, y0, x1, y1) in mm.
    @param per_board Number of windows wanted.
    @param seed Seed of the generator (the same board gives the same windows).
    @param pix Pixel of the coverage masks (mm).
    @param window Window side (mm).
    @param heater Heater side (mm); the heater sits at the centre of the window.
    @param max_tries Random positions tried at most.
    @return list of dicts: x_left, y_bottom (mm, file coordinates), coverage (float array, rows from the top), copper_fraction (window), heater_fraction (heater block).
    """
    rng = np.random.default_rng(seed)
    layer = ng.Layer(open(copper_path, errors="replace").read())
    x0, y0, x1, y1 = box
    out, tries = [], 0
    h = int(round(heater / pix))
    n = int(round(window / pix))
    lo = (n - h) // 2
    while len(out) < per_board and tries < max_tries and x1 - x0 > window and y1 - y0 > window:
        tries += 1
        ox, oy = rng.uniform(x0, x1 - window), rng.uniform(y0, y1 - window)
        cov = ng.render_coverage(layer, ox, oy + window, window, window, pix, 4)
        hb = cov[lo:lo + h, lo:lo + h]
        if 0.15 <= hb.mean() <= 0.9 and cov.mean() >= 0.15:
            out.append({"x_left": round(float(ox), 2), "y_bottom": round(float(oy), 2), "coverage": cov, "copper_fraction": float(cov.mean()), "heater_fraction": float(hb.mean())})
    return out


def sheet(cov):
    """!
    @brief The pixel sheet conductance of a coverage mask in the one-sheet physics.
    @param cov Float array, copper fraction per pixel.
    @return numpy.ndarray of W/K (laminate plus copper in proportion).
    """
    return cd.S_LAM + np.asarray(cov, float) * (cd.S_CU - cd.S_LAM)


def references(S, pix, power, fixed, heater):
    """!
    @brief The two pixel references (five-point and nine-point) of one window.
    @param S Pixel sheet conductances.
    @param pix Pixel (mm).
    @param power Heat per pixel (W).
    @param fixed Fixed (held) pixels.
    @param heater Heater block (y0, y1, x0, x1) in pixels.
    @return dict "5" and "9" -> mean temperature rise of the heater block (K).
    """
    y0, y1, x0, x1 = heater
    t5 = sc.pixel_reference(S, pix, power, H_FACE, fixed)
    t9 = dg.pixel_reference9(S, pix, power, H_FACE, fixed)
    return {"5": float(t5[y0:y1, x0:x1].mean()), "9": float(t9[y0:y1, x0:x1].mean())}


def coarse(S, pix, n, power, fixed, heater):
    """!
    @brief The heater mean of every mapping on cells of n x n pixels.
    @param S Pixel sheet conductances.
    @param pix Pixel (mm).
    @param n Pixels per cell side (even).
    @param power Heat per pixel (W).
    @param fixed Fixed pixels.
    @param heater Heater block (y0, y1, x0, x1) in pixels (multiples of n).
    @return dict method -> mean temperature rise of the heater block (K): fill fraction, geometric mean, lambda 0.5, flow-based faces, and flow-based faces with half the diagonal couplings.
    """
    y0, y1, x0, x1 = heater
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power[:cy * n, :cx * n].reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed, n).mean(axis=(2, 3)) >= 0.5
    faces = sc.coarse_faces(S, n, cd.S_CU, cd.S_LAM)
    out = {}
    for name in ("fill fraction (today)", "geometric mean", "lambda 0.5", "flow-based faces"):
        t = sc.solve_general(*faces[name], pix * n, pw, H_FACE, fx)
        out[name] = float(t[y0 // n:y1 // n, x0 // n:x1 // n].mean())
    t = dg.solve9(*dg.hybrid_faces(S, n, 0.5), pix * n, pw, H_FACE, fx)
    out["flow + diagonal 0.5"] = float(t[y0 // n:y1 // n, x0 // n:x1 // n].mean())
    return out


def run_window(cov, pix, cells_mm=(0.5, 1.0), heater_mm=HEATER_MM, with_reference9=True):
    """!
    @brief One window: the references and every mapping at every cell size, as errors against the references.
    @param cov Coverage mask of the window (rows from the top), square, side a whole number of cells of every cell size.
    @param pix Pixel (mm).
    @param cells_mm Cell sizes (mm).
    @param heater_mm Heater side (mm).
    @param with_reference9 False skips the nine-point reference (slower).
    @return dict with ref5, ref9 (K) and errors {cell_mm: {method: {"5": %, "9": %}}} (percent difference of the heater mean from the reference).
    """
    S = sheet(cov)
    power, fixed, heater = sc.box_scenario(S.shape, pix, heater_mm)
    t5 = sc.pixel_reference(S, pix, power, H_FACE, fixed)
    t9 = dg.pixel_reference9(S, pix, power, H_FACE, fixed) if with_reference9 else None
    y0, y1, x0, x1 = heater
    res = {"ref5": float(t5[y0:y1, x0:x1].mean()), "ref9": float(t9[y0:y1, x0:x1].mean()) if t9 is not None else float("nan"), "errors": {}}
    for c in cells_mm:
        n = int(round(c / pix))
        # Take the heater block to whole cells so that the heater mean is over the same pixels in the methods and in the references (the block grows by less than one cell on each side)
        hb = (heater[0] // n * n, -(-heater[1] // n) * n, heater[2] // n * n, -(-heater[3] // n) * n)
        refs = {"5": float(t5[hb[0]:hb[1], hb[2]:hb[3]].mean()), "9": float(t9[hb[0]:hb[1], hb[2]:hb[3]].mean()) if t9 is not None else float("nan")}
        runs = coarse(S, pix, n, power, fixed, hb)
        res["errors"][c] = {m: {k: 100.0 * (v / refs[k] - 1.0) for k in ("5", "9")} for m, v in runs.items()}
    return res
