#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: a small passive on a pad and a neck of copper (section and plan) and the three ways a model sees it. No data, no program.
@details Writes figures/fig_01_pad_neck_section.png (section with the heat paths) and figures/fig_02_three_views.png (what the FVM on the imported copper, the arithmetic cell fill and the
         uniform sheet of the reduced models see). Run: .venv/bin/python research/reduced-models-imported-passives/scripts/make_diagrams.py
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

FIG = HERE.parent / "figures"


def fig_section():
    """!
    @brief Section of the board under a 0402 part: the pad on a narrow track, the plane layer below, the heat paths.
    @return None.
    """
    fig, ax = dk.canvas(9, 4.2)
    ax.set_xlim(0, 12); ax.set_ylim(-0.5, 5.2); ax.set_aspect("auto")
    dk.layer(ax, 0, 1.6, 12, 1.6, dk.FR4, "FR-4 laminate (0.3 W/mK)")
    # Top copper: wide plane on the left, a thin track (neck), the pad under the part
    dk.layer(ax, 0, 3.2, 3.2, 0.25, dk.COPPER)
    dk.layer(ax, 3.2, 3.2, 3.6, 0.25, dk.COPPER)
    dk.layer(ax, 6.8, 3.2, 1.0, 0.25, dk.COPPER, "")
    dk.layer(ax, 7.8, 3.2, 4.2, 0.25, dk.AIR)
    dk.layer(ax, 0, 1.35, 12, 0.25, dk.COPPER)
    ax.text(0.1, 4.3, "top copper: plane", fontsize=7); ax.text(3.6, 4.3, "track (the neck)", fontsize=7); ax.text(6.55, 3.85, "pad", fontsize=7)
    ax.text(0.1, 1.05, "second copper layer", fontsize=7)
    dk.layer(ax, 6.4, 3.45, 1.8, 0.7, "#555555", "0402 part, 1 W", 7)
    # Heat paths
    for x in (7.0, 7.4):
        dk.arrow(ax, x, 3.3, x, 1.75, color=dk.HEAT, width=1.2)
    dk.arrow(ax, 6.8, 3.33, 3.5, 3.33, color=dk.HEAT, width=2.2, label="through the neck")
    dk.arrow(ax, 3.3, 3.33, 0.4, 3.33, color=dk.HEAT, width=1.0, label="spreads in the plane")
    ax.text(7.6, 2.3, "down through the laminate:\nlocal, set by the pad area", fontsize=7, color=dk.HEAT)
    ax.text(3.2, 0.3, "A model that sees only the AVERAGE copper of a 0.5 to 1 mm cell cannot show the neck:\nthe pad and the track are smaller than the cell it uses for the copper.",
            fontsize=8, ha="left")
    dk.save(fig, FIG / "fig_01_pad_neck_section.png", "Section of a small part on a pad joined by a narrow track")
    return


def fig_views():
    """!
    @brief Plan view of the same pad and track as the three treatments see them.
    @return None.
    """
    fig, axs = dk.canvas(10, 3.4, 1, 3)
    n = 40
    img = np.zeros((n, n))
    img[:, :6] = 1.0                       # plane on the left
    img[18:22, 6:30] = 1.0                 # the track
    img[14:26, 30:36] = 1.0                # the pad
    titles = ("FVM on the imported copper\n(faces: the pattern at 0.05 mm)", "Arithmetic fill of a 0.5 mm cell\n(smeared, 'fill' mapping)", "Uniform sheet of the layer\n(what the reduced models average over)")
    sm = np.kron(img, np.ones((1, 1)))
    k = 5
    smeared = sm.reshape(n // k, k, n // k, k).mean(axis=(1, 3))
    uni = np.full_like(sm, img.mean())
    for ax, a, t in zip(axs, (sm, smeared, uni), titles):
        ax.axis("on"); ax.set_xticks([]); ax.set_yticks([])
        ax.imshow(a, cmap="YlOrBr", vmin=0, vmax=1, extent=(0, n, 0, n), origin="upper", interpolation="nearest")
        ax.add_patch(Rectangle((30, 14), 6, 12, fill=False, edgecolor="k", linewidth=1.2))
        ax.set_title(t, fontsize=8)
    axs[0].text(1, 36, "plane", fontsize=7); axs[0].text(12, 24, "track", fontsize=7); axs[0].text(30, 10, "part", fontsize=7)
    dk.save(fig, FIG / "fig_02_three_views.png", "The same 1 W part seen three ways (schematic, not a board of the library)")


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_section()
    fig_views()
