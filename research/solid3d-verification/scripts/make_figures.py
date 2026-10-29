"""!
@file make_figures.py
@brief Pictures of the 3D solid verification, written to figures/ (committed, linked from the README files).

@details fig_01: dimensionless spreading resistance of a circular source, Yovanovich's Table 3 and the exact series of the circular and square tubes against the 3D solid; fig_02: grid convergence of the source temperature with the
         Richardson extrapolation; fig_03: maximum temperature of every model against the independent 3D finite-element solid for growing copper pads (needs scikit-fem); fig_05: the five models against the
         independent 3D solver (lib/layered3d.py) on one-layer boards, before and after the laminate nodes of the layered models (study_one_layer_board.py); fig_06: what spreading resistance is, from the
         axisymmetric solver (needs out/spreading.json); fig_07: the slabs of a one-layer board in the 3D solid before and after the laminate was added, and the five models on it.
fig_09: the time and the memory of a direct solve against the number of unknowns, measured by study_solve_cost.py (out/solve_cost.json) with the larger sizes reported in the program's documents as separate markers; drawn only by `make_figures.py cost`.
Usage: python research/solid3d-verification/scripts/make_figures.py [--reuse|cost]   (from the repository root; about 4 minutes; --reuse draws figure 5 from
       out/one_layer.json if it exists instead of re-running study_one_layer_board.py)
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
    @brief Yovanovich's Table 3 (isoflux), the exact series of the circular and of the square tube, and the 3D solid for eps = 0.1 to 0.4.
    @return None.
    """
    eps = sorted(e for e in sv.PSI_ISOFLUX if e > 0)
    ref = [sv.PSI_ISOFLUX[e] for e in eps]
    square = [sv.psi_square_series(e) for e in eps]
    mine = [sv.circular_psi(e) for e in eps]
    fine = np.linspace(0.05, 0.45, 41)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    axs[0].plot(fine, [sv.psi_circular_series(e) for e in fine], "k-", lw=1, label="exact series, circular tube")
    axs[0].plot(fine, [sv.psi_square_series(e) for e in fine], "k--", lw=1, label="exact series, square tube of the same area")
    axs[0].plot(eps, ref, "ko", label="Yovanovich (2003), Table 3")
    axs[0].plot(eps, mine, "s", color="#1d4ed8", label="3D solid (square tube), cell 1 mm")
    axs[0].set_xlabel("ε = a / b"); axs[0].set_ylabel("ψ = 4 a k Rs")
    axs[0].legend(fontsize=8); axs[0].set_title("Spreading resistance of an isoflux circular source", fontsize=10)
    x = np.arange(len(eps))
    axs[1].bar(x - 0.2, [100 * (m / r - 1) for m, r in zip(mine, ref)], 0.4, color="#1d4ed8", label="3D solid against the table")
    axs[1].bar(x + 0.2, [100 * (m / q - 1) for m, q in zip(mine, square)], 0.4, color="#93c5fd", label="against the square-tube series")
    axs[1].set_xticks(x); axs[1].set_xticklabels([f"{e:g}" for e in eps])
    axs[1].axhline(0, color="black", lw=0.8)
    axs[1].set_xlabel("ε"); axs[1].set_ylabel("Difference (%)"); axs[1].legend(fontsize=8)
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
    ax.set_title("a circular source on a flux tube, eps = a / b = 0.3\n(colour: log temperature; white: heat flow)", fontsize=9, fontweight="bold", pad=30)    # room for the label of the source above the axes
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
            ax.text(5, -0.35, "bottom face: h through the laminate", fontsize=7, ha="center")   # below the slabs, clear of the arrow
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
    fig.savefig(OUT / "fig_07_one_layer_board.png", dpi=110)
    plt.close(fig)


def fig_one_layer_independent():
    """!
    @brief The five models against the independent 3D solver on one-layer boards, before and after the corrections (part 2 of study_one_layer_board.py).
    @return None.
    """
    import json
    data_dir = HERE.parent / "out"
    path = data_dir / "one_layer.json"
    data_dir.mkdir(exist_ok=True)
    if "--reuse" not in sys.argv or not path.exists():                 # Re-run the study unless asked to reuse its output: a stale file would draw old numbers
        subprocess.run([sys.executable, str(HERE / "study_one_layer_board.py"), "--json", str(path)], check=True)
    rows = json.loads(path.read_text())
    models = ("fvm", "fdm", "lumped", "analytic", "solid3d")
    cols = {"fvm": "#1d4ed8", "fdm": "#9ca3af", "solid3d": "#059669", "lumped": "#d97706", "analytic": "#7c3aed"}
    labels = [("20 mm pad, " if r["pad"] else "full copper, ") + f"{r['thickness_mm']:g} mm" for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(13, 4.8))
    for k, m in enumerate(models):
        off = (k - 2) * 0.16
        ax.bar(x + off, [100 * (r["before"][m] / r["independent"] - 1) for r in rows], 0.15, color="none", ec=cols[m], ls="--")
        ax.bar(x + off, [100 * (r["after"][m] / r["independent"] - 1) for r in rows], 0.15, color=cols[m], alpha=0.85, label=f"{m} (now; dashed: before)")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("maximum rise against the independent 3D solver (%)")
    ax.set_title("One-layer boards: the laminate nodes bring the FVM and FDM to the 3D answer with full copper; a bare pad stays hard for Lumped and Analytic", fontsize=9)
    ax.legend(fontsize=7, ncol=3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_one_layer_against_independent.png", dpi=110)
    plt.close(fig)


# Sizes that the program's documents report (NOT reproduced on the quiet machine, cause not established: memory pressure or the computed-h loop; study_solve_cost.py now measures the same sizes) (CHANGELOG.md "A 3D-solid run that never ended", docs/versions.md, docs/versions.md "Planned"):
# 3D solid: (unknowns, seconds, GB); layered models: (unknowns, seconds, GB). The 400 000 unknowns point of docs/versions.md is 276 s and "5 GB".
REPORTED_3D = [(160_000, 49.0, 2.2), (254_000, 130.0, 4.4), (400_000, 276.0, 5.0), (512_000, 320.0, 8.0)]
REPORTED_LAYERED = [(1_000_000, 97.0, 4.4), (2_000_000, 273.0, 8.4)]


def fig_cost():
    """!
    @brief Time and peak memory of a direct steady solve against the number of unknowns: measured here (out/solve_cost.json, study_solve_cost.py) and reported in the program's documents; the limit of the 3D solid (250 000 unknowns) is marked.
    @return None.
    """
    import json
    data = json.loads((HERE.parent / "out" / "solve_cost.json").read_text())
    rows = data["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.6))
    styles = (("solid3d", "#059669", "o", "3D solid, plain two-layer board (measured here, quiet machine)"), ("example", "#d97706", "s", "3D solid, example board with vias and a heatsink (measured here, quiet machine)"),
              ("fvm", "#1d4ed8", "^", "layered FVM, plain board (measured here, quiet machine)"))
    for k, (ax, key, unit) in enumerate(((axs[0], "seconds", "time of the assembly and the direct solve (s)"), (axs[1], "peak_gb", "peak resident memory (GB)"))):
        for kind, col, mk, lab in styles:
            pts = sorted((r["unknowns"], r[key]) for r in rows if r["model"] == kind)
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker=mk, color=col, label=lab)
        idx = 1 if key == "seconds" else 2
        ax.plot([p[0] for p in REPORTED_3D], [p[idx] for p in REPORTED_3D], "x", color="#dc2626", ms=9, mew=2, label="3D solid, in the program's documents (not reproduced)")
        ax.plot([p[0] for p in REPORTED_LAYERED], [p[idx] for p in REPORTED_LAYERED], "+", color="#6d28d9", ms=11, mew=2, label="layered models, in docs/roadmap.md (not reproduced)")
        ax.axvline(250_000, color="k", ls="--", lw=1)
        ax.text(255_000, ax.get_ylim()[0] * 1.5 if ax.get_yscale() == "log" else 0, "limit of the 3D solid\n250 000 unknowns", fontsize=7, va="bottom")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("unknowns")
        ax.set_ylabel(unit)
        ax.grid(alpha=0.3, which="both")
    axs[0].legend(fontsize=6.5, loc="lower right")
    axs[0].set_title("Time of a direct solve against the size", fontsize=9)
    axs[1].set_title(f"Peak memory ({data['info']['machine']}, SciPy {data['info']['scipy']})", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_09_solve_cost.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the data figures (1 to 3 and 5 to 7; the diagrams 4 and 8 are drawn by make_diagrams.py; `cost` draws only figure 9).
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    if "cost" in sys.argv[1:]:
        fig_cost()
        print("figure in", OUT)
        return
    fig_psi()
    fig_gci()
    fig_pads()
    fig_spreading()
    fig_one_layer()
    fig_one_layer_independent()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
