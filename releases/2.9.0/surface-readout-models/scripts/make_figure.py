#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figure.py
@brief Draws `docs/images/fig_55_surface_models.png`: how the Lumped, the Analytic and the 3D solid read the surface of the outer copper (what this version ships).
@details Three sections drawn as the thing itself (no data, no program run): (a) the Lumped, which has no face flux and only quotes the term q'' t / 2k as a measured upper value;
         (b) the Analytic, whose fluxes are read from its own field and the uniform conductances of its sheet (rule F); (c) the 3D solid, the half slab above the outer copper slab
         when the layer is cut into slabs (above 105 um), the parabola fed with its own links on one slab. It replaces the copy of research/surface-readout-models fig_01, whose
         fourth panel (a transient frame) is not in this version. Run from the repository root:

             .venv/bin/python releases/2.9.0/surface-readout-models/scripts/make_figure.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "research"))
import diagram_kit as D  # noqa: E402

OUT = ROOT / "docs" / "images" / "fig_55_surface_models.png"


def _plate(ax, x0=0.5, w=9.0, n_cu=1, lam=False):
    """!
    @brief Draw a thick copper plate (and optionally a laminate and a thin bottom copper) with the source on top.
    @param ax Axes.
    @param x0 Left edge in drawing units.
    @param w Width in drawing units.
    @param n_cu Slabs drawn through the thick copper.
    @param lam True to add the laminate and the thin bottom copper below.
    @return Tuple (top y, bottom y of the thick layer).
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


def main():
    """!
    @brief Draw the three panels and save the picture.
    """
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.2))
    for ax in axs:
        ax.axis("off")
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.9, 4.9)
    # (a) Lumped: rings around the part, one node per ring; no face flux, so no surface temperature
    a = axs[0]
    top, bot = _plate(a)
    for x in (3.2, 2.2, 1.3, 6.8, 7.8, 8.7):
        a.plot([x, x], [bot - 0.05, top + 0.05], "k:", lw=0.6)
    a.plot([5.0], [(top + bot) / 2], "o", color="k", ms=6)
    for x in (2.7, 1.75, 7.3, 8.2):
        a.plot([x], [(top + bot) / 2], "o", color="gray", ms=4)
    a.text(5.0, bot - 0.35, "part's node", ha="center", fontsize=7.5)
    a.text(0.5, bot - 0.35, "grey: ring nodes\n(painted as a field)", fontsize=7, va="top")
    D.arrow(a, 5.0, top + 0.9, 5.0, top + 0.25, color=D.HEAT)
    a.text(5.0, top + 1.05, "q'' = P / A of the footprint", ha="center", fontsize=7.5, color=D.HEAT)
    a.text(0.5, -1.6, "No surface temperature (n/a). The text quotes q'' t / 2k:\na measured upper value for surface minus column, not a guarantee\n"
           "(fails for heat from a hotter neighbour, absent copper, thick plates)", fontsize=7)
    a.set_title("(a) Lumped: no heat flux through the face,\nso no surface; a text with the term only", fontsize=9)
    # (b) Analytic: uniform sheet, nodes at mid-thickness, uniform conductances
    b = axs[1]
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
    b.text(0.3, -1.6, "q_top = q_src - h_top_eff theta_1;  q_bot = - g_diel (theta_1 - theta_2)  ->  parabola: an estimate\n"
           "vias, blocks, heatsinks are not in g_diel; a face with a part over absent copper: n/a", fontsize=7)
    b.set_title("(b) Analytic: fluxes from its own field and the\nuniform conductances of its sheet (estimate)", fontsize=9)
    # (c) 3D solid with n copper slabs
    c = axs[2]
    top, bot = _plate(c, n_cu=4, lam=True)
    dz = (top - bot) / 4
    c.plot([5.0] * 4, [top - dz * (i + 0.5) for i in range(4)], "o", color="k", ms=4)
    D.arrow(c, 5.0, top + 0.9, 5.0, top + 0.25, color=D.HEAT, label="q_face")
    c.annotate("", xy=(7.2, top), xytext=(7.2, top - dz / 2), arrowprops=dict(arrowstyle="<->"))
    c.text(7.35, top + 0.35, "half slab dz/2:\nface = outer slab\n+ q_face dz / 2k", fontsize=7.5, va="bottom")
    c.text(0.3, -1.6, "above 105 um (2 to 8 slabs): face = outer slab + half slab, computed; column = mean of the slabs\n"
           "35 to 105 um (1 slab): the parabola fed with the solid's own links, an estimate", fontsize=7)
    c.set_title("(c) 3D solid: every conductance is in the matrix;\nthe face from the outer copper slab", fontsize=9)
    D.save(fig, str(OUT))


if __name__ == "__main__":
    main()
