#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_optimum_spacing.py
@brief Does the channel model place the optimum fin spacing where the measurements put it? (Published cases of vertical-base fin arrays.)

@details Yazicioglu and Yuncu (J. of Thermal Science and Technology 29 (1), 2009, 99-105), Table 1, collect the fin arrays of seven groups of experimenters (vertical base,
         vertical fins, plate fins of thickness 3 mm, convection heat only) with the spacing at which the heat is largest, `s_opt`. This script takes the rows of that table
         (length L, width W, height H, temperature difference, material) and computes the spacing at which the model of `lib/channel.py` gives the largest heat for a fixed base
         width W (the number of fins n = (W + s)/(s + t) changes with the spacing), with the Bar-Cohen and Rohsenow composite correlation and the Elenbaas one, and compares with
         (a) the measured `s_opt` of the table, (b) the closed form `s_opt = 2.7156 L / Ra_L^(1/4)` of the composite itself (no fins, plates of zero thickness), (c) the fit
         `s_opt = 3.15 L / Ra_L^(1/4)` of Yazicioglu and Yuncu (their equation 3). It also reproduces the Q(s) curves of two arrays (plot values, Figures 6 and 7 of that paper,
         from Leung and others 1985: L = 150 mm, W = 190 mm, t = 3 mm, H = 10 and 17 mm, duralumin): the shape (Q(s) divided by Q at s = 45 mm) is compared, not the absolute level
         (see the README: the level of those plots is 25 to 45 % above the model at wide spacing, for a reason not established).

Usage: .venv/bin/python research/fin-channel/scripts/study_optimum_spacing.py
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import channel as ch                                      # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")

# Table 1 of Yazicioglu and Yuncu 2009: (reference row, L mm, W mm, t mm, H mm range, dT range, measured s_opt range mm, material, k W/mK assumed)
ROWS = [(1, 150, 190, 3, (10, 17), (20, 40), (9.0, 9.5), "duralumin", 150.0),
        (2, 250, 190, 3, (60, 60), (20, 80), (10.0, 10.0), "light aluminium alloy", 170.0),
        (3, 250, 190, 3, (32, 90), (20, 60), (10.5, 10.5), "duralumin", 150.0),
        (4, 312, 190, 3, (60, 60), (40, 40), (10.0, 11.0), "duralumin", 150.0),
        (6, 500, 190, 3, (60, 60), (20, 40), (12.0, 12.0), "stainless steel", 15.0),
        (8, 100, 250, 3, (5, 25), (14, 106), (7.0, 7.0), "aluminium", 200.0),
        (9, 295, 180, 3, (5, 25), (21, 162), (10.0, 11.0), "aluminium alloy", 170.0)]

# Plot values (Figures 6 and 7 of the same paper, from Leung et al. 1985), Q in W against s in mm, +-0.5 W: read from the images
LEUNG = {(17, 40): {3: 25.0, 6: 32.0, 9: 34.7, 12: 31.0, 15: 29.0, 21: 24.3, 30: 21.2, 45: 17.7},
         (17, 20): {3: 8.9, 6: 11.5, 9: 13.8, 12: 12.6, 15: 11.4, 21: 10.3, 30: 8.2, 45: 7.1},
         (10, 40): {3: 19.6, 6: 25.0, 9: 28.8, 12: 26.3, 15: 23.5, 21: 20.6, 30: 18.4, 45: 16.0},
         (10, 20): {3: 7.2, 6: 9.2, 9: 10.6, 12: 9.9, 15: 8.9, 21: 8.1, 30: 7.3, 45: 6.4}}


def q_of_s(s_mm, theta, w, length, t, height, k, nu_fun, channel=True):
    """!
    @brief Heat of an array of base width w at a spacing s (continuous number of fins).
    @param s_mm Spacing in mm.
    @param theta Base excess temperature in K.
    @param w Base width in m.
    @param length Fin length (vertical) in m.
    @param t Fin thickness in m.
    @param height Fin height in m.
    @param k Fin conductivity in W/mK.
    @param nu_fun Composite correlation.
    @param channel False for the isolated-plate coefficient everywhere (no channel effect).
    @return Heat in W.
    """
    s = s_mm / 1000.0
    n = (w + s) / (s + t)
    return ch.array_heat(theta, n, s, t, height, length, k, nu_fun=nu_fun, channel=channel)["q"]


def best_spacing(theta, w, length, t, height, k, nu_fun):
    """!
    @brief Spacing in mm that maximises the heat, by a scan and a parabolic refinement.
    @param theta Base excess temperature in K.
    @param w Base width in m.
    @param length Fin length in m.
    @param t Fin thickness in m.
    @param height Fin height in m.
    @param k Fin conductivity in W/mK.
    @param nu_fun Composite correlation.
    @return Spacing in mm of the maximum (the end of the scan if the maximum is at the edge).
    """
    ss = np.linspace(2.0, 60.0, 233)
    qq = np.array([q_of_s(s, theta, w, length, t, height, k, nu_fun) for s in ss])
    i = int(np.argmax(qq))
    if 0 < i < len(ss) - 1:
        a, b, c = np.polyfit(ss[i - 1:i + 2], qq[i - 1:i + 2], 2)
        return float(-b / (2 * a))
    return float(ss[i])


def main():
    """!
    @brief Print the optimum-spacing table and the Leung shape comparison, and write the JSON for the figures.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    k_bcr = ch.optimum_spacing_constants(ch.nu_bcr)[0]
    print(f"Closed-form constants of the composites (computed here by maximising Nu_b / b^2): "
          + ", ".join(f"{n}: {ch.optimum_spacing_constants(f)[0]:.3f}" for n, f in ch.CORRELATIONS.items()))
    print("\nA. Optimum spacing, published rows against the model (mm)")
    print("| row (Table 1) | L (mm) | H (mm) | dT (K) | material | measured s_opt | model BCR (fins) | model Elenbaas (fins) | 2.7156 L/Ra_L^(1/4) | 3.15 L/Ra_L^(1/4) |")
    print("| :-- | --: | --: | --: | :-- | --: | --: | --: | --: | --: |")
    table = []
    for row, length, w, t, hr, tr, so, mat, k in ROWS:
        lo_hi = []
        for height, theta in ((hr[0], tr[0]), (hr[1], tr[0]), (hr[0], tr[1]), (hr[1], tr[1])):
            lo_hi.append((height, theta, best_spacing(theta, w / 1000, length / 1000, t / 1000, height / 1000, k, ch.nu_bcr),
                          best_spacing(theta, w / 1000, length / 1000, t / 1000, height / 1000, k, ch.nu_elenbaas)))
        sb = [x[2] for x in lo_hi]
        se = [x[3] for x in lo_hi]
        # Closed forms with the Rayleigh number of the plate length at the film temperature (20 degC ambient assumed)
        cf = []
        for theta in tr:
            p = ch.air(20.0 + theta / 2)
            ra_l = ch.G * p["beta"] * theta * (length / 1000) ** 3 * p["pr"] / p["nu"] ** 2
            cf.append((k_bcr * length / ra_l ** 0.25, 3.15 * length / ra_l ** 0.25))
        rng = lambda v: f"{min(v):.1f}" if abs(min(v) - max(v)) < 0.05 else f"{min(v):.1f} to {max(v):.1f}"      # noqa: E731
        mrange = f"{so[0]:g}" if so[0] == so[1] else f"{so[0]:g} to {so[1]:g}"
        print(f"| {row} | {length} | {hr[0]}-{hr[1]} | {tr[0]}-{tr[1]} | {mat} | {mrange} | {rng(sb)} | {rng(se)} | {rng([c[0] for c in cf])} | {rng([c[1] for c in cf])} |")
        table.append({"row": row, "L": length, "measured": so, "bcr": sb, "elenbaas": se, "closed_bcr": [c[0] for c in cf], "closed_fit": [c[1] for c in cf]})

    print("\nB. Shape of Q(s), Leung et al. 1985 (L = 150 mm, W = 190 mm, t = 3 mm; plot values): Q(s) / Q(45 mm)")
    print("| H (mm) | dT (K) | s (mm) | measured (plot) | channel model BCR | no channel effect (isolated-plate h) |")
    print("| --: | --: | --: | --: | --: | --: |")
    leung_out = {}
    for (height, theta), d in LEUNG.items():
        ref_m = d[45]
        ref_c = q_of_s(45, theta, 0.190, 0.150, 0.003, height / 1000, 150.0, ch.nu_bcr)
        ref_p = q_of_s(45, theta, 0.190, 0.150, 0.003, height / 1000, 150.0, ch.nu_bcr, channel=False)
        rows = []
        for s, q in d.items():
            qc = q_of_s(s, theta, 0.190, 0.150, 0.003, height / 1000, 150.0, ch.nu_bcr)
            qp = q_of_s(s, theta, 0.190, 0.150, 0.003, height / 1000, 150.0, ch.nu_bcr, channel=False)
            print(f"| {height} | {theta} | {s} | {q / ref_m:.2f} | {qc / ref_c:.2f} | {qp / ref_p:.2f} |")
            rows.append({"s": s, "q_meas": q, "shape_meas": q / ref_m, "shape_ch": qc / ref_c, "shape_plate": qp / ref_p, "q_ch": qc, "q_plate": qp})
        leung_out[f"{height}_{theta}"] = rows
    # Mean absolute shape difference for s >= 6 mm (the open front of 3 mm gaps is outside the model, see the README)
    for label, key in (("channel model", "shape_ch"), ("no channel effect", "shape_plate")):
        diffs = [abs(r[key] / r["shape_meas"] - 1) for rows in leung_out.values() for r in rows if r["s"] >= 6]
        diffs3 = [r[key] / r["shape_meas"] - 1 for rows in leung_out.values() for r in rows if r["s"] == 3]
        print(f"\n{label}: mean |shape / measured - 1| for s >= 6 mm: {100 * np.mean(diffs):.1f} %, max {100 * np.max(diffs):.1f} %; at s = 3 mm: "
              + ", ".join(f"{100 * d:+.0f} %" for d in diffs3))
    # Absolute level: the model against the plot values of Leung (heat in W) for s >= 9 mm
    ratios = [r["q_ch"] / r["q_meas"] for rows in leung_out.values() for r in rows if r["s"] >= 9]
    print(f"\nAbsolute level, Leung et al. arrays, s >= 9 mm: model / measured (channel model) from {min(ratios):.2f} to {max(ratios):.2f}, mean {np.mean(ratios):.2f} ({len(ratios)} points)")
    # Figure 5 of the same paper (Yazicioglu and Yuncu 2007 arrays: L = 250 mm, W = 180 mm, H = 25 mm, t = 3 mm, aluminium alloy), plot values at a base excess of 60 K
    fig5 = {5.8: 35.5, 8.8: 41.8, 14.8: 39.0, 32.4: 29.0, 85.5: 20.0}
    print("\nC. Absolute level of the arrays of Figure 5 (plot values at 60 K above the air, +-2 W; convection only): model against measurement")
    print("| s (mm) | fins | measured (W) | channel model (W) | difference | uniform isolated-plate h (W) | difference |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    fig5_rows = []
    for s, qm in fig5.items():
        n = (180.0 + s) / (s + 3.0)
        qc = q_of_s(s, 60.0, 0.180, 0.250, 0.003, 0.025, 170.0, ch.nu_bcr)
        qp = q_of_s(s, 60.0, 0.180, 0.250, 0.003, 0.025, 170.0, ch.nu_bcr, channel=False)
        print(f"| {s} | {n:.1f} | {qm:.1f} | {qc:.1f} | {100 * (qc / qm - 1):+.0f} % | {qp:.1f} | {100 * (qp / qm - 1):+.0f} % |")
        fig5_rows.append({"s": s, "q_meas": qm, "q_ch": qc, "q_plate": qp})
    plate = ch.h_plate_vertical(60.0, 0.25) * 0.18 * 0.25 * 60.0
    print(f"   the flat vertical plate of the same base (180 x 250 mm): model {plate:.1f} W against about 13.8 W measured (plot value at 60 K)")
    # The energy ceiling of closed channels at 3 mm: fully developed mean speed u = g beta dT s^2 / (12 nu), at most the air leaving at the wall temperature
    print("\nD. The ceiling of the heat that closed 3 mm channels can carry (Leung arrays, L = 150 mm, W = 190 mm, 3 mm gap, fully developed flow, air leaving at the wall temperature)")
    print("| H (mm) | dT (K) | channels | per channel (W) | all channels (W) | measured Q(3 mm) (W) |")
    print("| --: | --: | --: | --: | --: | --: |")
    for (height, theta), d in LEUNG.items():
        p = ch.air(20.0 + theta / 2)
        s, t = 0.003, 0.003
        n_ch = round((0.190 + s) / (s + t)) - 1
        u_mean = ch.G * p["beta"] * theta * s ** 2 / (12.0 * p["nu"])
        rho = ch.P_ATM / (ch.R_AIR * (293.15 + theta / 2))
        q_ch = rho * u_mean * s * (height / 1000) * ch.CP_AIR * theta
        print(f"| {height} | {theta} | {n_ch} | {q_ch:.2f} | {n_ch * q_ch:.1f} | {d[3]:.1f} |")
    with open(os.path.join(OUT, "optimum_study.json"), "w") as f:
        json.dump({"table": table, "leung": leung_out, "fig5": fig5_rows}, f, indent=1)


if __name__ == "__main__":
    main()
