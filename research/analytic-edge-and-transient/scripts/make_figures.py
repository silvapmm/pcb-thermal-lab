#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures with data of the analytic-edge-and-transient investigation: fig_02 per-layer edge error on 48 boards, fig_04 time to 63 % error per board and model, fig_05 step responses,
       fig_06 (review) the two calibrations of the local transient against the converged FVM, fig_07 (review) the per-layer edge against the FVM with and without the laminate sub-gaps.

@details Needs out/perlayer_54.txt (study_perlayer_edge.py --part 2), out/transient_both.txt (study_transient_both.py) and out/review.txt (study_review.py);
         fig_05 computes its curves.
         Run from the repository root: .venv/bin/python research/analytic-edge-and-transient/scripts/make_figures.py
"""

import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, HERE)
FIG = os.path.join(ROOT, "figures")
OUT = os.path.join(ROOT, "out")


def fig_02():
    """!
    @brief Error against the FVM of the program's common beta and of the per-layer edge, 48 boards of 2 or more layers, against the edge share.
    @return None.
    """
    a = np.loadtxt(os.path.join(OUT, "perlayer_54.txt"))[:48]
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4))
    for ax, col, title in ((axs[0], 2, "program (one beta)"), (axs[1], 3, "per-layer edge")):
        sc = ax.scatter(a[:, 1], a[:, col], c=np.log10(a[:, 0]), cmap="viridis", s=28)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_ylim(-10, 7)
        ax.set_xlabel("edge share of the loss coefficient")
        ax.set_ylabel("hottest rise, % of the FVM at 0.5 mm")
        ax.set_title(title)
    fig.colorbar(sc, ax=axs, label="log10 of the spread of slab / S")
    fig.savefig(os.path.join(FIG, "fig_02_perlayer_error.png"), dpi=105, bbox_inches="tight")
    plt.close(fig)


def parse_transient():
    """!
    @brief Read out/transient_both.txt.
    @return dict board -> dict model -> t63 error in percent.
    """
    data, board = {}, None
    for line in open(os.path.join(OUT, "transient_both.txt")):
        if line.startswith("board") or not line.strip():
            continue
        if not line.startswith(" "):
            board = line[:24].strip()
            data[board] = {}
            continue
        m = re.match(r"\s+(\S+(?: K\d+)?)\s+([\d.]+)\s+([\d.]+)\s+([+-][\d.]+)\s+([\d.]+)", line)
        if m and board:
            data[board][m.group(1)] = float(m.group(4))
    return data


def fig_04():
    """!
    @brief Error of the time to 63 % against the FVM at 1 mm, per board: Lumped, Analytic as in the program, local K16 and K24.
    @return None.
    """
    d = parse_transient()
    boards = [b for b in d if "analytic/program" in d[b] and abs(d[b]["analytic/program"]) > 1.0 or "local" in d[b] or True]
    boards = [b for b in d if d[b]]
    keys = [("lumped", "Lumped"), ("analytic/program", "Analytic, program"), ("local K16", "local modal K16"), ("local K24", "local modal K24")]
    x = np.arange(len(boards))
    fig, ax = plt.subplots(figsize=(11, 4.3))
    for i, (k, lab) in enumerate(keys):
        ax.bar(x + (i - 1.5) * 0.2, [d[b].get(k, np.nan) for b in boards], 0.2, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(boards, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("time to 63 %, error against the FVM (%)")
    ax.set_ylim(-70, 120)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_04_t63_error.png"), dpi=105, bbox_inches="tight")
    plt.close(fig)


def fig_05():
    """!
    @brief Step responses of the part on the board with vias and a heatsink under it: FVM, Analytic as in the program, local modal K24, Lumped.
    @return None.
    """
    import boards26 as B
    import local_modal as LM
    p = B.with_sink(B.with_vias(B.plain()))
    fig, ax = plt.subplots(figsize=(7, 4.2))
    t, z, r = B.step(p, "fvm", 1.0)
    ax.semilogx(t, z[0], "k", lw=2, label="FVM 1 mm")
    for model, lab, st in (("analytic", "Analytic, program", "--"), ("lumped", "Lumped", ":")):
        ti, zi, ri = B.step(p, model, 1.0)
        ax.semilogx(ti, zi[0], st, label=lab)
    ti, zi, ri, _ = LM.step_local(p, K=24)
    ax.semilogx(ti, zi[0], "-", label="local modal K24, one factor on all of C")
    ti, zi, ri, _ = LM.step_local(p, K=16, calibrate_on="vias")
    ax.semilogx(ti, zi[0], "-.", label="local modal K16, factor on the vias only (review)")
    ax.set_xlim(0.5, 600)
    ax.set_xlabel("time (s)")
    ax.set_ylabel("unit-step response of the part (K/W)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.savefig(os.path.join(FIG, "fig_05_step_vias_sink.png"), dpi=105, bbox_inches="tight")
    plt.close(fig)


def parse_review():
    """!
    @brief Read parts 1 and 4 of out/review.txt.
    @return Tuple (rows of part 1: (label, [program n4, program n1, per-layer n4, per-layer n1]), dict board -> [program, all, vias] t63 errors in percent).
    """
    p1, p4, part = [], {}, 0
    for line in open(os.path.join(OUT, "review.txt")):
        if re.match(r"^\d\.", line):
            part = int(line[0])
            continue
        if part == 1:
            m = re.match(r"\s+(.+?)\s*: FVM.*program\s+([+-][\d.]+) /\s+([+-][\d.]+) \| per-layer\s+([+-][\d.]+) /\s+([+-][\d.]+)", line)
            if m:
                p1.append((m.group(1).strip(), [float(m.group(k)) for k in range(2, 6)]))
        elif part == 4:
            m = re.match(r"\s+(.+?)\s+FVM .*program\s+([+-][\d.]+) %.*all .*?\(\s*([+-][\d.]+) %.*vias .*?\(\s*([+-][\d.]+) %", line)
            if m:
                p4[m.group(1).strip()] = [float(m.group(k)) for k in range(2, 5)]
    return p1, p4


def fig_06():
    """!
    @brief Review: time to 63 % against the FVM at 0.5 mm, the program, the local system with one factor on all of C, and with the factor on the vias only.
    @return None.
    """
    _, d = parse_review()
    boards = list(d)
    x = np.arange(len(boards))
    fig, ax = plt.subplots(figsize=(11, 4.3))
    for i, lab in enumerate(("Analytic, program", "local K16, one factor on all of C", "local K16, factor on the vias only")):
        vals = np.array([d[b][i] for b in boards])
        ax.bar(x + (i - 1) * 0.27, np.clip(vals, -70, 120), 0.27, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(boards, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("time to 63 %, error against the FVM at 0.5 mm (%)")
    ax.set_ylim(-70, 120)
    ax.text(x[-2] - 0.27, 112, f"{d[boards[-2]][0]:+.0f} %", ha="center", fontsize=7)
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_06_calibration_on_vias.png"), dpi=105, bbox_inches="tight")
    plt.close(fig)


def fig_07():
    """!
    @brief Review: hottest-rise error of the program and of the per-layer edge against the FVM with the laminate rule (n 4) and with one laminate link (n 1).
    @return None.
    """
    rows, _ = parse_review()
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(10, 4.2))
    labs = ("program, FVM n 4", "program, FVM n 1", "per-layer, FVM n 4", "per-layer, FVM n 1")
    for i, lab in enumerate(labs):
        ax.bar(x + (i - 1.5) * 0.2, [r[1][i] for r in rows], 0.2, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([r[0] for r in rows], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("hottest rise, % of the FVM at 0.5 mm")
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_07_perlayer_laminate.png"), dpi=105, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_02()
    fig_04()
    fig_05()
    fig_06()
    fig_07()
