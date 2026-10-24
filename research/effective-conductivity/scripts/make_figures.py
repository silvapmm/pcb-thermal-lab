"""!
@file make_figures.py
@brief Data figures of the effective-conductivity investigation, drawn from the JSON files that the studies write in out/ (run the studies first; make_diagrams.py draws the schematics).
@details Writes figures/fig_03_layer_orders_k_eff.png, fig_04_size_location_biot.png, fig_06_lee_spreading.png, fig_07_program_vs_coupon.png, fig_08_muzychka_and_the_thickness_rule.png and fig_10_natural_convection_forms.png.
         Run: .venv/bin/python research/effective-conductivity/scripts/make_figures.py (from the repository root; a few seconds).
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUTDIR = HERE.parent / "out"
FIG = HERE.parent / "figures"
C = {"paper": "#6b7280", "this": "#1d4ed8", "fvm": "#1f2937", "fdm": "#9ca3af", "solid3d": "#059669", "lumped": "#d97706", "analytic": "#7c3aed", "2d": "#dc2626"}


def load(name):
    """!
    @brief Read one study result.
    @param name File name without extension.
    @return dict The JSON content.
    """
    return json.loads((OUTDIR / f"{name}.json").read_text())


def layer_orders(cu):
    """!
    @brief Effective conductivity of the five layer orders: the paper against the independent solver, with the series and parallel limits.
    @param cu Content of culham_1998.json.
    @return None.
    """
    cases = sorted(cu["layers"], key=int)
    names = {"1": "Cu-Cu-FR4x3", "2": "Cu-FR4x3-Cu", "3": "FR4-Cu-FR4-Cu-FR4", "4": "FR4-Cu-Cu-FR4", "5": "FR4x3-Cu-Cu"}
    x = np.arange(len(cases))
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(x - 0.2, [cu["layers"][c]["paper"] for c in cases], 0.4, color=C["paper"], label="paper (text or plot)")
    ax.bar(x + 0.2, [cu["layers"][c]["k_eff"] for c in cases], 0.4, color=C["this"], label="independent 3D solver")
    for lim, lab in ((cu["limits"]["in_plane"], "in-plane 17.6"), (cu["limits"]["geometric"], "geometric mean 2.7"), (cu["limits"]["cross_plane"], "cross-plane 0.42")):
        ax.axhline(lim, color="k", lw=0.8, ls="--")
        ax.text(len(cases) - 0.45, lim + 0.2, lab, ha="right", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([f"case {c}\n{names[c]}" for c in cases], fontsize=7)
    ax.set_ylabel("effective conductivity (W/mK)")
    ax.set_title("Order of the layers: same copper, same FR4, k_e from 15 to 5 W/mK; the solver agrees within 2 to 6 %", fontsize=9)
    ax.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.0, 0.82))
    fig.tight_layout()
    fig.savefig(FIG / "fig_03_layer_orders_k_eff.png", dpi=110)
    plt.close(fig)


def size_location_biot(cu):
    """!
    @brief Effective conductivity against the relative source size, the source position and the film coefficient.
    @param cu Content of culham_1998.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
    eps = sorted(cu["sizes"], key=float)
    axs[0].plot([float(e) for e in eps], [cu["sizes"][e]["paper"] for e in eps], "s--", color=C["paper"], label="paper")
    axs[0].plot([float(e) for e in eps], [cu["sizes"][e]["k_eff"] for e in eps], "o-", color=C["this"], label="independent solver")
    axs[0].axhline(cu["limits"]["cross_plane"], color="k", lw=0.7, ls=":")
    axs[0].set_xlabel("epsilon = source area / board area")
    axs[0].set_ylabel("k_e (W/mK)")
    axs[0].set_title("source size: a maximum near 25 %", fontsize=9)
    axs[0].legend(fontsize=8)
    names = list(cu["location"])
    axs[1].bar(np.arange(len(names)) - 0.2, [cu["location"][n]["paper"] for n in names], 0.4, color=C["paper"], label="paper (+42 %, +67 % of 8.28)")
    axs[1].bar(np.arange(len(names)) + 0.2, [cu["location"][n]["k_eff"] for n in names], 0.4, color=C["this"], label="independent solver")
    axs[1].set_xticks(range(len(names)))
    axs[1].set_xticklabels(["source on an edge\n(assumed layout)", "source in a corner\n(assumed layout)"], fontsize=7)
    axs[1].set_title("source position: layout assumed, not shown in text", fontsize=9)
    axs[1].legend(fontsize=7)
    bi = sorted(cu["biot"], key=float)
    axs[2].semilogx([cu["biot"][h]["Bi"] for h in bi], [cu["biot"][h]["k_eff"] for h in bi], "o-", color=C["this"], label="independent solver")
    axs[2].axhspan(4.7, 4.9, color=C["paper"], alpha=0.3, label="paper: about 4.8 above Bi 100")
    axs[2].axhline(8.6, color=C["paper"], ls="--", lw=1, label="paper: about 8.6 at the lowest Bi")
    axs[2].set_xlabel("Biot number h L / k1 (L = 25 mm, k1 = 0.4)")
    axs[2].set_title("film coefficient: k_e falls from about 8 to 5", fontsize=9)
    axs[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_size_location_biot.png", dpi=110)
    plt.close(fig)


def lee(le):
    """!
    @brief Constriction resistance of the three source positions: the article, the 3D solver and the thin plate.
    @param le Content of lee_spreading.json.
    @return None.
    """
    pos = list(le)
    x = np.arange(len(pos))
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.bar(x - 0.27, [le[p]["paper"] for p in pos], 0.27, color=C["paper"], label="article (Seri Lee)")
    ax.bar(x, [le[p]["3d"] for p in pos], 0.27, color=C["this"], label="independent 3D solver")
    ax.bar(x + 0.27, [le[p]["2d"] for p in pos], 0.27, color=C["2d"], label="thin plate (k t), 2D")
    for k, p in enumerate(pos):
        ax.text(k, max(le[p]["paper"], le[p]["3d"]) + 0.05, f"{100 * (le[p]['3d'] / le[p]['paper'] - 1):+.1f} %", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(pos)
    ax.set_ylabel("maximum constriction resistance (K/W)")
    ax.set_title("Seri Lee's plate: centre 0.66, edge 1.29, corner 2.38 K/W (the article claims about 5 %)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_lee_spreading.png", dpi=110)
    plt.close(fig)


def program_vs_coupon(pc):
    """!
    @brief Error of the five models of the program against the independent solver on the Cu / FR4 / Cu coupon, against the source size.
    @param pc Content of program_vs_coupon.json.
    @return None.
    """
    sides = sorted(pc, key=float)
    eps = [(float(s) / 50.0) ** 2 for s in sides]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for m, mk in (("fvm", "o"), ("fdm", "s"), ("solid3d", "^"), ("lumped", "D"), ("analytic", "v")):
        ax.plot(eps, [100 * (pc[s][m] / pc[s]["independent"] - 1) for s in sides], mk + "-", color=C[m], label=m)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("epsilon = source area / board area")
    ax.set_ylabel("error of the mean top temperature rise under the source (%)")
    ax.set_title("Cu / FR4 / Cu coupon, 2.5 W: every model within 0.3 % of the independent solver (FDM 1.2 % for the 5 mm source)", fontsize=8.5)
    ax.legend(fontsize=8, ncol=5)
    fig.tight_layout()
    fig.savefig(FIG / "fig_07_program_vs_coupon.png", dpi=110)
    plt.close(fig)


def muzychka(mz):
    """!
    @brief The published cases against the solver and the models, and the through-thickness rule.
    @param mz Content of muzychka_2003.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6))
    c3 = mz["3"]
    labels = ["paper: centre max", "paper: mean source"]
    vals = [c3["paper"]["max_centre"], c3["paper"]["mean_area"]]
    axs[0].bar([0, 1], vals, 0.5, color=C["paper"], label="paper")
    ind = c3["independent"]
    axs[0].bar([0.5, 1.5], [ind["max"], float(np.mean(ind["mean"]))], 0.25, color=C["this"], label="independent solver")
    for k, m in enumerate(("fvm", "fdm", "solid3d", "analytic")):
        r = c3["program"][m]
        axs[0].plot([0.5, 1.5], [r["max"], float(np.mean(r["mean"]))], "o", color=C[m], label=m)
    axs[0].set_xticks([0.25, 1.25])
    axs[0].set_xticklabels(["maximum temperature\nat the centre", "area-weighted mean\nsource temperature"])
    axs[0].set_ylim(76, 82)
    axs[0].set_ylabel("temperature (C)")
    axs[0].set_title("Cross of five 20 mm sources, 100 x 100 x 10 mm plate (k 50, h 50)", fontsize=9)
    axs[0].legend(fontsize=7)
    th = mz["thickness"]
    ts = sorted(th, key=float)
    rise = [th[t]["independent"] for t in ts]
    q = 12500.0
    pred = [100 * 0.5 * q * float(t) * 1e-3 / 50.0 / r for t, r in zip(ts, rise)]
    axs[1].plot([float(t) for t in ts], pred, "k--", label="predicted: q'' t / (2 k) / rise")
    for m in ("fvm", "solid3d"):
        axs[1].plot([float(t) for t in ts], [-100 * (th[t][m] / th[t]["independent"] - 1) for t in ts], "o-", color=C[m], label=f"{m}: observed shortfall")
    c1 = mz["1a"]
    r1 = c1["independent"]["centroid"][0] - 25.0
    obs1 = -100 * ((c1["program"]["fvm"]["centroid"][0] - 25.0) / r1 - 1)
    axs[1].plot([10.0], [obs1], "*", ms=12, color=C["lumped"], label="case 1 (k 10): observed, FVM")
    axs[1].plot([10.0], [100 * 0.5 * 16000.0 * 0.01 / 10.0 / r1], "x", ms=9, color="k", label="case 1: predicted")
    axs[1].set_xscale("log")
    axs[1].set_xlabel("plate thickness (mm)")
    axs[1].set_ylabel("rise at the centre of the source: model below the 3D solver (%)")
    axs[1].set_title("One node through the thickness: the shortfall follows q'' t / (2 k)", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_08_muzychka_and_the_thickness_rule.png", dpi=110)
    plt.close(fig)


def natural_convection(nc):
    """!
    @brief The laminar form of Churchill and Chu against the general form over Ra, and the effect on h of a vertical board.
    @param nc Content of natural_convection.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.3))
    ra = [r for r, _ in nc["ratio"]]
    axs[0].semilogx(ra, [100 * v for _, v in nc["ratio"]], color=C["this"])
    axs[0].axhline(0, color="k", lw=0.8)
    axs[0].axvspan(1e5, 3e7, color="#fcd9a8", alpha=0.5, label="Ra of a 50 to 200 mm board at 10 to 80 K")
    axs[0].axvline(1e9, color="k", ls=":", lw=0.8)
    axs[0].set_xlabel("Rayleigh number")
    axs[0].set_ylabel("laminar form / general form - 1 (%), Pr 0.71")
    axs[0].set_title("Same authors, two forms: the laminar form is only for Ra below 1e9", fontsize=9)
    axs[0].legend(fontsize=8)
    for hgt, col in ((50.0, "#1d4ed8"), (100.0, "#059669"), (200.0, "#d97706")):
        rows = [r for r in nc["h"] if r["height_mm"] == hgt]
        axs[1].plot([r["dt"] for r in rows], [100 * (r["h_laminar"] / r["h_general"] - 1) for r in rows], "o-", color=col, label=f"board height {hgt:g} mm")
    axs[1].axhline(0, color="k", lw=0.8)
    axs[1].set_xlabel("temperature rise of the board (K)")
    axs[1].set_ylabel("h laminar form against h of the program (%)")
    axs[1].set_title("Effect on the coefficient: a few percent, up to 10 % on a 200 mm board", fontsize=9)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_10_natural_convection_forms.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Draw the six data figures.
    @return None.
    """
    FIG.mkdir(parents=True, exist_ok=True)
    cu = load("culham_1998")
    layer_orders(cu)
    size_location_biot(cu)
    lee(load("lee_spreading"))
    program_vs_coupon(load("program_vs_coupon"))
    muzychka(load("muzychka_2003"))
    natural_convection(load("natural_convection"))
    print("figures in", FIG)


if __name__ == "__main__":
    main()
