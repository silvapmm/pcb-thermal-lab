"""!
@file make_figures.py
@brief Pictures of the 3D solid verification, written to figures/ (committed, linked from the README files).

@details fig_01: dimensionless spreading resistance of a circular source, Yovanovich's Table 3 against the 3D solid; fig_02: grid convergence of the source temperature with the
         Richardson extrapolation; fig_03: maximum temperature of every model against the independent 3D finite-element solid for growing copper pads (needs scikit-fem); fig_04: the
         slabs of a one-layer board in the 3D solid before and after the laminate was added, and the five models on it.
Usage: python research/solid3d-verification/scripts/make_figures.py   (from the repository root; about 2 minutes)
"""

import os
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, str(HERE))
import solid3d_verification as sv                                                # noqa: E402
import study_one_layer_board as ol                                               # noqa: E402

OUT = HERE.parent / "figures"          # kept in the repository on purpose: the README files link to them


def fig_psi():
    """!
    @brief Yovanovich's Table 3 (isoflux) against the 3D solid for eps = 0.1 to 0.4.
    @return None.
    """
    eps = sorted(e for e in sv.PSI_ISOFLUX if e > 0)
    ref = [sv.PSI_ISOFLUX[e] for e in eps]
    mine = [sv.circular_psi(e) for e in eps]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].plot(eps, ref, "k-o", label="Yovanovich (2003), Table 3")
    axs[0].plot(eps, mine, "s", color="#1d4ed8", label="3D solid, cell 1 mm")
    axs[0].set_xlabel("ε = a / b"); axs[0].set_ylabel("ψ = 4 a k Rs")
    axs[0].legend(fontsize=8); axs[0].set_title("Spreading resistance of an isoflux circular source", fontsize=10)
    axs[1].bar([f"{e:g}" for e in eps], [100 * (m / r - 1) for m, r in zip(mine, ref)], color="#1d4ed8")
    axs[1].axhline(0, color="black", lw=0.8)
    axs[1].set_xlabel("ε"); axs[1].set_ylabel("Difference (%)")
    axs[1].set_title("Difference (largest at ε = 0.1: three cells across)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_spreading_resistance_vs_yovanovich.png", dpi=110)
    plt.close(fig)


def fig_gci():
    """!
    @brief Grid convergence of the mean source temperature per watt with the extrapolated value.
    @return None.
    """
    g = sv.grid_convergence()
    cells = np.array([4.0, 2.0, 1.0])
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(cells, g["values"], "o-", color="#1d4ed8", label="3D solid")
    ax.axhline(g["extrapolated"], color="k", ls="--", label=f"Richardson extrapolation {g['extrapolated']:.2f} K/W")
    ax.set_xscale("log", base=2); ax.invert_xaxis()
    ax.set_xticks(cells); ax.set_xticklabels(["4", "2", "1"])
    ax.set_xlabel("Cell size (mm)"); ax.set_ylabel("Mean source temperature per watt (K/W)")
    ax.set_title(f"Observed order {g['order']:.2f}, GCI of the fine mesh {100 * g['gci']:.2f} %", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_grid_convergence.png", dpi=110)
    plt.close(fig)


def fig_pads():
    """!
    @brief Tmax of every model against the 3D finite-element solid for growing copper pads (runs copper_dissipation.py --fem).
    @return None.
    """
    out = subprocess.run([sys.executable, str(HERE / "copper_dissipation.py"), "--fem"], capture_output=True, text=True, check=True).stdout.splitlines()
    i = next(k for k, ln in enumerate(out) if ln.startswith("| Top pad"))
    head = [c.strip() for c in out[i].strip("|").split("|")]
    rows = []
    for ln in out[i + 2:]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip("|").split("|")])
    sizes = [10, 20, 30, 40, 60, 80]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.4))
    colours = {"FVM": "#1f2937", "FDM": "#6b7280", "3D solid (FV)": "#059669", "Lumped": "#d97706", "Analytic": "#1d4ed8", "3D FEM": "#dc2626"}
    fem = np.array([float(r[head.index("3D FEM")]) for r in rows])
    for name, col in colours.items():
        v = np.array([float(r[head.index(name)]) for r in rows])
        axs[0].plot(sizes, v, "o-" if name == "3D FEM" else ".-", color=col, label=name, lw=2.4 if name == "3D FEM" else 1.2)
        if name != "3D FEM":
            axs[1].plot(sizes, (v - 25) / (fem - 25) * 100 - 100, ".-", color=col, label=name)
    axs[0].set_xlabel("Top copper pad (mm square)"); axs[0].set_ylabel("Tmax (°C)"); axs[0].set_title("Maximum temperature against the pad size", fontsize=10)
    axs[0].legend(fontsize=8)
    axs[1].axhline(0, color="black", lw=0.8)
    axs[1].set_ylim(-70, 110)
    axs[1].set_xlabel("Top copper pad (mm square)"); axs[1].set_ylabel("Error of the rise against the 3D FEM (%)")
    axs[1].set_title("The layered models fail on a one-sided pad (Lumped, Analytic)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_copper_pad_models_vs_fem.png", dpi=110)
    plt.close(fig)


def fig_one_layer():
    """!
    @brief The cross-section of a one-layer board as the 3D solid saw it (copper only) and sees it now (copper on four slabs of laminate), and the models on it.
    @return None.
    """
    from pcbthermal import SolverOptions, simulate
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.4), gridspec_kw={"width_ratios": [1, 1, 1.6]})
    for ax, title, lam in ((axs[0], "before: the copper only", False), (axs[1], "now: copper on the laminate (4 slabs)", True)):
        ax.set_xlim(0, 10)
        ax.set_ylim(-0.6, 3.2)
        ax.axis("off")
        ax.add_patch(plt.Rectangle((3.5, 2.55), 3.0, 0.25, fc="#dc2626", ec="k"))
        ax.text(5, 2.95, "part, 1 W", ha="center", fontsize=8)
        ax.add_patch(plt.Rectangle((1, 2.35), 8, 0.2, fc="#d97706", ec="k"))
        ax.text(9.2, 2.45, "copper 35 um", fontsize=7, va="center")
        if lam:
            for k in range(4):
                ax.add_patch(plt.Rectangle((1, 2.35 - 0.55 * (k + 1)), 8, 0.55, fc="#bbf7d0", ec="#15803d"))
            ax.text(9.2, 1.25, "FR-4 1.565 mm\n(4 slabs)", fontsize=7, va="center")
            ax.annotate("", xy=(5, 0.05), xytext=(5, 2.3), arrowprops=dict(arrowstyle="->", color="#dc2626"))
            ax.annotate("", xy=(1.2, 1.6), xytext=(4, 2.0), arrowprops=dict(arrowstyle="->", color="#dc2626"))
            ax.text(5.2, 0.15, "bottom face: h through the laminate", fontsize=7)
        else:
            ax.annotate("", xy=(1.2, 2.45), xytext=(4, 2.45), arrowprops=dict(arrowstyle="->", color="#dc2626"))
            ax.text(5, 1.9, "bottom face: h on the copper\nno laminate to spread the heat", fontsize=7, ha="center")
        ax.set_title(title, fontsize=9)
    models = ("fvm", "fdm", "solid3d", "lumped", "analytic")
    cols = {"fvm": "#1d4ed8", "fdm": "#9ca3af", "solid3d": "#059669", "lumped": "#d97706", "analytic": "#7c3aed"}
    x = np.arange(2)
    for k, m in enumerate(models):
        vals = [simulate(ol.board(pad), SolverOptions(models=(m,), cell_mm=1.0)).results[m].t_max for pad in (False, True)]
        axs[2].bar(x + (k - 2.5) * 0.13, vals, 0.13, color=cols[m], label=m)
    old = [simulate(ol.board(pad, thickness_mm=0.036), SolverOptions(models=("solid3d",), cell_mm=1.0)).results["solid3d"].t_max for pad in (False, True)]
    axs[2].bar(x + 2.5 * 0.13, old, 0.13, color="#fecaca", ec="#dc2626", label="3D solid before")
    axs[2].set_xticks(x)
    axs[2].set_xticklabels(["full copper", "20 mm pad"])
    axs[2].set_ylabel("maximum temperature (C)")
    axs[2].set_title("60 x 60 x 1.6 mm, one layer, 1 W on 6 x 6 mm", fontsize=9)
    axs[2].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_one_layer_board.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the four figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_psi()
    fig_gci()
    fig_pads()
    fig_one_layer()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
