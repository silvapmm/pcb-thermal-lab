"""!
@file make_figures.py
@brief Pictures of the 3D solid verification, written to figures/ (committed, linked from the README files).

@details fig_01: dimensionless spreading resistance of a circular source, Yovanovich's Table 3 against the 3D solid; fig_02: grid convergence of the source temperature with the
         Richardson extrapolation; fig_03: maximum temperature of every model against the independent 3D finite-element solid for growing copper pads. Needs scikit-fem for fig_03.
Usage: python research/solid3d-verification/make_figures.py   (from the repository root; about 2 minutes)
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
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, str(HERE))
import solid3d_verification as sv                                                # noqa: E402

OUT = HERE / "figures"          # kept in the repository on purpose: the README files link to them


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


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_psi()
    fig_gci()
    fig_pads()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
