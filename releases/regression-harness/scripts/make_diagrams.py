#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawing of the flow of the release regression (no data, no solver): the two revisions, the same harness, the two result sets, the diff and the classes, the independent reference and the frozen file.
@details Figure 01 of figures/ (the data figures from 02 on are drawn by make_figures.py, one numbering). It shows no number.
         File: fig_01_regression_flow.png.
         Usage: .venv/bin/python releases/regression-harness/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "research"))                    # the shared shapes stay in research/diagram_kit.py (this folder moved to releases/)

import diagram_kit as dk                                                    # noqa: E402

OUT = HERE.parent / "figures"


def flow():
    """!
    @brief Draw the flow of the regression and save fig_01.
    @return None.
    """
    fig, ax = dk.canvas(11.5, 6.4)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 13)
    ax.axis("off")
    # left column: the two program trees
    dk.box(ax, 0.3, 9.6, 4.4, 2.2, "release v2.4.4\n(git archive of the tag,\nscratch folder outside the repo)", "#e8e8e8")
    dk.box(ax, 0.3, 5.6, 4.4, 2.2, "release candidate 2.4.5\n(the working tree)", "#e8e8e8")
    # the harness takes both
    dk.box(ax, 6.2, 7.0, 4.4, 3.4, "same harness\n17 boards x 5 models\nx cells 2 / 1 / 0.5 mm\nsteady + t63 + SOR\n(memory caps)", "#cfe3f5", bold=True)
    dk.arrow(ax, 4.7, 10.7, 6.2, 9.4)
    dk.arrow(ax, 4.7, 6.7, 6.2, 8.0)
    # the two result sets
    dk.box(ax, 12.0, 9.6, 3.6, 2.2, "result set\nv2.4.4.json", "#fbe3c7")
    dk.box(ax, 12.0, 5.6, 3.6, 2.2, "result set\nrc.json", "#fbe3c7")
    dk.arrow(ax, 10.6, 9.4, 12.0, 10.4)
    dk.arrow(ax, 10.6, 8.0, 12.0, 6.8)
    # diff and classification
    dk.box(ax, 17.0, 7.0, 5.6, 3.4, "diff + classify\nagainst expected_shifts.json\nexpected / out of range /\nto be explained / unexplained /\nmust not move", "#d9ead3", bold=True)
    dk.arrow(ax, 15.6, 10.4, 17.0, 9.6)
    dk.arrow(ax, 15.6, 6.8, 17.0, 7.8)
    # independent reference
    dk.box(ax, 6.2, 1.0, 4.4, 2.4, "independent layered 3D solver\n(4 reference boards, same cell)", "#e6d9f0")
    dk.arrow(ax, 10.6, 2.2, 12.0, 2.2, "#6a3d9a")
    dk.arrow(ax, 13.8, 5.6, 13.8, 3.4, "#6a3d9a")
    dk.box(ax, 12.0, 1.0, 3.6, 2.4, "error of each model\nbefore and after", "#e6d9f0")
    dk.arrow(ax, 15.6, 2.2, 17.0, 2.2, "#6a3d9a")
    # freeze
    dk.box(ax, 17.0, 0.8, 5.6, 3.0, "freeze (after the diff shows no alarm)\nreference/v2.4.5.json\n'bit' or 'moved' per record", "#fff2cc", bold=True)
    dk.arrow(ax, 19.8, 7.0, 19.8, 3.8)
    # the permanent test
    dk.box(ax, 17.0, 11.2, 5.6, 1.6, "test_frozen_numbers.py\nnext versions: run vs frozen file", "#fff2cc")
    dk.arrow(ax, 19.8, 3.8, 22.9, 3.8, "#999999", style="-")
    dk.arrow(ax, 22.9, 3.8, 22.9, 12.0, "#999999", style="-")
    dk.arrow(ax, 22.9, 12.0, 22.6, 12.0, "#999999")
    dk.save(fig, OUT / "fig_01_regression_flow.png", "Release regression: one harness, two revisions, a classified diff and a frozen reference")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    flow()
