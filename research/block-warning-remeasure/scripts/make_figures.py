#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Plot the error of the Lumped and Analytic against the FVM from the CSV written by study_block_pads.py (figures/fig_02_block_errors.png).
@details Run: .venv/bin/python research/block-warning-remeasure/scripts/study_block_pads.py --set all --cell-mm 0.5 --csv research/block-warning-remeasure/out/cell05.csv
         then .venv/bin/python research/block-warning-remeasure/scripts/make_figures.py (from the repository root).
"""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    """!
    @brief Bar chart of hottest-point and worst-part error of both models for every case of the CSV; the 5 % line is the claim under test.
    @return None.
    """
    rows = list(csv.DictReader(open(ROOT / "out" / (sys.argv[1] if len(sys.argv) > 1 else "cell05.csv"))))
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    x = range(len(rows))
    for ax, (k, t) in zip(axs, (("hot", "hottest point of the board"), ("part_max", "worst part"))):
        ax.bar([i - 0.2 for i in x], [float(r[f"lumped_{k}"]) for r in rows], 0.4, label="Lumped", color="#1f77b4")
        ax.bar([i + 0.2 for i in x], [float(r[f"analytic_{k}"]) for r in rows], 0.4, label="Analytic", color="#e0a458")
        ax.axhspan(-5, 5, color="#cccccc", alpha=0.4, label="within 5 % (the claim)")
        ax.set_ylabel(f"error vs FVM, % of rise\n{t}")
        ax.legend(fontsize=7)
    axs[1].set_xticks(list(x))
    axs[1].set_xticklabels([r["label"] for r in rows], rotation=80, ha="right", fontsize=6)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "fig_02_block_errors.png", dpi=130)


if __name__ == "__main__":
    main()
