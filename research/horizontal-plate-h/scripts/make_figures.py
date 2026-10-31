#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the horizontal plate: the evidence ranges against the Rayleigh numbers of the boards, the levels in Nu and in ratio, the numerical plates against the levels, the coupling of the two faces, the local Nusselt numbers, the computed fields, and the effect on the boards.
@details Reads out/correlations.json (study_correlations.py), out/plate_h2d.json and out/fields_*.npz (study_plate_h2d.py) and out/board_effect.json (study_board_effect.py);
         a figure whose data is missing is skipped. Writes figures/fig_05 ... fig_11 (the numbers 01 to 04 belong to `make_diagrams.py`, one numbering for both).
         Run the studies first, then: .venv/bin/python research/horizontal-plate-h/scripts/make_figures.py (from the repository root).
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
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
import correlations as C                                           # noqa: E402

OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"
RED, BLUE, GREEN, GREY, ORANGE = "#d1495b", "#2e86c1", "#2a9d6f", "#6b7785", "#e08a1e"


def load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return Parsed JSON or None when missing.
    """
    p = OUT / name
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def reliable(r):
    """!
    @brief A numerical case that is fit to be plotted: finite, converged, and with the energy balance between 0.8 and 1.25 (the Ra = 1e5 strip cases are drifting, blow up or balance at 0.70 and are left out).
    @param r One entry of out/plate_h2d.json.
    @return bool.
    """
    return bool(np.isfinite(r["nu_up"]) and np.isfinite(r["nu_down"]) and r["converged"] and 0.8 <= r["balance"] <= 1.25)


def save(fig, name):
    """!
    @brief Save a figure with the common settings.
    @param fig Figure.
    @param name File name in figures/.
    @return None.
    """
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / name, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig_evidence():
    """!
    @brief Figure 5: the Rayleigh ranges of the published data sets (Jaffer's Table 1, read from the paper) against the range of the boards of the program (squares of 40 to 200 mm, 10 to 60 K, L = A/P).
    @return None.
    """
    sets = [("up", "Goldstein et al. 1973, naphthalene sublimation, air (Sc 2.5)", 1.6, 6.2e3), ("up", "Lloyd and Moran 1974, electrochemical, Sc 2200", 2.6e4, 1.6e9),
            ("up", "Fujii and Imura 1972, 5 x 10 cm, water, side walls", 5.7e6, 1.3e9), ("up", "Fujii and Imura 1972, 30 x 15 cm, water, side walls", 4.1e9, 4.8e11),
            ("down", "Goldstein and Lau 1983, 2.6-20 cm squares, air", 2.5e2, 4.5e3), ("down", "Faw and Dullforce 1982, 18.1 cm disc, air", 1.1e6, 1.6e6),
            ("down", "Aihara et al., 25 x 35 cm, air", 7.2e6, 1.0e7), ("down", "Fujii and Imura 1972, 5 x 10 cm, water", 1.8e7, 4.5e9)]
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    for k, (face, label, lo, hi) in enumerate(sets):
        ax.plot([lo, hi], [k, k], color=RED if face == "up" else BLUE, linewidth=6, solid_capstyle="butt")
        ax.text(hi * 1.5, k, label, va="center", fontsize=7)
    ax.axvspan(9.7e2, 5.0e5, ymin=0.0, ymax=0.5, color=RED, alpha=0.15)
    ax.axvspan(7.7e3, 4.0e6, ymin=0.5, ymax=1.0, color=BLUE, alpha=0.15)
    ax.text(1.2e3, -0.55, "boards, upper face: squares 40-200 mm, 10-60 K, Ra of L = A/P", fontsize=7, color=RED, va="center")
    ax.text(1.0e4, len(sets) - 0.05, "boards, lower face: the same in Jaffer's metric L_R = 2 L (squares)", fontsize=7, color=BLUE, va="center")
    ax.set_xscale("log"); ax.set_xlim(1, 1e16); ax.set_ylim(-0.7, len(sets) + 0.3)
    ax.set_yticks([]); ax.set_xlabel("Rayleigh number of the characteristic length used by each source")
    ax.set_title("Evidence for the horizontal faces (ranges of Jaffer 2023, Table 1, each in its own metric)", fontsize=8.5)
    ax.grid(axis="x", alpha=0.3)
    save(fig, "fig_05_evidence_ranges_against_the_boards.png")


def fig_levels(corr):
    """!
    @brief Figure 6: Nu of every level against Ra (L = A/P) for the upper and lower face, and the ratio to the program.
    @param corr Parsed out/correlations.json.
    @return None.
    """
    ras = np.logspace(1, 8, 200)
    fig, axs = plt.subplots(2, 2, figsize=(10.4, 7.2))
    ax = axs[0, 0]
    ax.loglog(ras, C.program_up(ras), color="k", label="program: 0.54 Ra^(1/4), 0.15 Ra^(1/3) above 1e7")
    ax.loglog(ras, C.jaffer_up(ras), color=RED, label="Jaffer (30): [0.642 + 0.370 Ra^(1/6)]^2")
    ax.set_title("upper face (hot face looking up), L = A/P", fontsize=8.5)
    ax = axs[0, 1]
    ax.loglog(ras, C.program_down(ras), color="k", label="program: 0.27 Ra^(1/4)")
    ax.loglog(ras, C.jaffer_down(ras), color=BLUE, label="Jaffer (46, 51), long strip (q = 1)")
    ax.loglog(ras, C.jaffer_down_shape(ras, 2.0), color=BLUE, linestyle="--", label="Jaffer, square (q = 2)")
    ax.loglog(ras, C.jaffer_down_shape(ras, 4 / np.pi), color=BLUE, linestyle=":", label="Jaffer, disc (q = 4/pi)")
    ax.loglog(ras, C.schulenberg_strip(ras), color=GREEN, label="Schulenberg strip (92), as printed")
    ax.loglog(ras, C.schulenberg_strip(ras, jaffer_coefficients=True), color=GREEN, linestyle="--", label="Schulenberg strip, Jaffer's coefficients")
    ax.loglog(ras, C.schulenberg_disc(ras), color=ORANGE, label="Schulenberg disc (94), L = R/2")
    ax.set_title("lower face (hot face looking down), L = A/P", fontsize=8.5)
    for ax in axs[0]:
        ax.axvspan(9.7e2, 5.0e5, color=GREEN, alpha=0.12)
        ax.set_xlabel("Ra of L = A/P"); ax.set_ylabel("Nu = h L / k"); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=6.3)
    ax = axs[1, 0]
    ax.semilogx(ras, C.jaffer_up(ras) / C.program_up(ras), color=RED, label="Jaffer / program")
    ax.set_title("upper face: level / program", fontsize=8.5)
    ax = axs[1, 1]
    for fn, lab, st in ((C.jaffer_down, "Jaffer strip", "-"), (lambda r: C.jaffer_down_shape(r, 2.0), "Jaffer square", "--"), (lambda r: C.jaffer_down_shape(r, 4 / np.pi), "Jaffer disc", ":")):
        ax.semilogx(ras, fn(ras) / C.program_down(ras), color=BLUE, linestyle=st, label=lab)
    ax.semilogx(ras, C.schulenberg_strip(ras) / C.program_down(ras), color=GREEN, label="Schulenberg strip")
    ax.semilogx(ras, C.schulenberg_disc(ras) / C.program_down(ras), color=ORANGE, label="Schulenberg disc")
    ax.set_title("lower face: level / program", fontsize=8.5)
    for ax in axs[1]:
        ax.axhline(1.0, color="k", linewidth=0.6); ax.axvspan(9.7e2, 5.0e5, color=GREEN, alpha=0.12)
        ax.set_xlabel("Ra of L = A/P"); ax.set_ylabel("ratio"); ax.grid(alpha=0.3); ax.legend(fontsize=6.5)
        ax.set_ylim(0.4, 2.3)
    fig.tight_layout()
    save(fig, "fig_06_levels_in_nu_and_in_ratio.png")


def fig_numerics(res, corr):
    """!
    @brief Figure 7: the numerical plates (strip and disc, isolated face and both faces hot) against the correlations, for the upper and the lower face.
    @param res Parsed out/plate_h2d.json.
    @param corr Parsed out/correlations.json (unused, kept for symmetry).
    @return None.
    """
    ras = np.logspace(2, 6, 100)
    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.6))
    for ax, face in zip(axs, ("up", "down")):
        if face == "up":
            ax.loglog(ras, C.program_up(ras), "k", label="program")
            ax.loglog(ras, C.jaffer_up(ras), color=RED, label="Jaffer (30)")
        else:
            ax.loglog(ras, C.program_down(ras), "k", label="program")
            ax.loglog(ras, C.jaffer_down(ras), color=BLUE, label="Jaffer strip")
            ax.loglog(ras, C.jaffer_down_shape(ras, 4 / np.pi), color=BLUE, linestyle=":", label="Jaffer disc")
            ax.loglog(ras, C.schulenberg_strip(ras), color=GREEN, label="Schulenberg strip")
            ax.loglog(ras, C.schulenberg_disc(ras), color=ORANGE, label="Schulenberg disc")
        for geom, mk in (("strip", "o"), ("disc", "s")):
            for faces, fill in (("both", True), (face, False)):
                pts = [(r["ra_l"], r["nu_" + face]) for r in res if r["geometry"] == geom and r["faces"] == faces and r["grid"] == "base" and reliable(r)]
                if pts:
                    pts.sort()
                    ax.loglog(*zip(*pts), marker=mk, linestyle="", markerfacecolor=(GREY if fill else "none"), markeredgecolor=GREY, markersize=7,
                              label=f"solver, {geom}, " + ("both faces hot" if faces == "both" else "isolated face"))
        ax.set_xlabel("Ra of L = A/P"); ax.set_ylabel("Nu = h L / k"); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=6.2)
        ax.set_title({"up": "upper face", "down": "lower face"}[face] + " (symmetric steady solution)", fontsize=8.5)
    save(fig, "fig_07_numerical_plates_against_the_levels.png")


def fig_coupling(res):
    """!
    @brief Figure 8: Nu of a face of the thin free board (both faces hot) divided by Nu of the same face alone, for the strip and the disc.
    @param res Parsed out/plate_h2d.json.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for geom, mk in (("strip", "o"), ("disc", "s")):
        for face, col in (("up", RED), ("down", BLUE)):
            pts = []
            for r in res:
                if r["geometry"] == geom and r["faces"] == "both" and r["grid"] == "base" and reliable(r):
                    alone = [q for q in res if q["geometry"] == geom and q["faces"] == face and q["ra_l"] == r["ra_l"] and q["grid"] == "base" and reliable(q)]
                    if alone and alone[0]["nu_" + face] > 0 and np.isfinite(alone[0]["nu_" + face]):
                        pts.append((r["ra_l"], r["nu_" + face] / alone[0]["nu_" + face]))
            if pts:
                pts.sort()
                ax.semilogx(*zip(*pts), marker=mk, color=col, label=f"{geom}, {face} face")
    ax.axhline(1.0, color="k", linewidth=0.6)
    ax.set_xlabel("Ra of L = A/P"); ax.set_ylabel("Nu(both faces hot) / Nu(face alone)"); ax.grid(alpha=0.3); ax.legend(fontsize=7)
    ax.set_title("What the other face does to a face (solver, steady symmetric flow)", fontsize=8.5)
    save(fig, "fig_08_the_other_face.png")


def fig_local(res):
    """!
    @brief Figure 9: the local Nusselt number along the half plate of the strip with both faces hot, upper and lower, at each Rayleigh number run.
    @param res Parsed out/plate_h2d.json.
    @return None.
    """
    rows = [r for r in res if r["geometry"] == "strip" and r["faces"] == "both" and r["grid"] == "base" and reliable(r)]
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.2), sharey=True)
    for ax, face in zip(axs, ("up", "down")):
        for r, c in zip(sorted(rows, key=lambda q: q["ra_l"]), (GREEN, BLUE)):
            ax.plot(r["x"], r["local_" + face], color=c, label=f"Ra {r['ra_l']:.0e}")
        ax.set_xlabel("x / a (0 = centre, 1 = edge)"); ax.set_yscale("log"); ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=7)
        ax.set_title({"up": "upper face", "down": "lower face"}[face], fontsize=8.5)
    axs[0].set_ylabel("local Nu = h a / k")
    save(fig, "fig_09_local_nusselt_number_of_the_strip.png")


def fig_fields():
    """!
    @brief Figure 10: isotherms and streamlines of the strip with both faces hot at the highest Rayleigh number run and of the disc, near the plate.
    @return None.
    """
    files = sorted(OUT.glob("fields_strip_*_both.npz"))
    files = [f for f in files if "1e+03" in f.name or "1e+04" in f.name] + [f for f in sorted(OUT.glob("fields_disc_*_both.npz")) if "1e+04" in f.name]
    if not files:
        return
    fig, axs = plt.subplots(1, len(files), figsize=(3.6 * len(files), 5.0))
    axs = np.atleast_1d(axs)
    for ax, f in zip(axs, files):
        d = np.load(f)
        x, y, T, psi = d["x"], d["y"], d["T"], d["psi"]
        X, Y = np.meshgrid(x, y, indexing="ij")
        ax.contourf(X, Y, T, levels=np.linspace(0, 1, 21), cmap="YlOrRd")
        ax.contour(X, Y, psi, levels=14, colors="k", linewidths=0.5)
        ax.plot([0, x[int(d["ip"])]], [0, 0], color="k", linewidth=3)
        ax.set_xlim(0, 3); ax.set_ylim(-2, 4); ax.set_aspect("equal")
        ax.set_title(f.stem.replace("fields_", "").replace("_both", "").replace("_", " Ra_L = ", 1) + (" (x = radius, Ra_R = 8 Ra_L)" if bool(d["axisym"]) else ""), fontsize=7.5)
        ax.set_xlabel("x / L"); ax.set_ylabel("y / L")
    save(fig, "fig_10_computed_fields_of_the_horizontal_plate.png")


def fig_board(be):
    """!
    @brief Figure 11: the change of the rise of the boards and of the finned block (fins down) with each level.
    @param be Parsed out/board_effect.json.
    @return None.
    """
    keys = ["jaffer", "up x0.6", "down x1.3", "up x0.6 down x1.3", "up x1.2", "down x0.7"]
    fig, axs = plt.subplots(1, 2, figsize=(11.0, 4.6), sharey=True)
    for ax, pref, title in ((axs[0], "", "convection and radiation (the program's default)"), (axs[1], "conv_", "convection only (emissivity 0)")):
        rows = [r for r in be if (pref + "program") in r]
        w = 0.8 / len(keys)
        for j, k in enumerate(keys):
            vals = [100 * (r[pref + k]["rise"] / r[pref + "program"]["rise"] - 1) for r in rows]
            ax.bar(np.arange(len(rows)) + j * w, vals, w, label=k)
        ax.set_xticks(np.arange(len(rows)) + 0.4 - w / 2)
        ax.set_xticklabels([r["case"].replace(" (horizontal)", "").replace(" square", "") for r in rows], rotation=70, ha="right", fontsize=6.5)
        ax.axhline(0, color="k", linewidth=0.6); ax.grid(axis="y", alpha=0.3); ax.set_title(title, fontsize=8.5)
    axs[0].set_ylabel("change of the rise (%)"); axs[0].legend(fontsize=6.5)
    save(fig, "fig_11_effect_on_the_rise_of_the_boards.png")


if __name__ == "__main__":
    corr, res, be = load("correlations.json"), load("plate_h2d.json"), load("board_effect.json")
    fig_evidence()
    if corr:
        fig_levels(corr)
    if res:
        fig_numerics(res, corr)
        fig_coupling(res)
        fig_local(res)
        fig_fields()
    if be:
        fig_board(be)
