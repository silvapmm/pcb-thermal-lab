#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures from the tables the studies printed: error of the via effect against the distance to the edge (figure 02) and against the edge film (figure 03).
@details Reads `out/sweep.txt` (study_edge_sweep.py) and `out/abs_films.txt` (study_edge_absolute.py --part films); run those first.
         Run from the repository root: `.venv/bin/python research/via-edge-image/scripts/make_figures.py`.
"""

import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(ROOT, "figures")


def parse_sweep(path):
    """!
    @brief Read the tables of study_edge_sweep.py.
    @param path File.
    @return dict {(h_side, mode, cell_index): [(d, error_percent), ...]}.
    """
    out, h = {}, None
    for line in open(path):
        m = re.match(r"## h_side = (\S+) W/m2K", line)
        if m:
            h = float(m.group(1))
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if h is not None and len(cols) >= 5 and cols[2] in ("program", "mirror", "robin"):
            for k, v in enumerate(cols[3:]):
                out.setdefault((h, cols[2], k), []).append((float(cols[0]), float(v.replace("%", "").replace("+", ""))))
    return out


def fig_02():
    """!
    @brief Figure 02: error of the via effect against the distance, for h_side 0 and 1000, three cells.
    @return None.
    """
    data = parse_sweep(os.path.join(ROOT, "out", "sweep.txt"))
    cells = ["1 mm", "0.5 mm", "0.25 mm"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, h in zip(axs, (0.0, 1000.0)):
        for k, col in zip(range(3), ("#c0392b", "#e67e22", "#7d3c98")):
            for mode, ls in (("program", "--"), ("mirror", "-")):
                pts = data[(h, mode, k)]
                ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, marker="o", ms=3, color=col, label=f"{mode}, {cells[k]}")
        ax.set_xscale("log")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("distance of the via from the edge (mm)")
        ax.set_title(f"h_side = {h:g} W/m2K", fontsize=9)
    axs[0].set_ylabel("error of the via effect (% of E)")
    axs[0].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_edge_error_against_distance.png"), dpi=140)
    plt.close(fig)


def fig_03():
    """!
    @brief Figure 03: error of T_max (K) against the edge film for the nearest via and 1 mm cells: program and mirror.
    @return None.
    """
    rows = []
    for line in open(os.path.join(ROOT, "out", "abs_films.txt")):
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) == 8 and re.match(r"^[0-9.e+]+$", cols[0]) and cols[1] == "0.16" and cols[4] == "1":
            rows.append((float(cols[0]), float(cols[2]), float(cols[3]), [float(c.split("/")[0]) for c in cols[5:8]]))
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    hs = [r[0] for r in rows]
    ax.plot(range(len(hs)), [r[3][0] for r in rows], "o--", color="#c0392b", label="program")
    ax.plot(range(len(hs)), [r[3][1] for r in rows], "s-", color="#2471a3", label="mirror image")
    ax.plot(range(len(hs)), [-r[2] * 0 for r in rows], color="k", lw=0.4)
    ax.set_xticks(range(len(hs)))
    ax.set_xticklabels([f"{h:g}\n(E {r[2]:.3f} K)" for h, r in zip(hs, rows)], fontsize=7)
    ax.set_xlabel("h_side (W/m2K) and the via effect E of the reference")
    ax.set_ylabel("error of T_max (K)")
    ax.set_title("1 mm cell, via 0.16 mm from the edge", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_edge_error_against_film.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_02()
    fig_03()
