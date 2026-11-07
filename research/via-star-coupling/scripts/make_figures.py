#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the via-star-coupling folder: the signed error of the via effect before and after the star on the review's reference set.
@details Reads the JSON files written by `study_reference_set.py` (`out/ref_solid.json` from the `solid` mode at 0.1 mm and 8 slabs, `out/ref_before.json` and
         `out/ref_after.json` from the `layered` mode on the tree before the star and on the branch) and draws `figures/fig_02_reference_set_errors.png`.
         Run from the repository root: `.venv/bin/python research/via-star-coupling/scripts/make_figures.py`.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
CASES = ["full d0.3", "full d1.5", "arr3 p1.0", "edge 0.35", "corner 0.35", "track 0.25", "quarter", "bareout g0.3", "bareout g0.6"]
LABELS = ["full, 0.3 mm", "full, 1.5 mm via\nunder 1 mm part", "3 x 3 array\n1.0 mm pitch", "0.35 mm from\nan edge", "0.35 mm from\na corner",
          "0.25 mm track\nending on it", "corner of a\ncopper quadrant", "bare laminate\n0.3 mm outside", "bare laminate\n0.6 mm outside"]


def fig_errors(path):
    """!
    @brief Signed error of the FVM via effect against the 3D solid, before and after, at 1, 0.5 and 0.25 mm (the largest errors are clipped at +300 % and labelled).
    @param path Output PNG.
    @return None.
    """
    out = os.path.join(FOLDER, "out")
    solid = json.load(open(os.path.join(out, "ref_solid.json")))
    before = json.load(open(os.path.join(out, "ref_before.json")))
    after = json.load(open(os.path.join(out, "ref_after.json")))
    cells = ("1.0", "0.5", "0.25")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5), sharey=True)
    clip = 300.0
    for ax, cell in zip(axes, cells):
        for k, (data, name, colour, dx) in enumerate(((before, "mean-potential (before)", "#4a6a96", -0.2), (after, "star (after)", "#c0602a", 0.2))):
            errs = []
            for c in CASES:
                ref = solid.get(f"{c}|solid|0.1|8", solid.get(f"{c}|solid|0.1|4"))
                errs.append(100.0 * (data[f"{c}|fvm|{cell}"] / ref - 1.0))
            xs = [i + dx for i in range(len(CASES))]
            ax.bar(xs, [max(-100.0, min(clip, e)) for e in errs], width=0.38, color=colour, label=name)
            for x, e in zip(xs, errs):
                if e > clip:
                    ax.text(x, clip + 5, f"{e:+.0f}", ha="center", va="bottom", fontsize=7, rotation=90)
        ax.axhline(0.0, color="black", lw=0.8)
        ax.axhspan(0.0, clip + 60, color="#f3e0d6", alpha=0.35, zorder=0)
        ax.set_title(f"FVM, cell {cell} mm")
        ax.set_xticks(range(len(CASES)))
        ax.set_xticklabels(LABELS, rotation=60, ha="right", fontsize=7)
        ax.set_ylim(-100, clip + 60)
    axes[0].set_ylabel("error of the via effect against the 3D solid, %\n(shaded: via effect too large, part reads too cool)")
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Review's reference set (10 x 10 mm boards, 3D solid at 0.1 mm, 8 slabs): the star against the mean-potential via")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    """!
    @brief Draw every data figure of the folder.
    @return None.
    """
    fig_errors(os.path.join(FOLDER, "figures", "fig_02_reference_set_errors.png"))


if __name__ == "__main__":
    main()
