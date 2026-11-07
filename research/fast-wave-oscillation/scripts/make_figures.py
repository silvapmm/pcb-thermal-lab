#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures 2 to 4 of the study from out/sweep_e3.json and out/sweep.json (run study_fast_wave_sweep.py and study_estimator.py first), and figures 6 and 7 of the
       review from out/review_*.json (run study_review_reference.py first).

@details Run from the repository root: `.venv/bin/python research/fast-wave-oscillation/scripts/make_figures.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
import matplotlib                                                    # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402
import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
import columns as Cn                                                 # noqa: E402

OUT = os.path.join(HERE, "..", "out")
FIG = os.path.join(HERE, "..", "figures")


def fig_swing(d):
    """!
    @brief Figure 2: swing per watt against frequency, reference / program / E3, three part sizes (2 layers, duty 0.3, h 10), and the ratio program / reference for 1, 2, 4 layers.
    @param d Sweep records with e3.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for side, c in ((2.0, "C0"), (5.0, "C1"), (10.0, "C2")):
        row = [r for r in d if r["layers"] == 2 and r["side"] == side and r["h"] == 10 and r["duty"] == 0.3]
        f = [r["f"] for r in row]
        ax[0].loglog(f, [r["ref_center"] for r in row], "-", color=c, label=f"{side:g} mm reference")
        ax[0].loglog(f, [r["prog_decision"] for r in row], "--", color=c, label="program")
        ax[0].loglog(f, [r["e3"] for r in row], "o", ms=3, color=c, label="E3 (closed form)")
    ax[0].set_xlabel("frequency (Hz)"); ax[0].set_ylabel("peak-to-peak rise per watt (K/W)")
    ax[0].set_title("2 layers, duty 30 %, h 10 W/m2K"); ax[0].legend(fontsize=6, ncol=3); ax[0].grid(True, which="both", alpha=0.3)
    for L, c in ((1, "C3"), (2, "C0"), (4, "C2")):
        for side, ls in ((2.0, ":"), (5.0, "--"), (10.0, "-")):
            row = [r for r in d if r["layers"] == L and r["side"] == side and r["h"] == 10 and r["duty"] == 0.5]
            ax[1].semilogx([r["f"] for r in row], [r["prog_decision"] / r["ref_center"] for r in row], ls, color=c, label=f"{L} layers {side:g} mm")
    ax[1].axhline(1.0, color="k", lw=0.8)
    ax[1].set_xlabel("frequency (Hz)"); ax[1].set_ylabel("program / reference"); ax[1].set_title("what the decision sees, duty 50 %")
    ax[1].legend(fontsize=6, ncol=3); ax[1].grid(True, which="both", alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_02_swing_against_frequency.png"), dpi=130)


def fig_attribution():
    """!
    @brief Figure 3: the step response of the exact and the lumped column (cause) and the swing against the number of laminate cells (cure by discretisation).
    @return None.
    """
    st = A.Stack(layers=2)
    area = 1e-4
    t = np.geomspace(1e-6, 1e3, 200)
    ex = Cn.exact_column(st, area, 10, 10)
    lu = Cn.lumped_column(st, area, 10, 10)
    ref = A.Reference(st, A.part_radius(10e-3), A.rectangle_radius(60e-3, 40e-3), 10, 10)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].loglog(t, ex.step(t, "top"), label="exact column (copper + laminate resolved)")
    ax[0].loglog(t, lu.step(t, "top"), "--", label="program column (one node per layer)")
    ax[0].loglog(t, ref.step(t, "center"), ":", label="2D reference (10 mm part)")
    ax[0].set_xlabel("time (s)"); ax[0].set_ylabel("step response (K/W)"); ax[0].legend(fontsize=7); ax[0].grid(True, which="both", alpha=0.3)
    ax[0].set_title("10 mm part, 2 layers: the first seconds")
    ns = [2, 4, 8, 16, 32, 64]
    gr = []
    for n in ns:
        m = Cn.exact_column(st, area, 10, 10, n_cu=2, n_gap=n // 2)
        r = m.square_wave(1 / 20.0, 0.3, "top")
        gr.append((r[0] - r[1]) * 10)
    ax[1].semilogx(ns, gr, "o-", label="graded cells (1.5 um at each copper face)")
    un = []
    ns2 = [1, 2, 4, 8, 16, 64, 256]
    for n in ns2:
        dz = np.concatenate([[st.t_cu], np.full(n, (st.thickness - 2 * st.t_cu) / n), [st.t_cu]])
        kz = np.concatenate([[st.k_cu], np.full(n, st.kz), [st.k_cu]])
        rc = np.concatenate([[st.rho_cp_cu], np.full(n, st.rho_cp_lam), [st.rho_cp_cu]])
        C, K = Cn._chain(dz, kz, rc, area, 10, 10)
        q = np.zeros(len(dz)); q[0] = 1
        r = Cn.Modal(C, K, q, {"top": q.copy()}).square_wave(1 / 20.0, 0.3, "top")
        un.append((r[0] - r[1]) * 10)
    ax[1].semilogx(ns2, un, "s--", label="equal sub-gaps (the laminate rule)")
    ax[1].axhline(6.37, color="k", lw=0.8, label="reference 6.37 K"); ax[1].axhline(0.753, color="r", lw=0.8, label="program 0.75 K")
    ax[1].set_xlabel("laminate cells across the gap"); ax[1].set_ylabel("swing, 10 W, 20 Hz, 30 % (K)"); ax[1].legend(fontsize=7); ax[1].grid(True, which="both", alpha=0.3)
    ax[1].set_title("the cure by cells is expensive")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_03_column_and_cells.png"), dpi=130)


def fig_decision(d):
    """!
    @brief Figure 4: where the decision is wrong, for the 10 mm part of 2 layers: power of the part against frequency (duty 30 %), true swing above the budget but the program says average.
    @param d Sweep records with e3.
    @return None.
    """
    row = {r["f"]: r for r in d if r["layers"] == 2 and r["side"] == 10.0 and r["h"] == 10 and r["duty"] == 0.3}
    fs = sorted(row)
    P = np.geomspace(0.1, 100, 80)
    grid = np.zeros((len(P), len(fs)))
    for j, f in enumerate(fs):
        for i, p in enumerate(P):
            true = p * row[f]["ref_center"] > 1.0
            prog = p * row[f]["prog_decision"] > 1.0
            grid[i, j] = 2 if (true and not prog) else (1 if true else 0)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    edges = np.log10(np.geomspace(0.1 / 1.0, 100 * 1.0, len(P) + 1))
    ax.pcolormesh(np.arange(len(fs) + 1), edges, grid, cmap=matplotlib.colors.ListedColormap(["#d8e8d0", "#f2d38b", "#d9544d"]), shading="flat")
    ax.set_xticks(np.arange(len(fs)) + 0.5); ax.set_xticklabels([f"{f:g}" for f in fs], rotation=60, fontsize=7)
    ax.set_yticks(np.log10([0.1, 1, 10, 100])); ax.set_yticklabels(["0.1", "1", "10", "100"])
    ax.set_xlabel("frequency (Hz)"); ax.set_ylabel("swing of the power (W)")
    ax.set_title("10 mm part, 2 layers, 30 %: green average is right, amber resolve is right,\nred the program averages a wave whose swing exceeds 1 K", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_04_wrong_decisions.png"), dpi=130)


def fig_review():
    """!
    @brief Figure 6: the reviewer's 3D reference against the author's, the program and E3 (2 layers, duty 0.3, h 10), and E3 / reference on the cases the author did not test.
    @return None.
    """
    s = json.load(open(os.path.join(OUT, "review_sample.json")))
    c = json.load(open(os.path.join(OUT, "review_cases.json")))
    bare = os.path.join(OUT, "review_bare.json")
    if os.path.exists(bare):
        b = json.load(open(bare))
        c = [r for r in c if r["case"] not in {x["case"] for x in b}] + b
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
    for side, col in ((2.0, "C0"), (10.0, "C2")):
        row = sorted([r for r in s if r["layers"] == 2 and r["side"] == side and r["h"] == 10 and r["duty"] == 0.3], key=lambda r: r["f"])
        f = [r["f"] for r in row]
        ax[0].loglog(f, [r["ref"] for r in row], "-", color=col, lw=2, label=f"{side:g} mm: reviewer's 3D reference")
        ax[0].loglog(f, [r["author_ref"] for r in row], "o", color=col, mfc="none", label="author's axisymmetric reference")
        ax[0].loglog(f, [r["e3"] for r in row], "x", color=col, label="E3")
        ax[0].loglog(f, [r["fvm"] for r in row], "--", color=col, label="program FVM, cell side/4")
        ax[0].loglog(f, [r["fvm_2mm"] for r in row], ":", color=col, label="program FVM, 2 mm (application)")
    ax[0].set_xlabel("frequency (Hz)"); ax[0].set_ylabel("swing per watt of on-power (K/W)"); ax[0].legend(fontsize=6.5); ax[0].grid(True, which="both", alpha=0.3)
    ax[0].set_title("2 layers, duty 30 %, h 10 W/m2K", fontsize=9)
    show = ["inner layer 2 of 4, 10 mm", "16 vias under the part, 10 mm, 4 layers", "elongated 2 x 10 mm", "near the corner, 5 mm at (1, 1)",
            "no top copper at all, 10 mm", "computed h, 10 W steady (h_top 22.5, h_bottom 15.5)"]
    for k, name in enumerate(show):
        row = sorted([r for r in c if r["case"] == name and r["duty"] == 0.3], key=lambda r: r["f"])
        ax[1].semilogx([r["f"] for r in row], [r["e3"] / r["ref"] for r in row], "-o", ms=3, color=f"C{k}", label=name)
    ax[1].axhline(1.0, color="k", lw=0.8)
    ax[1].set_ylim(0, 1.8); ax[1].set_xlabel("frequency (Hz)"); ax[1].set_ylabel("E3 / reviewer's reference"); ax[1].legend(fontsize=6.5); ax[1].grid(True, which="both", alpha=0.3)
    ax[1].set_title("E3 (top-sheet formula, disc of equal area) on cases outside the author's family", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_06_review_reference_and_cases.png"), dpi=130)


def fig_node_cost():
    """!
    @brief Figure 7: swing of the program's node structure with n laminate sub-gaps per gap over the resolved 1D column (10 mm part, 2 layers, duty 0.3).
    @return None.
    """
    import study_resolved_curve as S
    import review_rect3d as R
    area, gap = 1e-4, 1.6e-3 - 2 * 35e-6
    freqs = np.geomspace(0.3, 3000, 15)
    exact = R.Response(S.column(area, 10.0, 6, S.graded(gap, 80, 0.3e-6), node_holds_half=False))
    ex = np.array([exact.swing(1 / f, 0.3) for f in freqs])
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for n, first, st in ((1, None, "k-"), (4, None, "C0--"), (16, None, "C0-"), (4, 5e-6, "C1--"), (8, 5e-6, "C1-")):
        ch = R.Response(S.column(area, 10.0, 1, S.graded(gap, n, first)))
        lab = f"{n} sub-gaps, " + ("equal" if first is None else f"graded, first {first * 1e6:.0f} um") + (" (the program today)" if n == 1 else "")
        ax.semilogx(freqs, [ch.swing(1 / f, 0.3) / e for f, e in zip(freqs, ex)], st, label=lab)
    ax.axhline(1.0, color="grey", lw=0.8)
    ax.set_xlabel("frequency (Hz)"); ax.set_ylabel("swing / resolved column"); ax.set_ylim(0, 1.2); ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=7)
    ax.set_title("cost of a correction by nodes (1D column, 10 mm part)", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "fig_07_review_node_cost.png"), dpi=130)


def main():
    """!
    @brief Draw figures 2 to 4 and, when the review outputs exist, 6 and 7.
    @return None.
    """
    d = json.load(open(os.path.join(OUT, "sweep_e3.json")))
    fig_swing(d)
    fig_attribution()
    fig_decision(d)
    if os.path.exists(os.path.join(OUT, "review_sample.json")):
        fig_review()
        fig_node_cost()


if __name__ == "__main__":
    main()
