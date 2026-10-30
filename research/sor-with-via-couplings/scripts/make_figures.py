#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the SOR-with-vias study: the real matrix, the convergence curves, the relaxation and stiffness sweeps, and the temperature error of the program's SOR.
@details Figures 04 to 07 of figures/ (the diagrams 01 to 03 are drawn by make_diagrams.py). Figures 05 and 06 read `out/study_variants.json` (run `study_variants.py` first);
         figures 04 and 07 are computed here from a small board.
         Files: fig_04_the_matrix_with_via_couplings.png, fig_05_convergence_of_the_variants.png, fig_06_omega_and_via_stiffness.png, fig_07_error_of_the_programs_sor.png.
         Usage: python research/sor-with-via-couplings/scripts/make_figures.py   (from the repository root).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import boards as bd                                                         # noqa: E402
import diagram_kit as dk                                                    # noqa: E402,F401
import sorvia as sv                                                         # noqa: E402
import matplotlib.pyplot as plt                                             # noqa: E402

OUT = HERE.parent / "figures"
DATA = HERE.parent / "out" / "study_variants.json"


def _spy(ax, K, Kv, perm, title):
    """!
    @brief Plot the entries of K in a given order: stencil and diagonal grey, positive via entries red, negative via entries blue.
    @param ax Axes.
    @param K Sparse matrix.
    @param Kv Sparse via part (off-diagonal entries only).
    @param perm Permutation (new order of the unknowns).
    @param title Title.
    @return None.
    """
    n = K.shape[0]
    inv = np.empty(n, int)
    inv[perm] = np.arange(n)
    Kc = K.tocoo()
    ax.scatter(inv[Kc.col], inv[Kc.row], s=1.0, c="#999999", marker="s", linewidths=0)
    Vc = Kv.tocoo()
    pos = Vc.data > 0
    ax.scatter(inv[Vc.col[pos]], inv[Vc.row[pos]], s=6, c="#d62728", marker="s", linewidths=0, label="via entries > 0")
    ax.scatter(inv[Vc.col[~pos]], inv[Vc.row[~pos]], s=6, c="#1f77b4", marker="s", linewidths=0, label="via entries < 0")
    ax.set_xlim(-1, n)
    ax.set_ylim(n, -1)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=9)
    ax.tick_params(labelsize=7)


def fig_matrix(path):
    """!
    @brief The real matrix of a 6 mm lone-via board (two layers, 0.5 mm cells), in the natural and in the red-black-via order.
    @param path Output file.
    @return None.
    """
    net = bd.net_for(bd.pc.lone_via_board(6.0, 0.3, 385.0, source_mm=1.5, distance_mm=1.5), 0.5)
    K = net.K.tocsr()
    Kv = sv.via_matrix(net)
    n = K.shape[0]
    li, ii, jj = np.indices((net.nl, net.ny, net.nx))
    col = ((li + ii + jj) % 2).ravel()
    isvia = np.zeros(n, bool)
    for b in sv.via_blocks(net):
        isvia[b] = True
    perm = np.argsort(np.where(isvia, 2, col), kind="stable")
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.4))
    _spy(axs[0], K, Kv, np.arange(n), f"natural order (layer, row, column), N = {n}")
    _spy(axs[1], K, Kv, perm, "red cells | black cells | via cells (the via block is dense)")
    axs[0].legend(loc="lower left", fontsize=7, markerscale=2)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_convergence(path):
    """!
    @brief Residual against sweeps on the 3 x 3 array at 0.5 mm: no-via board, the program's rule, lagged, block and the first solve of the Woodbury variant.
    @param path Output file.
    @return None.
    """
    d = json.load(open(DATA))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, key in zip(axs, ("lone via, 2 layers 0.5", "3 x 3 array 0.5")):
        r = d[key]
        ax.semilogy(*zip(*r["base_history"]), color="#555555", label="board without vias (program's SOR)")
        for v, c, lab in (("program", "#d62728", "program's rule on the board with vias"), ("lagged", "#1f77b4", "(a) lagged via part"),
                          ("block", "#2ca02c", "(c) via blocks"), ("woodbury", "#ff7f0e", "(b) Woodbury, first inner solve")):
            h = r[v]["history"]
            ax.semilogy(*zip(*h), color=c, label=lab, linestyle="--" if v == "woodbury" else "-")
        ax.set_xscale("log")
        ax.set_xlabel("sweeps (log scale; the program's rule stops at its 200000 limit)")
        ax.set_ylabel("relative residual of the true K")
        ax.set_title(key.replace(" 0.5", ", 0.5 mm cell"), fontsize=9)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_sweeps(path):
    """!
    @brief Sweeps against omega and against the stiffness of the via part.
    @param path Output file.
    @return None.
    """
    d = json.load(open(DATA))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    om = d["omega"]
    xs = [float(k) for k in om]
    for i, (lab, c) in enumerate((("board without vias", "#555555"), ("(a) lagged", "#1f77b4"), ("(c) blocks", "#2ca02c"))):
        ys = [om[k][i] if om[k][i] else np.nan for k in om]
        axs[0].semilogy(xs, ys, "o-", color=c, label=lab)
        fail = [x for x, k in zip(xs, om) if not om[k][i]]
        axs[0].plot(fail, [2.2e4] * len(fail), "x", color=c, markersize=9)
    axs[0].set_xlabel("omega")
    axs[0].set_ylabel("sweeps to 1e-9 (x = not converged in 20000)")
    axs[0].set_title("3 x 3 array, 0.5 mm: relaxation factor", fontsize=9)
    axs[0].legend(fontsize=7)
    axs[0].grid(alpha=0.3)
    st = d["stiffness"]
    xs = [float(k) for k in st]
    for i, (lab, c) in enumerate((("(a) lagged", "#1f77b4"), ("(c) blocks", "#2ca02c"))):
        ys = [st[k][2 * i] if st[k][2 * i] else np.nan for k in st]
        axs[1].loglog(xs, ys, "o-", color=c, label=lab)
        fail = [x for x, k in zip(xs, st) if not st[k][2 * i]]
        axs[1].plot(fail, [2.2e4] * len(fail), "x", color=c, markersize=9)
    axs[1].set_xlabel("s: K = A + s K_via")
    axs[1].set_ylabel("sweeps to 1e-9 (x = diverged or not converged)")
    axs[1].set_title("stiffness of the via part (s = 1 is the real copper-filled via)", fontsize=9)
    axs[1].legend(fontsize=7)
    axs[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_error(path):
    """!
    @brief The lone-via board (10 mm, 0.5 mm cells): the direct temperature of the top layer and the error left by 30000 sweeps of the program's SOR.
    @param path Output file.
    @return None.
    """
    net = bd.net_for(bd.pc.lone_via_board(10.0, 0.3, 385.0), 0.5)
    th, _ = net.solve_steady("direct")
    r = sv.solve_variant(net, "program", max_iter=30000)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.3))
    ext = (0, 10, 0, 10)
    im = axs[0].imshow(th[0], origin="lower", extent=ext, cmap="inferno")
    axs[0].set_title("direct solver, top layer: rise above ambient (K)", fontsize=9)
    fig.colorbar(im, ax=axs[0], shrink=0.8)
    im = axs[1].imshow(r["theta"][0] - th[0], origin="lower", extent=ext, cmap="coolwarm")
    axs[1].set_title("program's SOR (30000 sweeps) minus direct (K)", fontsize=9)
    fig.colorbar(im, ax=axs[1], shrink=0.8)
    for a in axs:
        a.set_xlabel("x (mm)")
        a.set_ylabel("y (mm)")
        a.plot([5], [5], "wo", markersize=3)                                   # the via
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the four data figures.
    @return None.
    """
    bd.pc.load_libraries()
    OUT.mkdir(exist_ok=True)
    fig_matrix(OUT / "fig_04_the_matrix_with_via_couplings.png")
    fig_error(OUT / "fig_07_error_of_the_programs_sor.png")
    if DATA.exists():
        fig_convergence(OUT / "fig_05_convergence_of_the_variants.png")
        fig_sweeps(OUT / "fig_06_omega_and_via_stiffness.png")
    else:
        print("run study_variants.py first for figures 05 and 06")


if __name__ == "__main__":
    main()
