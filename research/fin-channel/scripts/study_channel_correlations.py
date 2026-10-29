#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_channel_correlations.py
@brief The composite correlations of the isothermal parallel-plate channel (Elenbaas, Churchill, Bar-Cohen and Rohsenow, Raithby and Hollands) against an independent numerical solution, their limits, and the optimum spacing they imply.

@details Question: do the correlations that the README of `block-and-fins` quoted from memory say what the literature says, and is the numerical solution of the channel that the literature
         is built on (Bodoia and Osterle's boundary-layer formulation, `lib/channel_bl.py`, which imports nothing from the program) in agreement with them? The script prints
         (1) the four correlations and the numerical Nusselt number for Ra_b from 0.1 to 1e5, with the energy balance and a grid check of the numerical solution,
         (2) the limits of every correlation (Ra_b / 24 and the boundary-layer constant) and the optimum spacing constants obtained by maximising the heat per unit base area
             (the "memory" values 2.714 and 1.307 of `research/theory/BIBLIOGRAPHY.md` are recomputed, not assumed).
         Results go to `research/fin-channel/out/correlations.json` for `make_figures.py`.

Usage: .venv/bin/python research/fin-channel/scripts/study_channel_correlations.py   (about 1 minute)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import channel as ch                                      # noqa: E402
import channel_bl as cb                                   # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RAS = (0.1, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1.0e3, 1.0e4, 1.0e5)


def main():
    """!
    @brief Run the comparison and print the tables.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    print("A. Mean Nusselt number Nu_b = h b / k of the symmetric isothermal channel, Pr = 0.71 (numerical: marching solution, 200 x 800)")
    print("| Ra_b | numerical | energy balance (wall - enthalpy) | Elenbaas (8) | Churchill (20) | Bar-Cohen & Rohsenow (21) | Raithby & Hollands (22) | numerical / BCR - 1 | spread of the four |")
    print("| --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    rows = []
    for ra in RAS:
        r = cb.solve(ra, n_y=200, n_x=800, stretch=3.0)
        c = {n: (f(ra, 0.71) if f is ch.nu_churchill else f(ra)) for n, f in ch.CORRELATIONS.items()}
        vals = list(c.values())
        spread = max(vals) / min(vals) - 1
        print(f"| {ra:g} | {r['nu_b']:.4f} | {100 * r['energy_residual']:+.1f} % | {c['Elenbaas']:.4f} | {c['Churchill']:.4f} | {c['Bar-Cohen-Rohsenow']:.4f} | {c['Raithby-Hollands']:.4f} | "
              f"{100 * (r['nu_b'] / c['Bar-Cohen-Rohsenow'] - 1):+.1f} % | {100 * spread:.0f} % |")
        rows.append({"ra": ra, "numerical": r["nu_b"], "energy": r["energy_residual"], **c})
    print("\nB. Grid check of the numerical solution (Nu_b by the enthalpy gain)")
    print("| Ra_b | 100 x 400 | 200 x 800 | 300 x 1200 |")
    print("| --: | --: | --: | --: |")
    for ra in (1.0, 10.0, 100.0, 1.0e3, 1.0e4):
        vals = [cb.solve(ra, n_y=ny, n_x=nx, stretch=3.0)["nu_b"] for ny, nx in ((100, 400), (200, 800), (300, 1200))]
        print(f"| {ra:g} | " + " | ".join(f"{v:.4f}" for v in vals) + " |")
    print("\nC. Limits of the correlations (Nu_b / Ra_b at Ra_b -> 0 and Nu_b / Ra_b^(1/4) at Ra_b -> infinity)")
    print("| correlation | Nu / Ra at 1e-3 | Nu / Ra^(1/4) at 1e9 |")
    print("| :-- | --: | --: |")
    for n, f in ch.CORRELATIONS.items():
        g = (lambda x: f(x, 0.71)) if f is ch.nu_churchill else f
        print(f"| {n} | {g(1e-3) / 1e-3:.5f} (1/24 = {1 / 24:.5f}) | {g(1e9) / 1e9 ** 0.25:.4f} |")
    print("\nD. Optimum spacing of plates of negligible thickness from each correlation: S_opt = K L / Ra_L^(1/4); Ra_b and Nu_b at the optimum")
    print("| correlation | K | Ra_b at the optimum | Nu_b at the optimum |")
    print("| :-- | --: | --: | --: |")
    for n, f in ch.CORRELATIONS.items():
        k, ra_b, nu = ch.optimum_spacing_constants(f)
        print(f"| {n} | {k:.4f} | {ra_b:.2f} | {nu:.4f} |")
    with open(os.path.join(OUT, "correlations.json"), "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
