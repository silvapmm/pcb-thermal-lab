#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cutcell_sources.py
@brief What the cut-cell literature documents and what it does not: reproduction of a published case, and the film (Robin) boundary on a disc and an annulus in three cut-cell schemes against the closed form.
@details Studies (each prints a markdown table; `--out` writes the numbers as JSON):

         jc      - Problem 1 of Johansen and Colella (the "flower", Dirichlet data, `phi = r^4 cos 3 theta`) with the independent implementation `lib/jc_poisson.py`,
                   against their Tables I and II (report LBNL-39908, printed page 15). Seconds.
         sheet   - a thin round sheet with face losses and a Robin film on the rim (disc, and annulus with a film on both rims) against the Bessel closed form of
                   `lib/sheet_robin.py`, for the program's treatment of a cut cell and for the aperture, links and links+strip schemes of the literature; the sheet is
                   moved against the grid by a fraction of a cell to show the dependence on where the outline cuts. Light (the largest case is 83 x 83 cells).
         proto   - the layered-FVM prototype `lib/fvm_cutcell.py` on a round two-layer board against the axisymmetric reduction (the closest representable version of the
                   sheet case); runs only when the prototype exists in `lib/` (it is on the branch `research/rotated-square-3d`), or in the folder named by the environment
                   variable `CUTCELL_LIB`.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_cutcell_sources.py [jc|sheet|proto|all] [--out out/cutcell_sources.json]   (from the repository root)
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import jc_poisson as jc          # noqa: E402
import sheet_robin as sr         # noqa: E402

# Published values of the report (LBNL-39908): Table I (partial and full cells, N, norm) and Table II (solution error), read from the page images (R)
JC_TABLE = {
    40: {"tau_p": 1.20e-1, "tau_i": 1.66e-3, "n_p": 208, "n_i": 400, "xi_inf": 5.85e-5, "xi_1": 8.34e-6},
    80: {"tau_p": 7.71e-2, "tau_i": 4.15e-4, "n_p": 420, "n_i": 1824, "xi_inf": 7.36e-6, "xi_1": 1.02e-6},
    160: {"tau_p": 4.20e-2, "tau_i": 1.04e-4, "n_p": 856, "n_i": 7712, "xi_inf": 1.17e-6, "xi_1": 1.07e-7},
    320: {"tau_p": 2.18e-2, "tau_i": 2.59e-5, "n_p": 1716, "n_i": 31716, "xi_inf": 1.68e-7, "xi_1": 1.80e-8},
    640: {"tau_p": 1.11e-2, "tau_i": 6.49e-6, "n_p": 3416, "n_i": 128604, "xi_inf": 2.27e-8, "xi_1": 5.02e-9},
}


def study_jc(sizes=(40, 80, 160, 320, 640)):
    """!
    @brief Reproduce Tables I and II of Johansen and Colella with the independent implementation.
    @param sizes Cells per unit length.
    @return dict {N: {published, computed}}.
    """
    print("\n### Johansen and Colella, Problem 1 (flower, Dirichlet): published against the independent implementation\n")
    print("| N | cut cells (pub / ours) | full cells (pub / ours) | max kappa tau, cut (pub / ours) | max tau, full (pub / ours) | max error (pub / ours) | 1-norm error (pub / ours) |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    out = {}
    for n in sizes:
        r, p = jc.solve(n), JC_TABLE[n]
        out[n] = {"published": p, "computed": {k: r[k] for k in ("tau_partial_inf", "tau_full_inf", "n_partial", "n_full", "xi_inf", "xi_1_mean")}}
        print(f"| {n} | {p['n_p']} / {r['n_partial']} | {p['n_i']} / {r['n_full']} | {p['tau_p']:.2e} / {r['tau_partial_inf']:.2e} | {p['tau_i']:.2e} / {r['tau_full_inf']:.2e} "
              f"| {p['xi_inf']:.2e} / {r['xi_inf']:.2e} | {p['xi_1']:.2e} / {r['xi_1_mean']:.2e} |", flush=True)
    return out


def _errors(shape, res, exact_fn, scheme, centre):
    """!
    @brief Errors of a solution against the closed form at the nodes.
    @param shape sheet_robin.Shape.
    @param res Result of `sheet_robin.solve`.
    @param exact_fn Function r -> exact rise.
    @param scheme Scheme name (the "program" cell value is a mean over the open part, so it is compared at the centroid; the others at their nodes).
    @param centre Centre of the sheet (x, y) in m.
    @return (max error over all cells, max error over the whole cells, volume-weighted mean absolute error) in K.
    """
    if scheme == "program":
        px, py = shape.cx, shape.cy
    else:
        px, py = res["px"], res["py"]
    err = np.abs(res["T"] - exact_fn(np.hypot(px - centre[0], py - centre[1])))
    full = shape.kap > 1.0 - 1e-9
    w = shape.kap * shape.dx ** 2
    ok = ~np.isnan(err)
    return float(np.nanmax(err)), float(np.nanmax(np.where(full, err, 0.0))), float((np.nan_to_num(err) * w)[ok].sum() / w[ok].sum())


def study_sheet(cells_per_radius=(5, 10, 20, 40)):
    """!
    @brief Round sheet with a Robin film on the rim, four schemes against the closed form.
    @param cells_per_radius Cells per radius.
    @return dict of the numbers.
    """
    radius, S, G, q = 0.01, 0.05, 20.0, 1000.0
    offsets = ((0.0, 0.0), (0.37, 0.21), (0.5, 0.5))
    out = {}
    cases = [("disc, H = 0.016 W/m K (h_side 10)", dict(H=0.016)), ("disc, H = 5 W/m K (h_side 3000)", dict(H=5.0)), ("disc, H = 100 W/m K (almost fixed rim)", dict(H=100.0)),
             ("annulus r1 = R/3, H = 5 on both rims", dict(H=5.0, inner=radius / 3.0))]
    for label, kw in cases:
        H, inner = kw["H"], kw.get("inner", 0.0)
        if inner:
            def exact_fn(r):
                return sr.annulus_exact(r, inner, radius, S, G, H, H, q)
            qe = sr.annulus_rim_loss(inner, radius, S, G, H, H, q)
        else:
            def exact_fn(r):
                return sr.disc_exact(r, radius, S, G, H, q)
            qe = sr.disc_rim_loss(radius, S, G, H, q)
        t_ref = float(np.max(exact_fn(np.linspace(inner if inner else 0.0, radius, 200))))
        print(f"\n### {label}: exact rim loss {qe:.4f} W of {q * np.pi * (radius ** 2 - inner ** 2):.4f} W, highest rise {t_ref:.3f} K\n")
        print("| cells per radius | shift (cells) | " + " | ".join(f"{s}: max / whole cells / mean (K), rim loss (%)" for s in sr.SCHEMES) + " |")
        print("| --: | :-- | " + " | ".join("--:" for _ in sr.SCHEMES) + " |")
        out[label] = {}
        for n_r in cells_per_radius:
            dx = radius / n_r
            for off in offsets:
                centre = (off[0] * dx, off[1] * dx)
                shape = sr.Shape(radius, dx, centre=centre, inner=inner)
                row, rec = [], []
                for sc in sr.SCHEMES:
                    try:
                        res = sr.solve(shape, S, G, H, q, sc, H_inner=H)
                    except ValueError:
                        # The film of Bochkov and Gibou is not defined when a cell centre lies farther outside the sheet than S / H
                        row.append("ill posed")
                        rec.append(None)
                        continue
                    e = _errors(shape, res, exact_fn, sc, centre)
                    rim = 100.0 * (res["q_rim"] / qe - 1.0)
                    row.append(f"{e[0]:.3f} / {e[1]:.3f} / {e[2]:.4f}, {rim:+.2f}")
                    rec.append([*e, rim])
                out[label][f"{n_r}|{off[0]},{off[1]}"] = rec
                print(f"| {n_r} | {off[0]}, {off[1]} | " + " | ".join(row) + " |", flush=True)
    return out


def study_proto():
    """!
    @brief Run the layered-FVM prototype on the round two-layer board against the axisymmetric reduction (the closest representable version of the sheet case).
    @return dict of the numbers, or None when the prototype is not available.
    """
    for path in (os.path.join(os.path.dirname(HERE), "lib"), os.environ.get("CUTCELL_LIB", "")):
        if path and os.path.exists(os.path.join(path, "fvm_cutcell.py")):
            sys.path.insert(0, path)
            break
    else:
        print("\n(proto: lib/fvm_cutcell.py not found; set CUTCELL_LIB to the lib folder of research/rotated-square-3d)")
        return None
    import fvm_cutcell as fc           # noqa: E402
    import layered_disc                # noqa: E402
    import rotsq                       # noqa: E402
    d, a = 40.0, 3.0
    out = {}
    print("\n### layered-FVM prototype on a round board (40 mm, 3 mm part): peak at the cell centre and rim loss, per cent against the axisymmetric reduction\n")
    print("| h_side | rise (K) | cell (mm) | " + " | ".join(f"{s}: peak / rim" for s in fc.MODES + ("program",)) + " |")
    print("| --: | --: | --: | " + " | ".join("--:" for _ in range(len(fc.MODES) + 1)) + " |")
    for hs in (10.0, 1000.0):
        p = rotsq.disc_board(d, a, hs)
        amb = p.board.ambient
        sol = layered_disc.solve(p, d / 2000.0, a / 1000.0)
        for c in (1.0, 0.5):
            ref = float(np.interp(c / 1000.0 * 0.5 * np.sqrt(2.0), sol["r"], sol["top"]))
            row, rec = [], []
            for sch in fc.MODES + ("program",):
                r = fc.solve(p, c, sch)
                peak = 100.0 * (r.t_max - amb - ref) / ref
                rim = 100.0 * (r.power_out["sides"] / sol["heat_rim"] - 1.0)
                row.append(f"{peak:+.2f} / {rim:+.2f}")
                rec.append([peak, rim])
            out[f"{hs:g}|{c:g}"] = rec
            print(f"| {hs:g} | {ref:.3f} | {c:g} | " + " | ".join(row) + " |", flush=True)
    return out


def main():
    """!
    @brief Command line entry.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1] if __doc__ else "")
    ap.add_argument("which", nargs="?", default="all", choices=["jc", "sheet", "proto", "all"])
    ap.add_argument("--out", default=None, help="write the numbers as JSON to this file")
    args = ap.parse_args()
    res = {}
    if args.which in ("jc", "all"):
        res["jc"] = study_jc()
    if args.which in ("sheet", "all"):
        res["sheet"] = study_sheet()
    if args.which in ("proto", "all"):
        res["proto"] = study_proto()
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as fh:
            json.dump(res, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
