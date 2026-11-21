#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the surface read-out investigation: fig_01 the section of each model with the nodes it keeps and the fluxes the rule reads (Lumped, Analytic, 3D solid, transient frame); fig_02 the decision chart that
       says which rule a model gets and with which wording; fig_03 the plates of the study (plan and section).
@details No data and no program: the shapes are the thing itself drawn to scale where a scale exists, the numbers in the labels are the plate definitions of lib/plates.py and the Fourier numbers of the study.
         Run from the repository root: .venv/bin/python research/surface-readout-models/scripts/make_diagrams.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import diagram_kit as D  # noqa: E402

FIG = os.path.join(HERE, "..", "figures")


def _plate(ax, x0=0.5, w=9.0, n_cu=1, lam=False):
    """!
    @brief Draw a thick copper plate (and optionally a laminate and a bottom copper) as a stack, with the source on top.
    @param ax Axes.
    @param x0 Left.
    @param w Width.
    @param n_cu Slabs drawn through the thick copper.
    @param lam True to add the laminate and the thin bottom copper below.
    @return tuple (top y, bottom y of the thick layer).
    """
    top, h = 3.0, 1.8
    dz = h / n_cu
    for i in range(n_cu):
        D.layer(ax, x0, top - h + (n_cu - 1 - i) * dz, w, dz, D.METAL)
    if lam:
        D.layer(ax, x0, top - h - 0.7, w, 0.7, D.FR4, "laminate")
        D.layer(ax, x0, top - h - 0.85, w, 0.15, D.COPPER)
    D.layer(ax, x0 + w * 0.35, top, w * 0.3, 0.2, D.HEAT)
    return top, top - h


def fig_01_models():
    """!
    @brief The four models: nodes kept, fluxes read, where the surface comes from.
    """
    fig, axs = plt.subplots(2, 2, figsize=(12, 9))
    for ax in axs.ravel():
        ax.axis("off")
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.6, 4.9)
    # (a) Lumped: rings around the part, one node per ring per layer
    a = axs[0, 0]
    top, bot = _plate(a)
    for x in (3.2, 2.2, 1.3, 6.8, 7.8, 8.7):
        a.plot([x, x], [bot - 0.05, top + 0.05], "k:", lw=0.6)
    a.plot([5.0], [(top + bot) / 2], "o", color="k", ms=6)
    for x in (2.7, 1.75, 6.0 + 1.3, 7.3 + 0.9):
        a.plot([x], [(top + bot) / 2], "o", color="gray", ms=4)
    a.text(5.0, bot - 0.35, "part's node", ha="center", fontsize=7.5)
    a.text(0.5, bot - 0.35, "grey: ring nodes\n(painted as a field)", fontsize=7, va="top")
    D.arrow(a, 5.0, top + 0.9, 5.0, top + 0.25, color=D.HEAT)
    a.text(5.0, top + 1.05, "q'' = P / A  (the only flux the bound reads)", ha="center", fontsize=7.5, color=D.HEAT)
    D.arrow(a, 5.0, (top + bot) / 2, 5.0, top, color="k", width=2)
    a.text(5.35, bot + 0.2, "surface - node <= q'' t / 2k\n(a bound on the TERM,\nnot on the model's error)", fontsize=7.5)
    a.set_title("(a) Lumped: no per-cell flux; an upper bound\non the through-thickness term only", fontsize=9)
    # (b) Analytic: uniform sheet, nodes at mid-thickness, uniform conductances
    b = axs[0, 1]
    top, bot = _plate(b, lam=True)
    b.plot([1.0, 9.0], [(top + bot) / 2] * 2, color="k", ls="--", lw=0.9)
    b.text(9.0, (top + bot) / 2 + 0.1, "node of layer 1", fontsize=7, ha="right")
    b.plot([1.0, 9.0], [bot - 0.8] * 2, color="k", ls="--", lw=0.9)
    b.text(9.0, bot - 0.75, "node of layer 2", fontsize=7, ha="right")
    D.arrow(b, 5.0, top + 0.9, 5.0, top + 0.25, color=D.HEAT, label="q_src")
    for x in (1.8, 8.2):
        D.arrow(b, x, top, x, top + 0.5, color=D.BLUE, width=1.0)
    b.text(0.6, top + 0.65, "h_top_eff theta_1", fontsize=7, color=D.BLUE)
    D.arrow(b, 3.0, bot + 0.2, 3.0, bot - 1.1, color=D.BLUE, label="")
    b.text(3.2, bot - 1.15, "g_diel (theta_1 - theta_2)", fontsize=7, color=D.BLUE)
    b.text(0.6, -1.3, "q_top = q_src - h_top_eff theta_1;  q_bot = - g_diel (theta_1 - theta_2)  ->  parabola (rule F)\nnot in g_diel: vias, blocks, heatsinks -> q_bot too small -> term between q t/3k and the rule's value (never above the bound)", fontsize=7)
    b.set_title("(b) Analytic: fluxes from the field and the\nuniform conductances of its own sheet", fontsize=9)
    # (c) 3D solid with n copper slabs
    c = axs[1, 0]
    top, bot = _plate(c, n_cu=4, lam=True)
    dz = (top - bot) / 4
    c.plot([5.0] * 4, [top - dz * (i + 0.5) for i in range(4)], "o", color="k", ms=4)
    D.arrow(c, 5.0, top + 0.9, 5.0, top + 0.25, color=D.HEAT, label="q_top")
    c.annotate("", xy=(7.2, top), xytext=(7.2, top - dz / 2), arrowprops=dict(arrowstyle="<->"))
    c.text(7.35, top - dz / 4 - 0.35, "dz/2 skipped by the\ninjection at the node:\nface = slab 1 + q_top dz / 2k", fontsize=7.5, va="top")
    c.text(0.6, -1.3, "1 slab (the program today): column = node, surface by the parabola from its own links (rule S)\n4 or 8 slabs (copper slabs, e2): surface = first slab + half slab; column = mean of the slabs", fontsize=7)
    c.set_title("(c) 3D solid: every conductance is in the matrix,\nso the fluxes are exact", fontsize=9)
    # (d) transient frame: the real profiles of the independent column solver, 10 mm copper, step of 100 kW/m2, films as the study
    d = axs[1, 1]
    d.axis("on")
    d.set_xlim(auto=True)
    d.set_ylim(auto=True)
    sys.path.insert(0, os.path.join(HERE, "..", "lib"))
    import column1d
    t, k, rc, h, q = 10e-3, 385.0, 8960.0 * 385.0, 400.0, 1e5
    alpha = k / rc
    for fo, col in ((0.03, "#9467bd"), (0.3, "#2ca02c"), (3.0, D.HEAT)):
        tau = fo * t * t / alpha
        r = column1d.solve([(t, k, rc, 80)], h, lambda s: q, tau, tau / 400)
        face = r["x_end"][0] + q * r["dz"][0] / (2 * k)
        mean = r["mean"][0][-1]
        d.plot(r["x_end"] - mean, r["z"] / t, color=col, lw=2, label=f"Fo {fo}: surface - mean = {face - mean:.2f} K (q t / 3k = {q * t / 3 / k:.2f})")
    d.invert_yaxis()
    d.axvline(0, color="k", ls=":", lw=0.8)
    d.set_xlabel("T(z) - layer mean (K)", fontsize=8)
    d.set_ylabel("depth z / t", fontsize=8)
    d.legend(loc="lower right", fontsize=7, title="10 mm Cu, 100 kW/m2, film 400 W/m2K (independent column solver)", title_fontsize=6.5)
    d.tick_params(labelsize=7)
    d.set_title("(d) transient frame: the same parabola,\nvalid once the heat has crossed the layer", fontsize=9)
    D.save(fig, os.path.join(FIG, "fig_01_models.png"))


def fig_02_decision():
    """!
    @brief The decision chart: which model gets which rule and which words.
    """
    fig, ax = D.canvas(11, 6.2)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6.2)
    D.box(ax, 3.8, 5.3, 3.4, 0.7, "a solved field of a model\n(steady or one frame)", "#cfe3f5", True)
    cols = [("FVM, FDM, FEM\n(2.8.0)", 0.2, "computed (FEM)\nparabola (FVM, FDM)", "#d9ead3"),
            ("3D solid", 2.9, "1 slab: rule S\n(exact links)\n4 to 8 slabs: computed", "#d9ead3"),
            ("Analytic", 5.6, "rule F\n(field + uniform g)\nestimate", "#fff2cc"),
            ("Lumped", 8.3, "bound q'' t / 2k\non the TERM only\n(no absolute number)", "#f4cccc")]
    for name, x, rule, colr in cols:
        D.arrow(ax, 5.5, 5.3, x + 1.2, 4.4)
        D.box(ax, x, 3.6, 2.4, 0.8, name, "#eeeeee")
        D.arrow(ax, x + 1.2, 3.6, x + 1.2, 2.9)
        D.box(ax, x, 1.8, 2.4, 1.1, rule, colr)
    notes = ["flag t/a > 0.5:\nupper estimate", "8 slabs: surface\nwithin 0.14 K of the\n3D surface on the\neight plates", "vias missing:\nterm low by up to\n1/3 of the bound", "column error of the\nmodel (up to 50 K on\n8 of 22 harness parts)\nstays in the number"]
    for (name, x, rule, colr), n in zip(cols, notes):
        D.arrow(ax, x + 1.2, 1.8, x + 1.2, 1.25)
        ax.text(x + 1.2, 0.65, n, ha="center", va="center", fontsize=7.5)
    ax.text(5.5, 0.05, "Every rule is a VIEW beside the column (decision 5): Tj, margin, top path and the comparison between models stay on the column.\nTransient frames: the same rule as the steady one of their model, an upper estimate below Fo 0.3.", ha="center", fontsize=7.5)
    D.save(fig, os.path.join(FIG, "fig_02_decision.png"), "Which rule each model gets (the result of this investigation)")


def fig_03_plates():
    """!
    @brief The plates of the study: plan with the source and the via, and the sections of the three kinds.
    """
    sys.path.insert(0, os.path.join(HERE, "..", "lib"))
    import plates
    fig = plt.figure(figsize=(11, 4.8))
    ax = fig.add_axes([0.03, 0.08, 0.28, 0.82])
    ax.set_aspect("equal")
    ax.add_patch(plt.Rectangle((0, 0), 50, 50, facecolor=D.METAL, edgecolor="k"))
    for name, kind, t, k, a, P, h, via in plates.PLATES[:2]:
        pass
    x0, y0, x1, y1 = plates.rect_mm(10.0)
    ax.add_patch(plt.Rectangle((x0, y0), 10, 10, facecolor=D.HEAT, alpha=0.6, edgecolor="k"))
    ax.add_patch(plt.Rectangle(plates.rect_mm(4.0)[:2], 4, 4, facecolor="none", edgecolor="k", ls="--"))
    ax.add_patch(plt.Rectangle(plates.rect_mm(2.0)[:2], 2, 2, facecolor="none", edgecolor="k", ls=":"))
    ax.plot([25], [25], "ko", ms=3)
    ax.text(25, 46, "50 x 50 mm, sides and top\ninsulated outside the source", ha="center", fontsize=7)
    ax.text(25, 3.5, "squares of 2, 4, 5, 10 mm, centred;\nvia 0.6 mm at the centre of\nthe last plate", ha="center", fontsize=7)
    ax.set_xlim(-2, 52)
    ax.set_ylim(-2, 52)
    ax.set_title("plan", fontsize=9)
    ax.axis("off")
    ax2 = fig.add_axes([0.35, 0.08, 0.62, 0.82])
    ax2.axis("off")
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0.2, 5.4)
    D.layer(ax2, 0.3, 3.0, 3.4, 1.2, D.METAL, "one thick layer\n(1 to 10 mm, k 150 to 385)")
    D.layer(ax2, 0.3, 2.95, 3.4, 0.05, D.FR4)
    D.layer(ax2, 0.3 + 1.2, 4.2, 1.0, 0.15, D.HEAT)
    D.arrow(ax2, 2.0, 4.9, 2.0, 4.4, color=D.HEAT)
    D.arrow(ax2, 2.0, 2.9, 2.0, 2.3, color=D.BLUE, label="h")
    ax2.text(2.0, 1.8, "6 one-layer plates: case 2, 1 mm Cu,\n3 mm Cu, 10 mm Al, 10 mm Cu, 5 mm Al", ha="center", fontsize=7.5)
    D.layer(ax2, 5.0, 3.6, 3.4, 0.9, D.METAL, "2 mm Cu")
    D.layer(ax2, 5.0, 3.0, 3.4, 0.6, D.FR4, "1 mm FR-4")
    D.layer(ax2, 5.0, 2.9, 3.4, 0.1, D.COPPER)
    D.layer(ax2, 5.0 + 1.2, 4.5, 1.0, 0.15, D.HEAT)
    D.arrow(ax2, 6.7, 5.1, 6.7, 4.7, color=D.HEAT)
    ax2.plot([6.7, 6.7], [2.9, 4.5], color="k", lw=2)
    ax2.text(7.0, 2.35, "via", fontsize=7)
    D.arrow(ax2, 6.7, 2.8, 6.7, 2.2, color=D.BLUE, label="h")
    ax2.text(6.7, 1.8, "two-layer board,\nwithout and with a via", ha="center", fontsize=7.5)
    ax2.text(0.3, 0.6, "all: independent 3D (layered3d, 0.5 mm, 8 sub-slabs per metal layer) + the FEM surface;\nprogram models at 0.5 and 1 mm.  Also the 1D boards of the transient study (part over the whole face).", fontsize=7.5)
    ax2.set_title("sections", fontsize=9)
    fig.savefig(os.path.join(FIG, "fig_03_plates.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01_models()
    fig_02_decision()
    fig_03_plates()
    print("diagrams written to", FIG)
