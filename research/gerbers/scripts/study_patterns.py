"""!
@file study_patterns.py
@brief Regular copper patterns (hatch stripes, cross-hatch, isolated squares, perforated plane): where do the scalar mappings fail?
@details The program lets the user draw a zone with a "fill" below 1, which stands for a hatch or a mesh. Real Gerber copper has pours with clearances
         and traces, but a hatch is a different geometry: stripes conduct as the arithmetic mean along them and as the harmonic mean across.
         Here synthetic patterns (36 x 36 mm, 0.1 mm pixels, heater of 6 x 6 mm at 12..18 mm) are used to test every mapping against the resolved copper.
         Patterns: stripes at 0, 45 and 90 degrees (pitch 0.5, 1 and 2 mm, fill 0.25, 0.5, 0.75); cross-hatch (grid of lines); isolated squares
         separated by clearances; a plane perforated by a lattice of round holes. Run: .venv/bin/python research/gerbers/scripts/study_patterns.py (from the repository root) (about 1 minute).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math
from multiprocessing import Pool

import numpy as np

import conduction as cd
import windows

PIX = windows.PIX
HEATER = windows.HEATER
CELLS = (0.6, 1.0, 2.0)
METHODS = ("arithmetic", "geometric", "Bruggeman", "lam 0.5", "lam 0.6", "cellnum", "dual m=0")


def coordinates():
    """!
    @brief Pixel-centre coordinates of a 36 x 36 mm window.
    @return Tuple (X, Y) in mm.
    """
    n = int(round(windows.WIN / PIX))
    c = (np.arange(n) + 0.5) * PIX
    return np.meshgrid(c, c)


def make_patterns():
    """!
    @brief Every synthetic pattern.
    @return List of tuples (class name, label, boolean mask).
    """
    X, Y = coordinates()
    out = []
    for theta in (0, 45, 90):
        a = math.radians(theta)
        u = X * math.cos(a) + Y * math.sin(a)
        for P in (0.5, 1.0, 2.0):
            for f in (0.25, 0.5, 0.75):
                out.append((f"stripes {theta} deg", f"P={P} f={f}", np.mod(u, P) < f * P))
    for P in (0.5, 1.0, 2.0):
        for w in (0.15, 0.3):
            out.append(("cross-hatch", f"P={P} w={w * P:.2f}", (np.mod(X, P) < w * P) | (np.mod(Y, P) < w * P)))
        for s in (0.7, 0.85):
            out.append(("squares", f"P={P} s={s * P:.2f}", (np.mod(X, P) < s * P) & (np.mod(Y, P) < s * P)))
        for r in (0.3, 0.4):
            dx, dy = np.mod(X, P) - P / 2, np.mod(Y, P) - P / 2
            out.append(("perforated", f"P={P} r={r * P:.2f}", dx * dx + dy * dy > (r * P) ** 2))
    return out


def run(args):
    """!
    @brief All mappings on one pattern and every cell size.
    @param args Tuple (class name, label, mask).
    @return List of records (class, label, copper fraction, cell mm, method, error of the mean %).
    """
    cls, label, mask = args
    S = cd.sheet_of(mask)
    hs, he = int(HEATER[0] / PIX), int(HEATER[1] / PIX)
    T = cd.solve_faces(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), PIX, hs, he, hs, he)
    ref = T[hs:he, hs:he].mean()
    out = []
    for c in CELLS:
        n = int(round(c / PIX))
        blk = cd.cell_blocks(S, n)
        f = (blk == cd.S_CU).mean(axis=(2, 3))
        k0, k1 = int(round(HEATER[0] / c)), int(round(HEATER[1] / c))
        cand = {"arithmetic": cd.faces_from_cells(*(2 * [cd.map_power(f, 1.0)])), "geometric": cd.faces_from_cells(*(2 * [cd.map_power(f, 0.0)])),
                "Bruggeman": cd.faces_from_cells(*(2 * [cd.map_bruggeman(f)])), "lam 0.5": cd.faces_from_cells(*cd.map_lambda(blk, 0.5)),
                "lam 0.6": cd.faces_from_cells(*cd.map_lambda(blk, 0.6)), "cellnum": cd.faces_from_cells(*cd.map_cell_problem(blk)),
                "dual m=0": cd.dual_faces(S, n, 0)}
        for name, (gx, gy) in cand.items():
            Tc = cd.solve_faces(gx, gy, c, k0, k1, k0, k1)[k0:k1, k0:k1]
            out.append((cls, label, float(mask.mean()), c, name, 100 * (Tc.mean() / ref - 1)))
    return out


def main():
    """!
    @brief Run all patterns and print the MAE per class and cell size, and the worst cases of the geometric mean and of lambda 0.5.
    @return None.
    """
    pats = make_patterns()
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(run, pats):
            out += r
    classes = sorted({o[0] for o in out})
    print(f"{len(pats)} patterns. MAE (bias) of the mean-temperature error, %")
    for c in CELLS:
        print(f"\ncell {c} mm" + "".join(f"{m:>16}" for m in METHODS))
        for cls in classes:
            row = []
            for m in METHODS:
                e = np.array([o[5] for o in out if o[0] == cls and o[3] == c and o[4] == m])
                row.append(f"{np.abs(e).mean():5.1f} ({e.mean():+5.1f})")
            print(f"  {cls:16s}" + "".join(f"{x:>16}" for x in row))
    for m in ("geometric", "lam 0.5"):
        worst = sorted((o for o in out if o[4] == m and o[3] <= 1.0), key=lambda o: -abs(o[5]))[:6]
        print(f"\nworst cases of '{m}' (cells up to 1 mm):")
        for o in worst:
            print(f"  {o[0]:16s} {o[1]:16s} copper {o[2]:.2f}  cell {o[3]}  error {o[5]:+.1f} %")


if __name__ == "__main__":
    main()
