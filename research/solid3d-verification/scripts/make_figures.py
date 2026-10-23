"""!
@file make_figures.py
@brief Pictures of the 3D solid verification, written to figures/ (committed, linked from the README files).

@details fig_01: dimensionless spreading resistance of a circular source, Yovanovich's Table 3 against the 3D solid; fig_02: grid convergence of the source temperature with the
         Richardson extrapolation; fig_03: maximum temperature of every model against the independent 3D finite-element solid for growing copper pads. Needs scikit-fem for fig_03.
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


def fig_spreading():
    """!
    @brief What spreading resistance is: the temperature and the heat flow of a circular source on a flux tube (axisymmetric solver, eps = 0.3), the dimensionless resistance against eps from that solver with Yovanovich's table and the program's 3D solid, and how the axisymmetric solver converges with the grid.
    @return None.
    """
    import json
    out = HERE.parent / "out"
    res = json.loads((out / "spreading.json").read_text())
    T = np.load(out / "spreading_field.npz")["T"].astype(float)
    nz, nr = T.shape
    fig = plt.figure(figsize=(16, 6.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1, 0.9], wspace=0.3)
    ax = fig.add_subplot(gs[0, 0])
    step = 6
    Tm = np.concatenate([T[:, ::-1], T], axis=1)               # mirrored: the whole section of the tube
    ext = (-1, 1, -2, 0)
    im = ax.imshow(np.log10(np.maximum(Tm, 1e-3)), extent=ext, aspect="equal", cmap="inferno", vmin=-0.3, vmax=np.log10(Tm.max()))
    r = (np.arange(nr) + 0.5) / nr
    z = -(np.arange(nz) + 0.5) / nr
    dTdz, dTdr = np.gradient(T, -1.0 / nr, 1.0 / nr)
    qz, qr = -dTdz, -dTdr                                        # heat flux (k = 1): towards falling temperature, z points up
    rr = np.concatenate([-r[::-1], r])
    qrm = np.concatenate([-qr[:, ::-1], qr], axis=1)
    qzm = np.concatenate([qz[:, ::-1], qz], axis=1)
    ax.streamplot(rr, z[::-1], qrm[::-1], qzm[::-1], color="white", density=1.1, linewidth=0.6, arrowsize=0.7)
    ax.plot([-0.3, 0.3], [0, 0], color="#2ca02c", linewidth=5, solid_capstyle="butt")
    ax.text(0, 0.06, "source, radius a (heat Q)", ha="center", fontsize=8, color="#2ca02c")
    ax.annotate("", (0.3, -0.12), (0.0, -0.12), arrowprops={"arrowstyle": "<->", "color": "w"})
    ax.text(0.15, -0.2, "a", color="w", ha="center", fontsize=9)
    ax.annotate("", (1.0, -0.35), (0.0, -0.35), arrowprops={"arrowstyle": "<->", "color": "w"})
    ax.text(0.5, -0.45, "b", color="w", ha="center", fontsize=9)
    ax.text(0, -2.12, "cooled face (T = 0); the sides are insulated", ha="center", fontsize=8)
    ax.set_title("a circular source on a flux tube, eps = a / b = 0.3\n(colour: log temperature; white: heat flow)", fontsize=9, fontweight="bold", pad=18)
    ax.set_xticks([])
    ax.set_yticks([])
    ax = fig.add_subplot(gs[0, 1])
    eps = [r_["eps"] for r_ in res["rows"]]
    ax.plot(eps, [r_["psi"] for r_ in res["rows"]], "-", color="#1f77b4", label="axisymmetric finite volumes (400 cells per radius)")
    ax.plot([0.1, 0.2, 0.3, 0.4], [0.9401, 0.8009, 0.6649, 0.5337], "ks", markersize=7, label="Yovanovich (2003), Table 3")
    ax.plot([0.2, 0.3], [0.8076, 0.6698], "^", color="#d62728", markersize=8, label="the program's 3D solid (square tube)")
    ax.set_xlabel("eps = a / b")
    ax.set_ylabel("psi = 4 a k Rs (dimensionless spreading resistance)")
    ax.set_title("the farther the heat has to spread (small source), the larger psi", fontsize=9)
    ax.legend(fontsize=7.5)
    ax.grid(alpha=0.3)
    ax = fig.add_subplot(gs[0, 2])
    nrs = [s_["cells_per_radius"] for s_ in res["sweep_eps02"]]
    errs = [abs(s_["psi"] / 0.8009 - 1) * 100 for s_ in res["sweep_eps02"]]
    ax.loglog(nrs, errs, "o-", color="#1f77b4", label="axisymmetric solver, eps = 0.2")
    ax.loglog(nrs, [errs[0] * nrs[0] / n for n in nrs], "--", color="grey", label="order one")
    ax.set_xlabel("cells per radius")
    ax.set_ylabel("error against the table (%)")
    ax.set_title(f"error halves with each halving of the cell;\nextrapolated {res['extrapolated_eps02']:.4f} against 0.8009", fontsize=9)
    ax.legend(fontsize=7.5)
    ax.grid(alpha=0.3, which="both")
    fig.suptitle("Spreading resistance: heat leaving a small source into a large body, from a third solver (README 4.3)", fontsize=10)
    fig.subplots_adjust(top=0.84, bottom=0.12, left=0.04, right=0.98)
    fig.savefig(OUT / "fig_06_spreading_resistance_explained.png", dpi=105)
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
    fig_spreading()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
