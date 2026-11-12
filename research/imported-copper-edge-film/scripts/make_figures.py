#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figure of the edge-film study: mean error and spread of the program's film and of the centroid film against the edge coefficient, 1 mm cell.
@details Figure 3 (`fig_03_film_against_h_side.png`) plots the numbers of the table of README 3.2 (columns c0 program and c9 centroid film, rows of the 1 mm
         cell at `h_side` 10, 50, 500 and 1000 W/m2K; mean and spread in per cent against the 3D truth). The numbers are copied from that table, which the
         studies of `scripts/study_candidates.py` print; nothing is recomputed here.
         Run from the repository root: `.venv/bin/python research/imported-copper-edge-film/scripts/make_figures.py`.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")

# h_side (W/m2K): (mean, spread) of c0 (the program's node film) and of c9 (the centroid film), cell 1 mm, README 3.2
H = (10, 50, 500, 1000)
C0 = ((-0.43, 0.76), (-1.08, 0.76), (-4.90, 3.78), (-6.36, 5.10))
C9 = ((-0.39, 0.79), (-0.63, 1.16), (-1.13, 2.84), (-1.26, 3.60))


def fig_film():
    """!
    @brief Figure 3: mean error and spread over the turn angles against the edge coefficient, node film against centroid film.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.8))
    for ax, k, title in ((axs[0], 0, "mean error of the hottest rise (%)"), (axs[1], 1, "spread over the turn angles (%)")):
        ax.plot(range(len(H)), [v[k] for v in C0], "o--", color="#c0392b", label="c0: film on the node (program before)")
        ax.plot(range(len(H)), [v[k] for v in C9], "s-", color="#2471a3", label="c9: centroid film")
        ax.set_xticks(range(len(H)))
        ax.set_xticklabels([f"{h}" for h in H])
        ax.set_xlabel("h_side (W/m2K), 1 mm cell")
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_film_against_h_side.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    fig_film()
