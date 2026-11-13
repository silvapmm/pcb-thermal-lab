#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the finite-element comparison: the meshes (via patch at the wall, disc O-grid, T outline), the convergence of the validation cases, the strong-edge
       plate against the finite-volume reference and the program, and the via effect and the drawn boards against the finite elements.
@details Run from the repository root after the studies: `.venv/bin/python research/independent-fem-edge/scripts/make_figures.py`. Writes `research/independent-fem-edge/figures/fig_NN_*.png`.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(1, os.path.join(FOLDER, "tests"))
import matplotlib                                                        # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402

import cases                                                             # noqa: E402

FIG = os.path.join(FOLDER, "figures")
OUT = os.path.join(FOLDER, "out")


def draw_plan(ax, plan, lim=None, title=""):
    """!
    @brief Draw a plan mesh coloured by tag.
    @param ax Axes.
    @param plan Quad2D.
    @param lim (x0, x1, y0, y1) in mm or None.
    @param title Title.
    @return None.
    """
    p = plan.xy[plan.quads] * 1e3
    for poly, t in zip(p, plan.tag):
        ax.fill(poly[:, 0], poly[:, 1], facecolor=plt.cm.tab20(t % 20), edgecolor="k", lw=0.25)
    ax.set_aspect("equal")
    if lim:
        ax.set_xlim(lim[0], lim[1])
        ax.set_ylim(lim[2], lim[3])
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("mm")


def fig_meshes():
    """!
    @brief Figure 1: the plan meshes.
    @return None.
    """
    fig, ax = plt.subplots(1, 4, figsize=(17, 4.4))
    draw_plan(ax[0], cases.strong_edge(1000.0, hf=0.1, via_dist=0.16).plan, (9.4, 10.0, 4.4, 5.0), "via 0.16 mm from the wall x = 10 (window to the wall)")
    draw_plan(ax[1], cases.strong_edge(1000.0, hf=0.1, via_dist=3.0).plan, (6.3, 7.7, 3.7, 5.0), "via 3 mm from the wall (O-grid patch, cut at the symmetry line)")
    draw_plan(ax[2], cases.disc_board(200.0, inset=1.2, n_side=8).plan, None, "disc, radius 10 mm: heater = inner square, copper edge = a circle level")
    draw_plan(ax[3], cases.t_outline(200.0, hf=0.4).plan, None, "T outline, half domain x >= 10 mm")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_meshes.png"), dpi=130)
    plt.close(fig)


def fig_validation():
    """!
    @brief Figure 2: the convergence of the manufactured solutions and the sheet series (recomputed, seconds).
    @return None.
    """
    import test_closed_forms as tc
    import test_manufactured as tm
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    n = np.array([10, 20, 40])
    e = [tm._box(k) for k in n]
    ax[0].loglog(1 / n, e, "o-", label="box, orthotropic, Robin x 6")
    ax[0].loglog(1 / n, e[0] * (n[0] / n) ** 2, "k--", lw=0.8, label="slope 2")
    nd = np.array([6, 12, 24])
    ed = [tm._disc(k) for k in nd]
    ax[0].loglog(1 / nd, ed, "s-", label="disc O-grid, curved Robin wall")
    ax[0].set_xlabel("1 / n")
    ax[0].set_ylabel("max nodal error")
    ax[0].set_title("manufactured solutions", fontsize=9)
    ax[0].legend(fontsize=7)
    ns = np.array([1, 2, 4])
    es = []
    for k in ns:
        r, plan, T = tc._sheet(20 * k, 12 * k)
        Np = r["info"]["ex"]["n_plan"]
        ref = T(plan.xy[:, 0], plan.xy[:, 1])
        es.append(np.abs(r["T"][:Np] - ref).max() / ref.max())
    ax[1].loglog(1 / (20 * ns), es, "o-", label="FEM against the Robin series")
    ax[1].loglog(1 / (20 * ns), es[0] * (1 / ns) ** 2, "k--", lw=0.8, label="slope 2")
    ax[1].set_xlabel("element size / length")
    ax[1].set_ylabel("relative max error")
    ax[1].set_title("sheet with two Robin walls (own series)", fontsize=9)
    ax[1].legend(fontsize=7)
    r, plan, T = tc._sheet(40, 24)
    Np = r["info"]["ex"]["n_plan"]
    x, y = plan.xy[:, 0] * 1e3, plan.xy[:, 1] * 1e3
    sc = ax[2].tricontourf(x, y, r["T"][:Np], 20)
    ax[2].tricontour(x, y, T(plan.xy[:, 0], plan.xy[:, 1]), 10, colors="k", linewidths=0.5)
    ax[2].set_aspect("equal")
    ax[2].set_title("sheet: FEM (fill) and series (lines), K", fontsize=9)
    fig.colorbar(sc, ax=ax[2])
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_validation_convergence.png"), dpi=130)
    plt.close(fig)


def fig_plate():
    """!
    @brief Figure 3: the strong-edge plate at 1000 W/m2K: FEM against the mesh (rising to its limit) and the FV reference (falling to it), and the program's error.
    @return None.
    """
    fem = json.load(open(os.path.join(OUT, "fem_cache.json")))
    fv = json.load(open(os.path.join(OUT, "fv.json")))
    rep = json.load(open(os.path.join(OUT, "report.json")))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for h, c in ((200.0, "tab:blue"), (1000.0, "tab:red")):
        hs = [0.2, 0.1, 0.05]
        v = [fem[f"plate|{h}|0.0|{hf}|6"]["tmax"] for hf in hs]
        e = rep[f"plate|{h}|0.0"]["ext"]
        ax[0].plot(hs, 100 * (np.array(v) / e - 1), "o-", color=c, label=f"FEM, {h:.0f} W/m2K")
        fvv = [fv[f"{h}|None|0.0|{dx}"]["tmax"] for dx in (0.00025, 0.000125)]
        ax[0].plot([0.25, 0.125], 100 * (np.array(fvv) / e - 1), "s--", color=c, label=f"FV ref3d (8 slabs), {h:.0f}")
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xscale("log")
    ax[0].set_xlabel("plan size (mm)")
    ax[0].set_ylabel("% from the FEM extrapolation")
    ax[0].set_title("strong-edge plate, hottest rise: the two methods against their mesh", fontsize=9)
    ax[0].legend(fontsize=7)
    labels = ["default (2 sub-gaps)", "8 sub-gaps"]
    x = np.arange(2)
    for i, (h, c) in enumerate(((200.0, "tab:blue"), (1000.0, "tab:red"))):
        for j, cell in enumerate((0.5, 0.25)):
            vals = [float(s) for s in rep[f"plate|{h}|0.0"]["prog_fvm"][j].split(" / ")]
            ax[1].bar(x + (i * 2 + j) * 0.2 - 0.3, vals, 0.2, color=c, alpha=0.5 + 0.5 * j, label=f"FVM {cell} mm, {h:.0f} W/m2K")
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels(labels, fontsize=8)
    ax[1].set_ylabel("% from the FEM extrapolation")
    ax[1].set_title("program FVM on the plate (copper to the wall)", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_plate_methods_and_program.png"), dpi=130)
    plt.close(fig)


def fig_boards():
    """!
    @brief Figure 4: the via effect and the drawn boards (squares, disc, T): program and FV references against the FEM.
    @return None.
    """
    rep = json.load(open(os.path.join(OUT, "report.json")))
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    keys = [k for k in rep if k.startswith("via|")]
    x = np.arange(len(keys))
    for j, (lab, col) in enumerate((("FV 1/8 mm", "tab:gray"), ("FVM 0.25 mm, default (2 sub-gaps)", "tab:red"), ("FVM 0.25 mm, 8 sub-gaps", "tab:green"))):
        vals = []
        for k in keys:
            r = rep[k]
            if j == 0:
                vals.append(100 * (r["fv"][1] / r["ext"] - 1) if r["fv"][1] else np.nan)
            else:
                parts = r["prog_fvm"][1].split(" / ")
                vals.append(float(parts[0 if j == 1 else 1]) if parts[0] != "-" else np.nan)
        ax[0].bar(x + (j - 1) * 0.25, vals, 0.25, color=col, label=lab)
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels([k.replace("via|", "h ").replace("|", ", d ") + " mm" for k in keys], fontsize=7)
    ax[0].set_ylabel("% of the FEM via effect")
    ax[0].set_title("via effect E against the FEM (conforming cylinder)", fontsize=9)
    ax[0].legend(fontsize=7)
    keys = [k for k in rep if k.split("|")[0] in ("sq_in", "sq_wall", "T_wall", "disc_wall", "disc_in") and not k.endswith("tmax")]
    x = np.arange(len(keys))
    for j, (lab, col) in enumerate((("FV truth", "tab:gray"), ("FVM 1 mm", "tab:red"), ("FVM 0.5 mm", "tab:orange"), ("FDM 1 mm", "tab:blue"), ("FDM 0.5 mm", "tab:cyan"))):
        vals = []
        for k in keys:
            r = rep[k]
            if j == 0:
                vals.append(100 * (r["truth"] / r["ext"] - 1) if r["truth"] else np.nan)
            else:
                s = r["prog"][j - 1]
                vals.append(float(s.split(" ")[0]) if s != "-" else np.nan)
        ax[1].bar(x + (j - 2) * 0.16, vals, 0.16, color=col, label=lab)
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([k.replace("|", "\n") for k in keys], fontsize=7)
    ax[1].set_ylabel("% of the FEM heater mean")
    ax[1].set_title("squares, disc and T against the FEM", fontsize=9)
    ax[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_boards_against_fem.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    which = sys.argv[1:] or ["meshes", "validation", "plate", "boards"]
    for w in which:
        {"meshes": fig_meshes, "validation": fig_validation, "plate": fig_plate, "boards": fig_boards}[w]()
        print("figure", w, "done", flush=True)
