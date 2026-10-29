#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_warning_rule.py
@brief Where does the channel effect start to matter, as a function of the gap, the fin height, the length of the channels and the temperature of the block, and is a rule on the channel Rayleigh number a better warning than "gap below 4 mm"?

@details For a grid of gap, fin height, channel length and block excess temperature the script computes, with `lib/channel.py`:
         * `Ra_b = g beta theta b^4 Pr / (nu^2 L)` at the block excess temperature theta (film temperature at theta / 2);
         * the fraction of the isolated-plate limit of the composite, `phi = Nu_b / (0.59 Ra_b^(1/4)) = [1 + (14.16 / Ra_b^(3/4))^2]^(-1/2)` (a function of Ra_b alone);
         * the loss of the finned face, `rho = h_exp(channel) / h_exp(program)`, with `h_exp(program) = h_pl x fin_ratio(h_pl)` and `h_pl` the isolated vertical plate of height L
           at theta (Churchill and Chu, laminar form), the coefficient the program's computed mode gives for a plate of that height.
         * the same loss against the composite's own isolated-plate limit, `rho_bl = h_exp(channel) / h_exp(0.59 Ra_b^(1/4) k / b)` (added by the review: the
           Churchill and Chu plate is 1 to 13 % below that limit, so `rho` mixes the channel effect with the difference between two plate correlations; `rho_bl` is the
           channel effect alone, about `phi`).
         It then asks which rule separates the cases with `rho < 0.9` (a loss of 10 % of the finned-face conductance) from the others: the program's rule today (still air, gap below 4 mm)
         and the rule `Ra_b < Ra_crit`; the best `Ra_crit` is searched, and the gap at which each rule changes its answer is tabulated.

Usage: .venv/bin/python research/fin-channel/scripts/study_warning_rule.py
"""

import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import channel as ch                                      # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
GAPS = np.array([1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0]) / 1000.0
LENGTHS = (0.020, 0.040, 0.060, 0.100, 0.200)
THETAS = (10.0, 20.0, 40.0, 80.0)
HEIGHTS = (0.005, 0.015, 0.030)
T_FIN, K_FIN = 0.0015, 204.0


def point(gap, height, length, theta):
    """!
    @brief The numbers of one geometry and temperature.
    @param gap Air gap in m.
    @param height Fin height in m.
    @param length Channel length in m.
    @param theta Block excess temperature in K.
    @return Dict with ra_b, phi, rho, h_ch, h_pl.
    """
    c = ch.exposed_h_channel(theta, gap, T_FIN, height, length, K_FIN)
    h_pl = ch.h_plate_vertical(theta, length)
    hc = height + 0.5 * T_FIN
    p = gap + T_FIN
    eta = ch.fin_efficiency(h_pl, K_FIN, T_FIN, hc)
    h_prog = h_pl * ((1.0 - T_FIN / p) + 2.0 * hc * eta / p)
    ra = c["ra_b"]
    phi = (1.0 + (14.16 / ra ** 0.75) ** 2) ** -0.5
    # The boundary-layer limit of the composite itself, at the block temperature: h = 0.59 Ra_b^(1/4) k / b (= 0.59 Ra_L^(1/4) k / L)
    h_bl = 0.59 * ch.ra_channel(theta, gap, length) ** 0.25 * ch.air(20.0 + 0.5 * theta)["k"] / gap
    eta_bl = ch.fin_efficiency(h_bl, K_FIN, T_FIN, hc)
    h_bl_exp = h_bl * ((1.0 - T_FIN / p) + 2.0 * hc * eta_bl / p)
    return {"ra_b": ra, "phi": phi, "rho": c["h_exp"] / h_prog, "rho_bl": c["h_exp"] / h_bl_exp, "h_ch": c["h_ch"], "h_pl": h_pl, "h_bl": h_bl}


def main():
    """!
    @brief Run the grid, print the tables and write the JSON.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    pts = []
    for height, length, theta in itertools.product(HEIGHTS, LENGTHS, THETAS):
        for gap in GAPS:
            d = point(gap, height, length, theta)
            d.update({"gap": gap, "height": height, "length": length, "theta": theta})
            pts.append(d)
    ra = np.array([d["ra_b"] for d in pts])
    rho = np.array([d["rho"] for d in pts])
    gap = np.array([d["gap"] for d in pts])
    bad = rho < 0.9
    print(f"{len(pts)} cases; {bad.sum()} with a loss of the finned face of 10 % or more (rho < 0.9)")
    print("\nA. Rule: still air and gap below 4 mm (the program today)")
    w4 = gap < 4.0e-3
    print(f"   warns {w4.sum()}; misses {int((bad & ~w4).sum())} cases with rho < 0.9 (false negatives), warns {int((w4 & ~bad).sum())} without a 10 % loss (false positives)")
    print("\nB. Rule: Ra_b < Ra_crit (the channel Rayleigh number at the block temperature)")
    print("| Ra_crit | warns | false negatives (rho < 0.9, no warning) | false positives |")
    print("| --: | --: | --: | --: |")
    best = None
    for rc in (30, 50, 70, 90, 110, 130, 160, 200, 300):
        w = ra < rc
        fn, fp = int((bad & ~w).sum()), int((w & ~bad).sum())
        print(f"| {rc} | {int(w.sum())} | {fn} | {fp} |")
        if best is None or fn + fp < best[1]:
            best = (rc, fn + fp)
    print(f"   fewest errors at Ra_crit = {best[0]} ({best[1]} misclassified of {len(pts)})")
    # Ra_b at which rho = 0.9, 0.75 and 0.5 along every (height, length, theta) line, by interpolation in the gap
    print("\nC. Ra_b at which the loss of the finned face reaches 10 %, 25 % and 50 % (by interpolation along the gap, every combination of the grid)")
    cr = {0.9: [], 0.75: [], 0.5: []}
    for height, length, theta in itertools.product(HEIGHTS, LENGTHS, THETAS):
        line = [d for d in pts if d["height"] == height and d["length"] == length and d["theta"] == theta]
        r_line = np.array([d["rho"] for d in line])
        a_line = np.array([d["ra_b"] for d in line])
        for level in cr:
            if r_line.min() < level < r_line.max():
                cr[level].append(float(np.interp(level, r_line, a_line)))
    for level, vals in cr.items():
        print(f"   rho = {level}: Ra_b median {np.median(vals):.0f}, range {min(vals):.0f} to {max(vals):.0f} ({len(vals)} lines)")
    print("\nD. Gap (mm) at which Ra_b = 90 for a few channel lengths and block temperatures (the gap below which the rule warns)")
    print("| channel length (mm) | " + " | ".join(f"{t:g} K" for t in THETAS) + " |")
    print("| --: | " + " | ".join("--:" for _ in THETAS) + " |")
    for length in LENGTHS:
        cells = []
        for theta in THETAS:
            g = np.linspace(1e-3, 40e-3, 4000)
            r = np.array([ch.ra_channel(theta, x, length) for x in g])
            cells.append(f"{1000 * g[np.searchsorted(r, 90.0)]:.1f}")
        print(f"| {1000 * length:g} | " + " | ".join(cells) + " |")
    print("\nE. The 6.5 mm gap of the program's finned blocks (fins 15 mm high, 1.5 mm thick)")
    print("| channel length (mm) | block excess (K) | Ra_b | h channel (W/m²K) | h plate (W/m²K) | loss of the finned face (1 - rho) |")
    print("| --: | --: | --: | --: | --: | --: |")
    for length, theta in itertools.product((0.030, 0.040, 0.060, 0.100), (20.0, 40.0, 60.0)):
        d = point(0.0065, 0.015, length, theta)
        print(f"| {1000 * length:g} | {theta:g} | {d['ra_b']:.0f} | {d['h_ch']:.2f} | {d['h_pl']:.2f} | {100 * (1 - d['rho']):.0f} % |")
    # F (review): the same counts when the loss is measured against the composite's own isolated-plate limit, so that it is the channel effect alone
    rho_bl = np.array([d["rho_bl"] for d in pts])
    bad_bl = rho_bl < 0.9
    print("\nF. The loss against the composite's own isolated-plate limit (0.59 Ra_b^(1/4) k / b), the channel effect alone")
    print(f"   {bad_bl.sum()} cases with rho_bl < 0.9; the 4 mm rule misses {int((bad_bl & ~w4).sum())}, false positives {int((w4 & ~bad_bl).sum())}")
    print("| Ra_crit | warns | false negatives | false positives |")
    print("| --: | --: | --: | --: |")
    for rc in (30, 50, 70, 90, 110, 130):
        w = ra < rc
        print(f"| {rc} | {int(w.sum())} | {int((bad_bl & ~w).sum())} | {int((w & ~bad_bl).sum())} |")
    print("   ratio of that limit to the Churchill and Chu laminar plate (the baseline of A to E), min / median / max: "
          f"{min(d['h_bl'] / d['h_pl'] for d in pts):.3f} / {np.median([d['h_bl'] / d['h_pl'] for d in pts]):.3f} / {max(d['h_bl'] / d['h_pl'] for d in pts):.3f}")
    print("\nG. The 6.5 mm gap (fins 15 x 1.5 mm): loss of the finned face against the Churchill and Chu plate (as in E) and against the composite's own plate limit")
    print("| channel length (mm) | block excess (K) | Ra_b | phi | loss against the plate | loss against the limit (channel effect) |")
    print("| --: | --: | --: | --: | --: | --: |")
    for length, theta in itertools.product((0.030, 0.040, 0.060, 0.100), (20.0, 40.0, 60.0)):
        d = point(0.0065, 0.015, length, theta)
        print(f"| {1000 * length:g} | {theta:g} | {d['ra_b']:.0f} | {d['phi']:.2f} | {100 * (1 - d['rho']):.0f} % | {100 * (1 - d['rho_bl']):.0f} % |")
    with open(os.path.join(OUT, "warning_rule.json"), "w") as f:
        json.dump({"points": pts, "best_ra_crit": best[0]}, f)


if __name__ == "__main__":
    main()
