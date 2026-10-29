#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the plate-level investigation (numbers 04 and above; 01 to 03 are drawn by `make_diagrams.py`).
@details Needs out/board_effect.json, out/finned_block.json (`study_board_effect.py`, `study_finned_block.py`) and, for the 2D points, out/plate2d.json (`study_plate2d.py`);
         a missing file leaves its panel out. Figure 09 runs one coarse 2D case (about one minute).
         Run: .venv/bin/python research/plate-h-level/scripts/make_figures.py (from the repository root).
"""

import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                        # noqa: E402
import plate2d as p2                                      # noqa: E402
import similarity as sim                                  # noqa: E402
from pcbthermal import convection                         # noqa: E402

import study_air_data as ad                               # noqa: E402

FIG = os.path.join(os.path.dirname(HERE), "figures")
OUT = os.path.join(os.path.dirname(HERE), "out")
COL = {"general": "#1f77b4", "laminar": "#2ca02c", "bl": "#7f7f7f", "bl_le": "#8c564b", "mcadams": "#d62728", "squire": "#bcbd22"}
PR = 0.71


def load(name):
    """!
    @brief Read a JSON file of out/ or None.
    @param name File name.
    @return The data or None.
    """
    path = os.path.join(OUT, name)
    return json.load(open(path)) if os.path.exists(path) else None


def save(fig, name):
    """!
    @brief Save a figure.
    @param fig Figure.
    @param name File name in figures/.
    @return None.
    """
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, name), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig04_similarity():
    """!
    @brief Figure 4: the similarity profiles at Pr 0.72 with Ostrach's tabulated values, and the coefficient C(Pr) with the fits.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.0))
    ax = axs[0]
    e, fp, th = sim.profile(0.72, eta_max=6.0, n=600)
    ax.plot(e, th, color="#d62728", label="temperature H = (T - Tinf)/(Tw - Tinf)")
    ax.plot(e, fp * 2.0, color="#1f77b4", label="velocity 2 F'(eta) (scaled x 2)")
    # Table I(b) of Ostrach, read from the page image: eta, F', H
    tab = [(0.5, .2246, .7493), (1.0, .2759, .5168), (1.5, .2363, .3281), (2.0, .1697, .1945), (0.0, 0.0, 1.0)]
    ax.plot([t[0] for t in tab], [t[2] for t in tab], "o", color="#d62728", mfc="none", label="Ostrach Table I(b), H")
    ax.plot([t[0] for t in tab], [2 * t[1] for t in tab], "s", color="#1f77b4", mfc="none", label="Ostrach Table I(b), F'")
    ax.set_xlabel("eta = (y/x) (Gr_x/4)^(1/4)")
    ax.set_title("a. similarity solution, Pr 0.72 (own collocation solver)", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax = axs[1]
    prs = np.logspace(-1, 2, 25)
    c = [sim.coefficient(p, "bvp") for p in prs]
    ax.semilogx(prs, c, "k-", lw=2, label="exact (own solver)")
    ax.semilogx(prs, [sim.churchill_usagi(p) for p in prs], "--", color=COL["laminar"], label="0.670/[1+(0.492/Pr)^(9/16)]^(4/9)")
    ax.semilogx(prs, [4 / 3 * 0.508 * (p / (0.952 + p)) ** 0.25 for p in prs], ":", color=COL["squire"], lw=2, label="Squire integral, 4/3 x 0.508 [Pr/(0.952+Pr)]^(1/4)")
    ax.axhline(0.59, color=COL["mcadams"], lw=1)
    ax.text(0.11, 0.595, "0.59 (not a function of Pr)", color=COL["mcadams"], fontsize=7)
    ax.axvspan(0.69, 0.73, color="#cccccc", alpha=0.6)
    ax.text(0.7, 0.30, "air", fontsize=7, ha="center")
    ax.set_xlabel("Prandtl number")
    ax.set_ylabel("C in Nu = C Ra^(1/4)")
    ax.set_title("b. the coefficient of the plate-average Nusselt number", fontsize=9)
    ax.legend(fontsize=7, loc="lower right")
    ax.grid(alpha=0.3, which="both")
    save(fig, "fig_04_similarity_solution_and_coefficient.png")


def fig05_levels_and_data():
    """!
    @brief Figure 5: Nu / Ra^(1/4) against Ra for every level, the air measurements (plot values) and the 2D numerical points.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
    ra = np.logspace(2, 12, 400)
    ax = axs[0]
    for k in ("general", "laminar", "bl", "mcadams"):
        ax.semilogx(ra, L.nu_level(k, ra, PR) / ra ** 0.25, color=COL[k], lw=2, label=L.LABELS[k])
    for name, pts, mk in (("King", ad.KING, "D"), ("Cheesewright", ad.CHEESEWRIGHT, "s"), ("Jakob", ad.JAKOB, "v")):
        ax.semilogx([p[0] for p in pts], [p[1] / p[0] ** 0.25 for p in pts], mk, mfc="none", color="k", ms=5, label=f"air, {name} (plot values)")
    d = load("plate2d.json")
    if d:
        base = [r for r in d if r["config"] in ("base", "wide")]
        ax.semilogx([r["ra"] for r in base], [r["nu"] / r["ra"] ** 0.25 for r in base], "*", color="#ff7f0e", ms=11, label="2D numerical plate (own solver)")
    ax.axvspan(6e4, 3e7, color="#dddddd", alpha=0.5)
    ax.text(1.4e5, 0.2, "boards\n40 to 200 mm", fontsize=7)
    ax.set_ylim(0.1, 1.4)
    ax.set_xlabel("Rayleigh number of the plate height")
    ax.set_ylabel("Nu / Ra^(1/4)")
    ax.set_title("a. the levels and the measurements (Pr 0.71 and 0.70)", fontsize=9)
    ax.legend(fontsize=6.5, loc="upper left")
    ax.grid(alpha=0.3, which="both")
    ax = axs[1]
    r = np.logspace(3.5, 8, 300)
    g = L.nu_level("general", r, PR)
    for k in ("laminar", "bl", "mcadams"):
        ax.semilogx(r, 100 * (L.nu_level(k, r, PR) / g - 1), color=COL[k], lw=2, label=L.LABELS[k])
    ax.axvspan(6e4, 3e7, color="#dddddd", alpha=0.5)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Rayleigh number")
    ax.set_ylabel("difference of Nu to the general form (%)")
    ax.set_title("b. how far the levels are from the program's default", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, which="both")
    save(fig, "fig_05_levels_against_rayleigh_and_data.png")


def fig06_h_against_height():
    """!
    @brief Figure 6: the convection coefficient of a vertical face against its height for each level, 10, 30 and 60 K above 20 degC, with the 2D numerical points.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(10.6, 3.6), sharey=False)
    d = load("plate2d.json")
    h = np.logspace(np.log10(0.02), np.log10(0.4), 60)
    for ax, dt in zip(axs, (10.0, 30.0, 60.0)):
        for k in ("general", "laminar", "bl", "mcadams"):
            ax.semilogx(h * 1e3, [L.h_vertical(k, 20.0 + dt, 20.0, x)[0] for x in h], color=COL[k], lw=2, label=L.LABELS[k])
        if d:
            props = convection.air_properties(20.0 + dt / 2)
            for r in d:
                if r["config"] == "base":
                    # height that gives this Ra at this temperature difference, and the coefficient of the 2D solution there
                    ra1 = convection.rayleigh(dt, 1.0, props)
                    x = (r["ra"] / ra1) ** (1.0 / 3.0)
                    if 0.015 < x < 0.5:
                        ax.plot(x * 1e3, r["nu"] * props["k"] / x, "*", color="#ff7f0e", ms=10)
        ax.set_title(f"{dt:.0f} K above the air (convection only)", fontsize=9)
        ax.set_xlabel("height of the face (mm)")
        ax.set_xticks([20, 50, 100, 200, 400])
        ax.set_xticklabels(["20", "50", "100", "200", "400"])
        ax.minorticks_off()
        ax.grid(alpha=0.3, which="both")
    axs[0].set_ylabel("h (W/m2K)")
    axs[0].legend(fontsize=6.5)
    axs[2].plot([], [], "*", color="#ff7f0e", ms=10, label="2D numerical plate")
    axs[2].legend(fontsize=6.5)
    save(fig, "fig_06_coefficient_against_height.png")


def fig07_effect_on_rise():
    """!
    @brief Figure 7: the change of the rise of boards (vertical, computed h) and of the finned block with the level.
    @return None.
    """
    be, fb = load("board_effect.json"), load("finned_block.json")
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 4.0))
    ax = axs[0]
    if be:
        names = [r["case"].replace(" (vertical)", "") for r in be]
        x = np.arange(len(be))
        w = 0.2
        for j, k in enumerate(("laminar", "bl", "mcadams")):
            ax.bar(x + (j - 1) * w, [100 * (r[k]["rise"] / r["general"]["rise"] - 1) for r in be], w, color=COL[k], label=L.LABELS[k] + " (with radiation)")
        ax.plot(x + w * 1.0, [100 * (r["conv_mcadams"]["rise"] / r["conv_general"]["rise"] - 1) for r in be], "k_", ms=8, label="0.59, convection only")
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=70, ha="right", fontsize=6.5)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("rise of the hottest point against the general form (%)")
    ax.set_title("a. vertical boards, computed h, radiation included", fontsize=9)
    ax.legend(fontsize=6.5)
    ax.grid(alpha=0.3, axis="y")
    ax = axs[1]
    if fb:
        gaps = [r["gap_mm"] for r in fb]
        base = [r["uniform_laminar"]["rise"] for r in fb]
        for k, lab, c, ls in (("uniform_general", "uniform, general form", COL["general"], "-"), ("uniform_bl", "uniform, exact BL", COL["bl"], "-"), ("uniform_mcadams", "uniform, 0.59", COL["mcadams"], "-"),
                              ("channel_059", "channel composite, plate limit 0.59", COL["mcadams"], "--"), ("channel_exact", "channel composite, plate limit 0.5157", COL["bl"], "--")):
            ax.plot(gaps, [100 * (r[k]["rise"] / b - 1) for r, b in zip(fb, base)], ls, color=c, lw=2, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("gap between the fins (mm)")
    ax.set_ylabel("rise against the uniform laminar form (%)")
    ax.set_title("b. the finned block (3 W, 40 mm channels, convection only)", fontsize=9)
    ax.legend(fontsize=6.5)
    ax.set_ylim(-10, 30)
    ax.grid(alpha=0.3)
    save(fig, "fig_07_effect_on_the_rise.png")


def fig08_field():
    """!
    @brief Figure 8: isotherms and streamlines of the 2D numerical plate at Ra = 1e5 (coarse grid), the thing the plate level summarises.
    @return None.
    """
    m = p2.Plate2D(1e5, PR, nx=60, ny_plate=50, ny_below=20, ny_above=30)
    r = m.run(dt=3.0 * m.x[1] ** 2, max_steps=120000, check=5000, tol=5e-5)
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 5.2))
    X, Y = np.meshgrid(m.x, m.y, indexing="ij")
    ax = axs[0]
    cs = ax.contourf(X, Y, m.T, levels=np.linspace(0, 1, 21), cmap="YlOrRd")
    ax.contour(X, Y, m.T, levels=[0.05, 0.1, 0.2, 0.4, 0.6, 0.8], colors="k", linewidths=0.5)
    ax.plot([0, 0], [0, 1], color="k", lw=4)
    ax.set_xlim(0, 0.6)
    ax.set_ylim(-0.3, 1.6)
    ax.set_aspect("equal")
    ax.set_title(f"a. temperature (Ra 1e5, Nu {r['nu']:.2f})", fontsize=9)
    ax.set_xlabel("x / L")
    ax.set_ylabel("y / L")
    fig.colorbar(cs, ax=ax, shrink=0.7)
    ax = axs[1]
    ax.contour(X, Y, m.psi, levels=np.linspace(m.psi.min(), 0, 25), colors="#1f77b4", linewidths=0.7)
    ax.plot([0, 0], [0, 1], color="k", lw=4)
    ax.set_xlim(0, 1.5)
    ax.set_ylim(-0.6, 2.2)
    ax.set_aspect("equal")
    ax.set_title("b. streamlines: air drawn in from the side and from below", fontsize=9)
    ax.set_xlabel("x / L")
    save(fig, "fig_08_computed_field_of_the_plate.png")
    y, nu = m.nusselt_local()
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    ax.semilogy(y, nu, "k-", label="2D numerical, Ra 1e5")
    xx = y[1:-1]
    c = 3.0 / 4.0 * sim.coefficient(PR, "bvp")                                  # local coefficient of the similarity solution, 0.3868
    ax.semilogy(xx, c * 1e5 ** 0.25 * xx ** -0.25, "--", color=COL["bl"], label="similarity, 0.3868 Ra^(1/4) (y/L)^(-1/4)")
    ax.set_xlabel("y / L (from the leading edge)")
    ax.set_ylabel("h L / k, local")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, which="both")
    save(fig, "fig_09_local_nusselt_number.png")


if __name__ == "__main__":
    fig04_similarity()
    fig05_levels_and_data()
    fig06_h_against_height()
    fig07_effect_on_rise()
    fig08_field()
