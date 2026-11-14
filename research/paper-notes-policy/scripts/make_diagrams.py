#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Draw the diagram of what crosses the line between the local papers library and git.

Run from the repository root: .venv/bin/python research/paper-notes-policy/scripts/make_diagrams.py
Writes figures/fig_01_paper_to_note_line.png. No data, no program; the picture is schematic.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "figures"


def box(ax, x, y, w, h, text, fc):
    """!
    @brief Draw a rounded box with centred text.

    @param ax    Matplotlib axes.
    @param x     Left edge.
    @param y     Bottom edge.
    @param w     Width.
    @param h     Height.
    @param text  Text in the box.
    @param fc    Face colour.
    @return None
    """
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=fc, ec="#333", lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)


def main():
    """!
    @brief Make figure 1.

    @return None
    """
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    # Left of the line: local only (never committed); right: in git.
    ax.add_patch(plt.Rectangle((0, 0), 5.35, 5.2, fc="#fbeaea", ec="none"))
    ax.add_patch(plt.Rectangle((5.35, 0), 5.65, 5.2, fc="#e9f5e9", ec="none"))
    ax.axvline(5.35, color="#a00", lw=3)
    ax.text(2.6, 4.95, "LOCAL ONLY: papers/ (git-ignored)", ha="center", fontsize=10, weight="bold", color="#a00")
    ax.text(8.2, 4.95, "IN GIT (MIT repository, public)", ha="center", fontsize=10, weight="bold", color="#060")
    box(ax, 0.2, 3.4, 2.2, 1.0, "paper / book / standard\n(PDF, copyrighted)", "#fff")
    box(ax, 2.9, 3.4, 2.2, 1.0, "OCR text, verified\nagainst page images\n(reproduction)", "#fff")
    box(ax, 5.7, 3.4, 2.4, 1.0, "own-words NOTE\n(template, <= 150 words,\nequations as facts)", "#fff")
    box(ax, 8.6, 3.4, 2.2, 1.0, "docs/theory.md,\nBIBLIOGRAPHY key,\nprogram docstrings", "#fff")
    for x0, x1 in ((2.4, 2.9), (5.1, 5.7), (8.1, 8.6)):
        ax.annotate("", xy=(x1, 3.9), xytext=(x0, 3.9), arrowprops=dict(arrowstyle="->", lw=1.6))
    ax.text(2.75, 4.05, "read", fontsize=7.5, ha="center")
    ax.text(5.4, 4.05, "write in\nown words", fontsize=7.5, ha="center", color="#a00")
    ax.text(8.35, 4.05, "cite by key", fontsize=7.5, ha="center")
    ax.text(2.6, 2.7, "stays on the left: figures, tables as a block, text, OCR pages,\n"
            "paragraphs, the PDF, anything of a confidential file", ha="center", fontsize=8.5, color="#a00")
    ax.text(8.2, 2.7, "may cross: bibliographic data, equations and numbers as facts\n"
            "(with equation and page), short quotation <= 25 words,\nour own account, limits, reading status",
            ha="center", fontsize=8.5, color="#060")
    box(ax, 0.3, 0.5, 4.8, 1.3, "local checks (developer tool):\nsimilarity of the note against the OCR text\n(run of >= 8 identical words, 6-gram share)", "#fff")
    box(ax, 5.7, 0.5, 5.1, 1.3, "repository test (CI, needs no papers/):\ntemplate fields, word limits, no OCR markers,\nno images, no tracked path under papers/", "#fff")
    fig.tight_layout()
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "fig_01_paper_to_note_line.png", dpi=130)


if __name__ == "__main__":
    main()
