#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the channel-effect investigation, drawn from the JSON files of the study scripts (research/fin-channel/out/) and from the numerical channel solver.
@details Needs `out/program_study.json` (study_program_finned_block.py), `out/optimum_study.json` (study_optimum_spacing.py), `out/warning_rule.json` (study_warning_rule.py).
         Writes figures/fig_02_channel_profiles.png, fig_03_nusselt_against_rayleigh.png, fig_05_coefficient_and_heat_against_gap.png, fig_06_leung_array.png,
         fig_07_optimum_spacing.png, fig_08_program_error_against_gap.png and fig_09_warning_rule.png (the numbers 01, 04 and 10 belong to `make_diagrams.py`).
         Run: .venv/bin/python research/fin-channel/scripts/make_figures.py (from the repository root, after the study scripts).
"""

import json
import os
import sys
from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import channel as ch                                               # noqa: E402
import channel_bl as cb                                            # noqa: E402

OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"
COL = {"Elenbaas": "#1f77b4", "Churchill": "#2ca02c", "Bar-Cohen-Rohsenow": "#d62728", "Raithby-Hollands": "#9467bd"}


def load(name):
    """!
    @brief Read a JSON file of the study scripts.
    @param name File name inside out/.
    @return Parsed object.
    """
    with open(OUT / name) as f:
        return json.load(f)


def save(fig, name):
    """!
    @brief Tighten and save a figure.
    @param fig Figure.
    @param name File name inside figures/.
    @return None.
    """
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=110)
    plt.close(fig)


def fig_profiles():
    """!
    @brief Figure 2: velocity and temperature across the half channel at the exit, and the local Nusselt number along it, from the numerical solver at three Rayleigh numbers.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    for ra, c in ((1.0, "#1f77b4"), (100.0, "#2ca02c"), (1.0e4, "#d62728")):
        r = cb.solve(ra, n_y=200, n_x=800, stretch=3.0, return_fields=True)
        y = r["y"] / 0.5
        axs[0].plot(y, r["u_exit"] / np.max(r["u_exit"]), color=c, label=f"Ra_b = {ra:g}")
        axs[1].plot(y, r["theta_exit"], color=c)
        axs[2].loglog(r["x"] / r["x"][-1], r["nu_local"], color=c)
    axs[0].set(xlabel="y / half gap (0 = centre, 1 = wall)", ylabel="u / u_max at the exit", title="velocity at the exit")
    axs[1].set(xlabel="y / half gap", ylabel="(T - T0)/(Tw - T0) at the exit", title="temperature at the exit")
    axs[2].set(xlabel="x / L", ylabel="local Nu_b", title="local Nusselt number along the wall", xlim=(1e-4, 1.0), ylim=(1e-3, 1e3))
    axs[0].legend(fontsize=8)
    for a in axs:
        a.grid(alpha=0.3)
    fig.suptitle("Numerical channel (marching solver, lib/channel_bl.py): low Ra_b fills the gap with warm air, high Ra_b leaves a cold core with boundary layers", fontsize=9)
    save(fig, "fig_02_channel_profiles.png")


def fig_nusselt():
    """!
    @brief Figure 3: the four composite correlations and the numerical solution against the channel Rayleigh number, with the two limits.
    @return None.
    """
    rows = load("correlations.json")
    ra = np.logspace(-1.5, 5.5, 200)
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, f in ch.CORRELATIONS.items():
        nu = np.array([f(x, 0.71) if f is ch.nu_churchill else f(x) for x in ra])
        axs[0].loglog(ra, nu, color=COL[name], label=name)
        axs[1].semilogx(ra, nu / np.array([ch.nu_bcr(x) for x in ra]), color=COL[name], label=name)
    axs[0].loglog(ra, ra / 24.0, "k--", linewidth=0.8, label="fully developed, Ra_b / 24")
    axs[0].loglog(ra, 0.59 * ra ** 0.25, "k:", linewidth=0.8, label="boundary layer, 0.59 Ra_b^(1/4)")
    axs[0].loglog([r["ra"] for r in rows], [r["numerical"] for r in rows], "ko", markersize=4, label="numerical (marching solver)")
    axs[1].semilogx([r["ra"] for r in rows], [r["numerical"] / ch.nu_bcr(r["ra"]) for r in rows], "ko", markersize=4, label="numerical")
    axs[1].axhline(1.0, color="k", linewidth=0.5)
    axs[0].set(xlabel="channel Rayleigh number Ra_b", ylabel="Nu_b = h b / k", title="Nusselt number of the isothermal channel", ylim=(1e-3, 30))
    axs[1].set(xlabel="channel Rayleigh number Ra_b", ylabel="Nu_b / Nu_b(Bar-Cohen and Rohsenow)", title="against the Bar-Cohen and Rohsenow composite", ylim=(0.75, 1.3))
    axs[0].legend(fontsize=7)
    for a in axs:
        a.grid(alpha=0.3, which="both")
    save(fig, "fig_03_nusselt_against_rayleigh.png")


def fig_coefficient():
    """!
    @brief Figure 5: the coefficient between the fins, the heat of an array and the optimum spacing against the gap, for the channel model and for the isolated-plate coefficient.
    @return None.
    """
    gaps = np.linspace(1.5, 40.0, 200)
    length, theta, t, hgt, k, w = 0.100, 40.0, 0.0015, 0.015, 204.0, 0.100
    h_ch = np.array([ch.exposed_h_channel(theta, g / 1000, t, hgt, length, k)["h_ch"] for g in gaps])
    h_pl = ch.h_plate_vertical(theta, length)
    q_ch, q_pl = [], []
    for g in gaps:
        n = (w + g / 1000) / (g / 1000 + t)
        q_ch.append(ch.array_heat(theta, n, g / 1000, t, hgt, length, k)["q"])
        q_pl.append(ch.array_heat(theta, n, g / 1000, t, hgt, length, k, channel=False)["q"])
    fig, axs = plt.subplots(1, 2, figsize=(11, 4))
    axs[0].plot(gaps, h_ch, color="#d62728", label="channel (Bar-Cohen and Rohsenow)")
    axs[0].axhline(h_pl, color="k", linestyle="--", label=f"isolated plate of the same height ({h_pl:.2f})")
    axs[0].set(xlabel="gap between the fins (mm)", ylabel="h on the fin faces (W/m²K)", title="L = 100 mm, 40 K above the air: the coefficient between the fins")
    axs[1].plot(gaps, q_ch, color="#d62728", label="with the channel effect")
    axs[1].plot(gaps, q_pl, color="k", linestyle="--", label="uniform isolated-plate h (what a uniform-h fin model gives)")
    i = int(np.argmax(q_ch))
    axs[1].plot(gaps[i], q_ch[i], "ro")
    axs[1].annotate(f"optimum {gaps[i]:.1f} mm", (gaps[i], q_ch[i]), textcoords="offset points", xytext=(8, -14), fontsize=8)
    axs[1].set(xlabel="gap between the fins (mm)", ylabel="heat of a 100 mm wide array (W)", title="fins 15 x 1.5 mm, aluminium: heat at a fixed width")
    for a in axs:
        a.grid(alpha=0.3)
        a.legend(fontsize=7)
    save(fig, "fig_05_coefficient_and_heat_against_gap.png")


def fig_leung():
    """!
    @brief Figure 6: the four arrays of Leung and others (plot values read from Yazicioglu and Yuncu 2009, Figures 6 and 7) against the channel model and the uniform-h model, as the shape Q(s)/Q(45 mm).
    @return None.
    """
    data = load("optimum_study.json")["leung"]
    fig, axs = plt.subplots(2, 2, figsize=(10, 6.4), sharex=True)
    for ax, key in zip(axs.ravel(), ("17_40", "17_20", "10_40", "10_20")):
        rows = data[key]
        s = [r["s"] for r in rows]
        ax.plot(s, [r["shape_meas"] for r in rows], "ko", label="measured (plot values)")
        ax.plot(s, [r["shape_ch"] for r in rows], "-s", color="#d62728", markersize=4, label="channel model")
        ax.plot(s, [r["shape_plate"] for r in rows], "--^", color="gray", markersize=4, label="uniform isolated-plate h")
        h, dt = key.split("_")
        ax.set_title(f"H = {h} mm, base {dt} K above the air", fontsize=9)
        ax.set_ylabel("Q(s) / Q(45 mm)")
        ax.grid(alpha=0.3)
    axs[1, 0].set_xlabel("fin spacing s (mm)")
    axs[1, 1].set_xlabel("fin spacing s (mm)")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle("Leung et al. (1985) arrays, L = 150 mm, t = 3 mm: shape of Q(s) (3 mm point: open front, outside the model)", fontsize=9)
    save(fig, "fig_06_leung_array.png")


def fig_optimum():
    """!
    @brief Figure 7: measured optimum spacing of eight published fin-array families against the channel model, the composite closed form and the fit of Yazicioglu and Yuncu.
    @return None.
    """
    rows = load("optimum_study.json")["table"]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for i, r in enumerate(rows):
        mid = 0.5 * (r["measured"][0] + r["measured"][1])
        for key, col, off in (("bcr", "#d62728", -0.15), ("closed_bcr", "#1f77b4", 0.0), ("closed_fit", "#2ca02c", 0.15)):
            v = r[key]
            ax.plot([i + off] * 2, [min(v) - 0.04, max(v) + 0.04], color=col, linewidth=5, alpha=0.7, solid_capstyle="butt")
        ax.plot([i, i], [r["measured"][0], r["measured"][1]], "k_", markersize=14, markeredgewidth=2)
    ax.plot([], [], color="#d62728", linewidth=5, alpha=0.7, label="channel model of the array (range over H and dT of the row)")
    ax.plot([], [], color="#1f77b4", linewidth=5, alpha=0.7, label="2.716 L / Ra_L^(1/4) (composite closed form)")
    ax.plot([], [], color="#2ca02c", linewidth=5, alpha=0.7, label="3.15 L / Ra_L^(1/4) (Yazicioglu and Yuncu fit)")
    ax.plot([], [], "k_", markersize=14, markeredgewidth=2, label="measured (Table 1)")
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"row {r['row']}\nL = {r['L']} mm" for r in rows], fontsize=7)
    ax.set(ylabel="optimum spacing (mm)", title="Optimum fin spacing: published measurements and the model")
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.3, axis="y")
    save(fig, "fig_07_optimum_spacing.png")


def fig_program():
    """!
    @brief Figure 8: the rise of the finned block with the channel coefficient against the uniform coefficient, against the gap, the fin height, the channel length and the power.
    @return None.
    """
    d = load("program_study.json")
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6))
    g = d["gap"]
    axs[0].plot([r["gap_mm"] for r in g], [r["d_pct"] for r in g], "o-", color="#d62728", label="FVM 1 mm")
    axs[0].plot([r["gap_mm"] for r in g], [r["d_phi_pct"] for r in g], "--", color="#1f77b4", label="FVM, phi form (proposal)")
    axs[0].plot([r["gap_mm"] for r in d["solid3d"]], [r["d_pct"] for r in d["solid3d"]], "s", color="k", label="3D solid 2 mm")
    axs[0].set(xlabel="gap (mm)", ylabel="rise with the channel coefficient / program - 1 (%)", title="gap (15 mm fins, L 40 mm)")
    axs[0].axvline(4.0, color="gray", linestyle=":")
    axs[0].text(4.1, 60, "program's\nwarning\n(4 mm)", fontsize=7, color="gray")
    axs[1].plot([r["height_mm"] for r in d["height"]], [r["d_pct"] for r in d["height"]], "o-", color="#d62728")
    axs[1].set(xlabel="fin height (mm)", title="fin height (gap 6.5 mm)")
    axs[2].plot([r["length_mm"] for r in d["length"]], [r["d_pct"] for r in d["length"]], "o-", color="#d62728")
    axs[2].set(xlabel="channel length (mm)", title="channel length (gap 6.5 mm)")
    axs[3].plot([r["theta_program"] for r in d["power"]], [r["d_pct"] for r in d["power"]], "o-", color="#d62728")
    axs[3].set(xlabel="block excess temperature (K)", title="temperature of the block (gap 6.5 mm)")
    for a in axs:
        a.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.suptitle("Program finned block (60 x 40 mm board, 3 W): difference of the rise of the hottest point between the channel coefficient and the uniform isolated-plate coefficient", fontsize=9)
    save(fig, "fig_08_program_error_against_gap.png")


def fig_rule():
    """!
    @brief Figure 9: the loss of the finned face against the channel Rayleigh number for every case of the grid, the thresholds, and the gap below which each rule warns.
    @return None.
    """
    d = load("warning_rule.json")
    pts = d["points"]
    ra = np.array([p["ra_b"] for p in pts])
    rho = np.array([p["rho"] for p in pts])
    gap = np.array([p["gap"] for p in pts]) * 1000
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    sc = axs[0].scatter(ra, 100 * (1 - rho), c=np.array([p["length"] for p in pts]) * 1000, s=8, cmap="viridis")
    axs[0].set_xscale("log")
    axs[0].axhline(10, color="k", linewidth=0.6)
    axs[0].axvline(50, color="#d62728", linestyle="--", label="Ra_b = 50")
    axs[0].axvline(90, color="#d62728", linestyle=":", label="Ra_b = 90 (no case missed)")
    axs[0].set(xlabel="channel Rayleigh number Ra_b", ylabel="loss of the finned face, 1 - h_exp(channel)/h_exp(program) (%)", title="1080 cases: height, length, temperature, gap", ylim=(-25, 100))
    fig.colorbar(sc, ax=axs[0], label="channel length (mm)")
    axs[0].legend(fontsize=7)
    th = np.linspace(10, 100, 40)
    for length in (0.02, 0.04, 0.1, 0.2):
        gc = []
        for t in th:
            gg = np.linspace(1e-3, 40e-3, 800)
            r = np.array([ch.ra_channel(t, x, length) for x in gg])
            gc.append(1000 * gg[np.searchsorted(r, 90.0)])
        axs[1].plot(th, gc, label=f"L = {1000 * length:g} mm")
    axs[1].axhline(4.0, color="gray", linestyle=":")
    axs[1].text(60, 4.15, "today's rule: gap < 4 mm", fontsize=7, color="gray")
    axs[1].set(xlabel="block excess temperature (K)", ylabel="gap below which the rule Ra_b < 90 warns (mm)", title="the warning threshold depends on L and on the temperature")
    axs[1].legend(fontsize=7)
    for a in axs:
        a.grid(alpha=0.3)
    save(fig, "fig_09_warning_rule.png")


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_profiles()
    fig_nusselt()
    fig_coefficient()
    fig_leung()
    fig_optimum()
    fig_program()
    fig_rule()
