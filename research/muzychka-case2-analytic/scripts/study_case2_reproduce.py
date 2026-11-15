#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_reproduce.py
@brief Case 2 of Muzychka, Culham and Yovanovich (2003): what each model of the program and the independent 3D solver report, and where the gap to the paper comes from.
@details Prints (1) the independent 3D solution at several plan cells and sub-slab counts (surface centroid and mean, the paper's quantities, and the through-thickness mean of the column,
         the quantity one node per layer stands for), (2) the five models of the program at several cells (layer temperature at the source centroid and mean over the source),
         (3) the decomposition of the gap paper -> program into the through-thickness term (surface minus layer mean) and the film term (3D layer mean minus the program),
         (4) the same board with the half-layer resistance t/(2k) put in series with the bottom film (a change of the input, not of the program), (5) the Analytic with more modes,
         (6) the heater rows that the Results table shows (peak and mean over the footprint) and the warnings of the run.
         Run from the repository root: .venv/bin/python -u research/muzychka-case2-analytic/scripts/study_case2_reproduce.py [--quick]
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402

np.set_printoptions(precision=2, suppress=True, linewidth=160)
OUT = os.path.join(HERE, "..", "out")


def fmt(v):
    """!
    @brief A list of numbers as text.
    @param v Iterable of floats.
    @return str.
    """
    return "[" + ", ".join(f"{x:7.2f}" for x in v) + "]"


def main(quick=False):
    """!
    @brief Run the study and print every table.
    @param quick True to skip the finest cells and the 16 sub-slab reference.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    res = {}
    print("paper centroid", fmt(C.PAPER_CENTROID), "mean", fmt(C.PAPER_MEAN))
    print("\n1. independent 3D solver (adiabatic top, h 400 on the bottom, insulated sides)")
    refs = {}
    for dx, ns in ((0.5, 8), (0.5, 16), (0.25, 8)) if not quick else ((0.5, 8),):
        r = C.reference3d(dx, ns)
        refs[(dx, ns)] = r
        print(f" dx {dx} mm, {ns:2d} sub-slabs: surface centroid {fmt(r['surf_c'])} mean {fmt(r['surf_m'])}\n"
              f"{'':27s}layer-mean centroid {fmt(r['lay_c'])} mean {fmt(r['lay_m'])}  bottom mean {r['bottom_mean']:.2f}")
    ref = refs[(0.5, 8)]
    res["ref3d"] = {f"{k[0]}_{k[1]}": {a: (b if not isinstance(b, np.ndarray) else b.tolist()) for a, b in v.items()} for k, v in refs.items()}

    print("\n2. models of the program (layer temperature, centroid | mean of the source)")
    res["models"] = {}
    cells = (2.0, 1.0, 0.5) if quick else (2.0, 1.0, 0.5, 0.25)
    for m in ("fvm", "fdm", "analytic", "lumped", "solid3d"):
        for cell in cells:
            r, sim = C.run(m, cell)
            if r is None:
                continue
            res["models"][f"{m}_{cell}"] = r
            print(f" {m:8s} {cell:5.2f} mm: centroid {fmt(r['cen'])} mean {fmt(r['mean'])}   minus 3D surface centroid {fmt(np.array(r['cen']) - ref['surf_c'])}"
                  f"   minus 3D layer mean {fmt(np.array(r['cen']) - ref['lay_c'])}", flush=True)

    print("\n3. decomposition of the gap to the paper (centroids, K), FVM at 0.5 mm")
    f = np.array(res["models"]["fvm_0.5"]["cen"])
    thr = np.array(ref["surf_c"]) - np.array(ref["lay_c"])
    film = np.array(ref["lay_c"]) - f
    flux = np.array(C.POWERS) * 1e-4 * 0 + np.array(C.POWERS) / 1e-4                      # W/m2 under each 10 x 10 mm source
    bound = flux * (C.T_MM * 1e-3) / (2 * C.K_PLATE)
    mean_flux_term = sum(C.POWERS) / (C.W_MM * 1e-3) ** 2 * (C.T_MM * 1e-3) / (2 * C.K_PLATE)
    print(f" paper - 3D surface (reference check):   {fmt(np.array(C.PAPER_CENTROID) - ref['surf_c'])}")
    print(f" 3D surface - 3D layer mean (through-thickness, depends on spreading): {fmt(thr)}   bound q''t/2k {fmt(bound)}   ratio {fmt(thr / bound)}")
    print(f" 3D layer mean - FVM (film: the t/(2k) of the face film is not in the node): {fmt(film)}   mean-flux estimate Q t / (2 k A) = {mean_flux_term:.2f} K")
    print(f" total surface - FVM: {fmt(np.array(ref['surf_c']) - f)}   paper - FVM {fmt(np.array(C.PAPER_CENTROID) - f)}")
    res["decomp"] = {"through": thr.tolist(), "film": film.tolist(), "bound": bound.tolist(), "film_estimate": mean_flux_term}

    print("\n4. the half-layer film in series with h_bottom (input change on a copy of the problem, program untouched)")
    h_eff = 1.0 / (1.0 / C.H_PAPER + (C.T_MM * 1e-3) / (2 * C.K_PLATE))
    print(f" h_bottom 400 -> {h_eff:.2f} W/m2K")
    res["film_fix"] = {}
    for m in ("fvm", "fdm", "analytic", "lumped"):
        r, sim = C.run(m, 0.5, h=h_eff)
        if r:
            res["film_fix"][m] = r
            print(f" {m:8s} 0.5 mm: centroid {fmt(r['cen'])}   minus 3D layer mean {fmt(np.array(r['cen']) - ref['lay_c'])}   minus 3D surface {fmt(np.array(r['cen']) - ref['surf_c'])}")

    print("\n5. Analytic modes (default and 3 x as many) at 0.5 mm")
    for modes in (None, 60, 120):
        r, sim = (C.run("analytic", 0.5) if modes is None else C.run("analytic", 0.5, analytic_modes=modes))
        if r:
            print(f" modes {modes}: centroid {fmt(r['cen'])}")

    print("\n6. what the Results table and the warnings show (FVM 1 mm, the project as built here)")
    r, sim = C.run("fvm", 1.0)
    rows = sim.heater_rows()
    for row in rows:
        print(f"   {row['name']}: power {row['power_w']:.1f} W  t_max {row['t_max']:.2f}  t_mean {row['t_mean']:.2f} C")
    for w in sim.warnings:
        print("   WARNING:", w[:260])
    for m in ("analytic", "lumped", "fdm", "solid3d"):
        r2, s2 = C.run(m, 1.0)
        if s2:
            print(f"   [{m}] warnings: {len(s2.warnings)}; thick-plate shown: {sum('thick and poorly' in w for w in s2.warnings)}")
    with open(os.path.join(OUT, "reproduce.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)


if __name__ == "__main__":
    main("--quick" in sys.argv)
