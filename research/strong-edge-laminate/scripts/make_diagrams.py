#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagram of the strong-edge study: the laminate that each layer node holds in the simple stack-up (equal slabs) and with the physical slabs.
@details Figure 3 (`fig_03_simple_and_physical_slabs.png`), a drawing of the situation of README 8.2 with the numbers that README quotes (0.4 mm for every
         node of the simple stack-up; 0.28 mm for an outer copper node and 0.52 mm for an inner one with the physical slabs). No data and no program.
         Run from the repository root: `.venv/bin/python research/strong-edge-laminate/scripts/make_diagrams.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import diagram_kit as dk                                            # noqa: E402

FIG = os.path.join(os.path.dirname(HERE), "figures")


def fig_slabs():
    """!
    @brief Figure 3: a four-layer board at the cooled wall, the laminate held by every copper node in the two stack-up rules.
    @return None.
    """
    fig, axs = dk.canvas(11, 4.6, ncols=2)
    rules = (("simple stack-up: every node stands for an equal share T / L", (0.4, 0.4, 0.4, 0.4), "0.4 mm"),
             ("physical slabs: each node holds half of the gaps next to it", (0.28, 0.52, 0.52, 0.28), "0.28 / 0.52 mm"))
    for ax, (title, slabs, label) in zip(axs, rules):
        ax.set_xlim(0, 10)
        ax.set_ylim(-0.6, 8.6)
        ax.axis("off")
        ax.set_title(title, fontsize=9)
        y = 7.0
        for k, s in enumerate(slabs):
            h = 10.0 * s / 1.6 * 0.5                                # laminate shown to scale of 1.6 mm over 5 drawing units
            dk.layer(ax, 1.2, y - h / 2, 6.0, h, dk.FR4, "")        # the laminate the node holds
            dk.layer(ax, 1.2, y - 0.09, 6.0, 0.18, dk.COPPER, f"copper {k + 1}", size=7)
            ax.text(7.5, y, f"{slabs[k]:g} mm", fontsize=8, va="center")
            y -= 2.0
        dk.arrow(ax, 9.0, 6.4, 9.0, 0.8, color="#b03030", style="<-", label="film of the wall", size=7)
        ax.text(1.2, -0.4, f"laminate held by a node: {label}; the wall film acts on it at the copper temperature", fontsize=7)
    dk.save(fig, os.path.join(FIG, "fig_03_simple_and_physical_slabs.png"))


if __name__ == "__main__":
    fig_slabs()
