"""!
@file make_figures.py
@brief Data figures of the effective-conductivity investigation, drawn from the JSON files that the studies write in out/ (run the studies first; make_diagrams.py draws the schematics).
@details Writes figures/fig_03_layer_orders_k_eff.png, fig_04_size_location_biot.png, fig_06_lee_spreading.png, fig_07_program_vs_coupon.png, fig_08_muzychka_and_the_thickness_rule.png, fig_10_natural_convection_forms.png, fig_11_biot_definitions.png, fig_12_corrections_impact.png, fig_13_channel_correlations.png, fig_14_plate_alignment_sweep.png and fig_17_one_layer_independent.png.
         Run: .venv/bin/python research/effective-conductivity/scripts/make_figures.py (from the repository root; a few seconds).
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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
    axs[2].semilogx([cu["biot"][h]["Bi"] for h in bi], [cu["biot"][h]["paper"] for h in bi], "s--", color=C["paper"], label="paper (read from the plot)")
    axs[2].semilogx([cu["biot"][h]["Bi"] for h in bi], [cu["biot"][h]["k_eff"] for h in bi], "o-", color=C["this"], label="independent solver")
    axs[2].set_xlabel("Biot number h L / k1 (L = 25 mm, k1 = 0.4)")
    axs[2].set_title("film coefficient: apart from Bi about 1; the paper's plateau of 4.8 is not reachable", fontsize=8)
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
    worst = max(abs(100 * (pc[s][m] / pc[s]["independent"] - 1)) for s in sides for m in ("fvm", "solid3d", "analytic"))
    ax.set_title(f"Cu / FR4 / Cu coupon, 2.5 W: FVM, 3D solid and Analytic within {worst:.1f} % of the independent solver; FDM and Lumped within about 1 %", fontsize=8.5)
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
    x = [float(t) for t in ts]
    axs[1].plot(x, [100 * th[t]["bound"] / th[t]["independent"] for t in ts], "k--", label="bound: q'' t / (2 k) / rise")
    axs[1].plot(x, [100 * th[t]["gradient"] / th[t]["independent"] for t in ts], "k:", marker=".", label="measured: surface minus thickness mean (3D)")
    for m in ("fvm", "solid3d"):
        axs[1].plot(x, [-100 * (th[t][m] / th[t]["independent"] - 1) for t in ts], "o-", color=C[m], label=f"{m}: observed shortfall")
    c1 = mz["1a"]["independent"]
    r1 = c1["mean"][0] - 25.0
    obs1 = -100 * ((mz["1a"]["program"]["fvm"]["mean"][0] - 25.0) / r1 - 1)
    axs[1].plot([10.0], [obs1], "*", ms=12, color=C["lumped"], label="case 1 (k 10), 10 W source: FVM shortfall")
    axs[1].plot([10.0], [100 * c1["gradient"][0] / r1], "P", ms=9, color="k", label="case 1: measured gradient")
    axs[1].plot([10.0], [100 * c1["bound"][0] / r1], "x", ms=9, color="k", label="case 1: bound")
    axs[1].set_xscale("log")
    axs[1].set_xlabel("plate thickness (mm)")
    axs[1].set_ylabel("rise of the source: model below the 3D solver (%)")
    axs[1].set_title("One node is the thickness mean: the surface gradient is below q'' t / (2 k) when the heat spreads", fontsize=8.5)
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


def biot_definitions(bd):
    """!
    @brief The effective conductivity of the base laminate against the film coefficient under five definitions of the mean wall temperature, and the solid-body resistance against the series path.
    @param bd Content of biot_definitions.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.5))
    hs = bd["h"]
    bi = [h * 0.025 / 0.4 for h in hs]
    styles = {"A_top_free+bottom": ("A: free top face and bottom", "#1d4ed8", "o-"), "B_bottom_only": ("B: bottom only", "#059669", "s-"), "C_top_free_only": ("C: free top face only", "#d97706", "^-"),
              "D_flux_weighted": ("D: weighted by the heat flux", "#7c3aed", "v-"), "E_ambient": ("E: ambient (ideal sink)", "#9ca3af", "x--")}
    for m, (lab, col, mk) in styles.items():
        axs[0].semilogx(bi, bd["modes"][m], mk, color=col, label=lab, lw=1.2)
    axs[0].semilogx(bi, bd["bottom_only_film"], "d:", color="#dc2626", label="film on the bottom only (B)")
    axs[0].axhspan(4.7, 4.9, color="#6b7280", alpha=0.3, label="paper: plateau about 4.8 above Bi 100")
    axs[0].set_xlabel("Biot number h L / k1 (L = 25 mm, k1 = 0.4)")
    axs[0].set_ylabel("effective conductivity (W/mK)")
    axs[0].set_title("No definition gives the plateau: k_e falls to 0.6 W/mK", fontsize=9)
    axs[0].legend(fontsize=7)
    axs[1].semilogx(bi, bd["R_solid"], "o-", color="#1d4ed8", label="solid-body resistance of the laminate")
    axs[1].axhline(bd["series_under_source"], color="k", ls="--", label="series resistance of the stack under the footprint: 6.3 K/W")
    axs[1].set_xlabel("Biot number")
    axs[1].set_ylabel("resistance (K/W)")
    axs[1].set_ylim(0, 7)
    axs[1].set_title("With strong films the heat does not spread: it goes down through the stack", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_11_biot_definitions.png", dpi=110)
    plt.close(fig)


def corrections_impact(ci):
    """!
    @brief What the corrections and proposals change: the plate check against the cell size, the laminar form on the program, the thick-plate criterion on the block cases.
    @param ci Content of corrections_impact.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4))
    ns = sorted(ci["plate"], key=int)
    paper = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}
    for pos, col in (("centre", "#1d4ed8"), ("edge midpoint", "#059669"), ("corner", "#d97706")):
        axs[0].plot([100.0 / int(n) for n in ns], [100 * (ci["plate"][n][pos] / paper[pos] - 1) for n in ns], "o-", color=col, label=pos)
    axs[0].axhline(0, color="k", lw=0.8)
    axs[0].set_xscale("log")
    axs[0].set_xticks([4, 2, 1, 0.5, 0.25])
    axs[0].set_xticklabels(["4", "2", "1", "0.5", "0.25"])
    axs[0].xaxis.set_minor_formatter(plt.NullFormatter())
    axs[0].invert_xaxis()
    axs[0].set_xlabel("cell size (mm); the source keeps its 25 mm on 1, 0.5 and 0.25 mm cells (24 mm on 2 mm cells)")
    axs[0].set_ylabel("plate model against Seri Lee (%)")
    axs[0].set_title(f"The documented +4.5 % was a 24 mm source (round() on 1 mm cells): {100 * (ci['documented']['rc_24mm'] / 0.66 - 1):+.1f} %", fontsize=9)
    axs[0].legend(fontsize=8)
    rows = ci["forms"]
    x = np.arange(len(rows))
    axs[1].bar(x, [100 * ((r["t_laminar"] - r["ambient"]) / (r["t_general"] - r["ambient"]) - 1) for r in rows], color="#1d4ed8")
    axs[1].axhline(0, color="k", lw=0.8)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels([r["board"].replace(", ", ",\n").replace("2-layer board ", "2-layer\n") for r in rows], fontsize=6)
    axs[1].set_ylabel("change of the maximum rise with the laminar form (%)")
    axs[1].set_title("Laminar form on the program (vertical boards): -0.7 to +0.2 %", fontsize=9)
    vals = [c["percent"] for c in ci["criterion"]]
    axs[2].hist(vals, bins=20, color="#1d4ed8")
    axs[2].axvline(5.0, color="#dc2626", ls="--", label="proposed threshold, 5 %")
    axs[2].set_xlabel("q'' t / (2 k) / rise (%) over the 74 metal-block cases")
    axs[2].set_ylabel("cases")
    axs[2].set_title(f"Thick-plate criterion: maximum {max(vals):.2f} %, none above the threshold", fontsize=9)
    axs[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_12_corrections_impact.png", dpi=110)
    plt.close(fig)


def alignment(ci):
    """!
    @brief The centre value of the plate check for many cell sizes (the source keeps its 25 mm), and against the side of the source.
    @param ci Content of corrections_impact.json.
    @return None.
    """
    d = np.array([a[0] for a in ci["alignment"]])
    err = np.array([a[2] for a in ci["alignment"]])
    off = np.array([a[1] for a in ci["alignment"]])
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    sc = axs[0].scatter(d, err, c=off, cmap="viridis", s=36)
    axs[0].axhline(0, color="k", lw=0.8)
    axs[0].invert_xaxis()
    axs[0].set_ylim(-1, 6)
    axs[0].set_xlabel("cell size (mm)")
    axs[0].set_ylabel("centre value against Seri Lee (%)")
    axs[0].set_title(f"46 cell sizes, the source kept at 25 mm: {err.min():+.1f} to {err.max():+.1f} %", fontsize=9)
    fig.colorbar(sc, ax=axs[0], label="distance of the source edge from a cell edge (cells)")
    ss = ci["side_sweep"]
    axs[1].plot([a for a, _ in ss], [e for _, e in ss], "o-", color="#1d4ed8", label="0.5 mm cells, edges on cell edges")
    doc = ci["documented"]
    axs[1].plot([doc["side_mm"]], [100 * (doc["rc_24mm"] / 0.66 - 1)], "*", ms=14, color="#dc2626", label="the documented check (round() on 1 mm cells)")
    axs[1].axhline(0, color="k", lw=0.8)
    axs[1].set_xlabel("side of the heated square (mm); the source of the article is 25 mm")
    axs[1].set_ylabel("error (%)")
    axs[1].set_title("One millimetre less of source side: +3.5 %; the documented check had 24 mm", fontsize=9)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_14_plate_alignment_sweep.png", dpi=110)
    plt.close(fig)


def channel(ch):
    """!
    @brief The two channel correlations and the optimum spacing.
    @param ch Content of channel_correlations.json.
    @return None.
    """
    el = np.array(ch["el"])
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    axs[0].loglog(el, ch["elenbaas"], color="#1d4ed8", label="Elenbaas (1942)")
    axs[0].loglog(el, ch["blend"], "--", color="#d97706", label="blend of Raithby and Hollands")
    axs[0].loglog(el, ch["bcr"], ":", color="#059669", label="Bar-Cohen and Rohsenow (as quoted, not opened)")
    axs[0].set_xlabel("Elenbaas number of the spacing El")
    axs[0].set_ylabel("Nusselt number based on the spacing")
    axs[0].set_title("Natural convection between vertical isothermal plates", fontsize=9)
    axs[0].legend(fontsize=8)
    grid = np.logspace(0, 3, 600)
    from study_channel_correlations import nu_elenbaas, nu_blend, nu_bcr
    for f, col, lab in ((nu_elenbaas, "#1d4ed8", "Elenbaas"), (nu_blend, "#d97706", "blend"), (nu_bcr, "#059669", "Bar-Cohen and Rohsenow (quoted)")):
        q = f(grid) / np.sqrt(grid)
        axs[1].semilogx(grid, q / q.max(), color=col, label=lab)
    axs[1].axvline(54.3, color="k", ls=":", label="2.714^4 = 54.3 (Bar-Cohen and Rohsenow, as quoted)")
    axs[1].axvline(50.0, color="#6b7280", ls=":", label="about 50 (Simons)")
    axs[1].set_xlabel("El")
    axs[1].set_ylabel("heat per unit of base area, relative")
    axs[1].set_title(f"Optimum spacing: El = {ch['opt_Elenbaas']:.0f}, {ch['opt_blend']:.0f} and {ch['opt_BCR']:.1f} (quoted: 54.3)", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_13_channel_correlations.png", dpi=110)
    plt.close(fig)


def one_layer(ol):
    """!
    @brief The one-layer board: a sketch of the board with the pad and the slabs, and the rise in the independent solver, the 3D solid before and after the correction, and the FVM.
    @param ol Content of one_layer_independent.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axs[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.5, 3.2), 9.0, 0.25, fc="#bbf7d0", ec="#15803d"))
    ax.add_patch(plt.Rectangle((3.5, 3.2), 3.0, 0.25, fc="#d97706", ec="k"))
    ax.add_patch(plt.Rectangle((4.5, 3.45), 1.0, 0.25, fc="#dc2626", ec="k"))
    ax.add_patch(plt.Rectangle((0.5, 1.4), 9.0, 1.8, fc="#bbf7d0", ec="#15803d"))
    for k in range(1, 4):
        ax.plot([0.5, 9.5], [1.4 + 0.45 * k] * 2, color="#15803d", lw=0.6)
    ax.text(5, 3.95, "part 6 x 6 mm, 1 W (film on top, also under it)", ha="center", fontsize=8)
    ax.text(5, 2.9, "copper slab: 20 mm pad (orange), laminate elsewhere (green)", ha="center", fontsize=7.5)
    ax.text(5, 1.0, "laminate: FR-4 1.565 mm, 0.3 W/mK (4 slabs in the 3D solid, 8 in the solver)", ha="center", fontsize=7.5)
    ax.annotate("", xy=(5, 1.45), xytext=(5, 3.15), arrowprops=dict(arrowstyle="->", color="#dc2626"))
    ax.annotate("", xy=(1.0, 2.6), xytext=(3.6, 3.1), arrowprops=dict(arrowstyle="->", color="#dc2626"))
    ax.text(5, 0.4, "bottom face: film of 15 W/m2K through the laminate", ha="center", fontsize=7.5)
    ax.set_title("The one-layer board of the check (not to scale)", fontsize=9)
    keys = list(ol)
    x = np.arange(len(keys))
    for k, (name, col, lab) in enumerate((("independent", C["this"], "independent 3D solver"), ("solid3d", C["solid3d"], "3D solid (corrected)"),
                                         ("solid3d_before", "#fecaca", "3D solid before (no laminate)"), ("fvm", C["fvm"], "FVM (one node)"),
                                         ("fvm_series", "#9ca3af", "FVM, laminate in series under the bottom film (candidate)"))):
        axs[1].bar(x + (k - 2) * 0.16, [ol[c][name] for c in keys], 0.16, color=col, ec="#dc2626" if name == "solid3d_before" else None, label=lab)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels([("20 mm pad, " if ol[c]["pad"] else "full copper, ") + f"{ol[c]['thickness_mm']:g} mm" for c in keys], fontsize=8)
    axs[1].set_ylabel("rise of the hottest copper cell (K)")
    pad = next(c for c in keys if ol[c]["pad"])
    axs[1].set_title(f"With the pad the laminate matters: corrected {100 * (ol[pad]['solid3d'] / ol[pad]['independent'] - 1):+.1f} %, "
                     f"before {100 * (ol[pad]['solid3d_before'] / ol[pad]['independent'] - 1):+.0f} %, FVM {100 * (ol[pad]['fvm'] / ol[pad]['independent'] - 1):+.0f} %", fontsize=9)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_17_one_layer_independent.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Draw the ten data figures.
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
    biot_definitions(load("biot_definitions"))
    corrections_impact(load("corrections_impact"))
    channel(load("channel_correlations"))
    alignment(load("corrections_impact"))
    one_layer(load("one_layer_independent"))
    print("figures in", FIG)


if __name__ == "__main__":
    main()
