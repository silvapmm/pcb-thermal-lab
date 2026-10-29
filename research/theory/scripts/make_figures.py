"""!
@file make_figures.py
@brief Data figures of the theory folder: three closed forms of `docs/theory.md` drawn from numbers computed here (closed form or program), none typed in.
@details fig_31: efficiency tanh(mL)/(mL) of a plate fin and the fin ratio of the program (`pcbthermal.blocks.fin_ratio`) against the fin height, for three metals;
         fig_32: convergence of the Analytic cosine series with the number of modes against the FVM on the example board, and the effect of the edge loss
                 (`h_side` of the board against insulated edges) on the four uniform scenarios of `docs/validation.md` section 2 (the study of topic 37);
         fig_33: the through-thickness correction q'' t / (2 k) of a layer against its thickness, for copper, FR-4, steel and aluminium, with the 5 % limit of the
                 thick-plate check (`pcbthermal.checks.thick_plate_bound`, `THICK_PLATE_LIMIT`) on the rise of the example board.
         Every printed table is the source of the numbers in the README.
         Usage: .venv/bin/python research/theory/scripts/make_figures.py   (from the repository root; about 3 minutes)
"""

import copy
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np               # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "models-comparison" / "scripts"))

from pcbthermal import analytic, blocks, checks, fvm, model  # noqa: E402
from pcbthermal.examples import example_board                 # noqa: E402
import accuracy_study                                          # noqa: E402

## Output folder (committed on purpose; the README links to the files).
OUT = HERE.parent / "figures"
## Colours of the metals and of the FR-4, shared by the three figures.
COLORS = {"aluminium": "#1d4ed8", "copper": "#c97a2b", "steel": "#6b7280", "FR-4": "#059669"}


def metal_k(name):
    """!
    @brief Conductivity of a metal of the program's library.
    @param name Start of the library name, for example "Aluminium".
    @return float Conductivity in W/mK.
    @throws KeyError If no metal of the library starts with the name.
    """
    for entry in model.METALS:
        if entry[0].lower().startswith(name.lower()):
            return float(entry[1])
    raise KeyError(name)


def fin_block(k, height_mm, thickness_mm=1.0, pitch_mm=5.0):
    """!
    @brief A Heatsink (block) with plate fins, through the program's builder, to feed `blocks.fin_ratio`.
    @param k Conductivity of the metal in W/mK.
    @param height_mm Fin height in mm.
    @param thickness_mm Fin thickness in mm.
    @param pitch_mm Fin pitch in mm.
    @return The Heatsink.
    """
    p = model.Problem.new(width_mm=50, height_mm=50, layers=2)
    p.add_heatsink(1, 0.0, rect=(10, 10, 40, 40), thickness_mm=3.0, k=k, fin_height_mm=height_mm,
                   fin_thickness_mm=thickness_mm, fin_pitch_mm=pitch_mm)
    return p.heatsinks[0]


def fig_fins():
    """!
    @brief Efficiency of a plate fin against mL (closed form) and the fin ratio of the program against the fin height.
    @return None.
    """
    h = 10.0                      # W/m2K, a natural-convection value; the same for every curve
    t_mm, p_mm = 1.0, 5.0         # Fin thickness and pitch of the block of the example in docs/models.md
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    # Left: the closed form, a single curve for any fin
    ml = np.logspace(-2, 1.2, 200)
    axs[0].plot(ml, np.tanh(ml) / ml, color="k", lw=2)
    axs[0].set_xscale("log")
    axs[0].set_xlabel("m L, with m = sqrt(2 h / (k t))  (dimensionless)")
    axs[0].set_ylabel("Fin efficiency tanh(mL) / (mL)")
    axs[0].set_ylim(0, 1.05)
    axs[0].set_title("Adiabatic-tip plate fin: one curve for any metal", fontsize=9)
    axs[0].axhline(0.5, color="#d1d5db", lw=0.8)
    print("| Metal | Fin height (mm) | mL | efficiency | fin ratio (program) |\n| :-- | --: | --: | --: | --: |")
    markers = {}
    # Right: the program's ratio of the finned face to the plain plate, fins 1 mm thick at 5 mm pitch
    heights = np.linspace(0.0, 60.0, 61)
    for name, key in (("aluminium", "Aluminium"), ("copper", "Copper"), ("steel", "Carbon")):
        k = metal_k(key)
        ratios = []
        for hh in heights:
            if hh == 0.0:
                ratios.append(1.0)
            else:
                ratios.append(blocks.fin_ratio(h, fin_block(k, hh, t_mm, p_mm)))
        axs[1].plot(heights, ratios, color=COLORS[name], lw=2, label=f"{name} (k = {k:.0f} W/mK)")
        for hh in (10.0, 30.0, 60.0):
            s = fin_block(k, hh, t_mm, p_mm)
            hc = (hh + 0.5 * t_mm) / 1000.0
            m = np.sqrt(2.0 * h / (k * t_mm / 1000.0))
            eta = np.tanh(m * hc) / (m * hc)
            r = blocks.fin_ratio(h, s)
            print(f"| {name} | {hh:.0f} | {m * hc:.3f} | {eta:.3f} | {r:.3f} |")
            markers.setdefault(name, []).append((m * hc, eta))
        axs[0].plot([x for x, _ in markers[name]], [y for _, y in markers[name]], "o", color=COLORS[name], ms=7)
    # The limit of the fins that were perfect conductors: 1 - t/p + 2 Hc / p
    perfect = [(1 - t_mm / p_mm) + 2 * (hh + 0.5 * t_mm) / p_mm for hh in heights]
    axs[1].plot(heights, perfect, "k--", lw=1, label="fins of infinite conductivity (efficiency 1)")
    axs[1].set_xlabel("Fin height H (mm)   [fins 1 mm thick, 5 mm pitch, h = 10 W/m2K]")
    axs[1].set_ylabel("Fin ratio (heat of the finned face / plain plate)")
    axs[1].set_title("Fin ratio of the program (blocks.fin_ratio); dots on the left: H = 10, 30, 60 mm", fontsize=9)
    axs[1].legend(fontsize=8, loc="upper left")
    axs[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_31_fin_efficiency_and_ratio.png", dpi=110)
    plt.close(fig)


def fig_series_edges():
    """!
    @brief Convergence of the Analytic series with the number of modes against the FVM, and the edge-loss effect on the uniform scenarios.
    @return None.
    """
    p = example_board()
    amb = p.board.ambient
    ref = fvm.solve_steady(p, 0.5).t_max - amb                # FVM rise of the hottest point at 0.5 mm cells
    modes = [10, 20, 30, 50, 75, 100, 150, 200, 300]
    print(f"\nExample board, FVM 0.5 mm: rise {ref:.3f} K\n| Modes | Analytic rise (K) | against FVM (%) |\n| --: | --: | --: |")
    rises = []
    for n in modes:
        r = analytic.solve_steady(p, 0.5, n_terms=n).t_max - amb
        rises.append(r)
        print(f"| {n} | {r:.3f} | {100 * (r / ref - 1):+.2f} |")
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), gridspec_kw={"width_ratios": [1, 1.15]})
    axs[0].plot(modes, [100 * (r / ref - 1) for r in rises], "o-", color="#1d4ed8", lw=2)
    axs[0].axhline(0, color="k", lw=0.8)
    axs[0].set_xscale("log")
    axs[0].set_xlabel("Cosine modes per direction (n_terms)")
    axs[0].set_ylabel("Analytic rise against FVM 0.5 mm (%)")
    axs[0].set_title("Example board, hottest point: the Analytic rise against the FVM, by number of modes", fontsize=8.5)
    axs[0].grid(alpha=0.3)
    # Right: the four uniform scenarios, with h_side of the board and with insulated edges, on the FVM at 0.25 mm
    keep = ("reference board (centred", "example, uniform", "example, only U1, uniform", "reference board, 8 layers")
    cases = [(n, q) for n, q in accuracy_study.cases() if n.startswith(keep)]
    print("\n| Scenario | Edges | Analytic (K) | FVM 0.25 mm (K) | Analytic against FVM (%) |\n| :-- | :-- | --: | --: | --: |")
    labels, with_edge, insulated = [], [], []
    for name, q0 in cases:
        gaps = []
        for edge in ("h_side", "insulated"):
            q = copy.deepcopy(q0)
            if edge == "insulated":
                q.board.h_side = None                       # The boundary condition of the cosine series
            a = analytic.solve_steady(q).t_max - q.board.ambient
            f = fvm.solve_steady(q, 0.25).t_max - q.board.ambient
            gaps.append(100 * (a / f - 1))
            print(f"| {name} | {edge} | {a:.3f} | {f:.3f} | {gaps[-1]:+.2f} |")
        # The parenthesis (what the board is) is in the README; short labels do not run into each other
        labels.append(re.sub(r"\s*\(.*\)", "", name).replace(", ", ",\n", 1))
        with_edge.append(gaps[0]); insulated.append(gaps[1])
    x = np.arange(len(labels))
    axs[1].bar(x - 0.2, with_edge, 0.4, color="#c97a2b", label="board's h_side in the FVM (series has insulated edges)")
    axs[1].bar(x + 0.2, insulated, 0.4, color="#059669", label="insulated edges in both")
    for k in range(len(labels)):
        axs[1].text(k - 0.2, with_edge[k] + (0.03 if with_edge[k] >= 0 else -0.07), f"{with_edge[k]:+.2f}", ha="center", fontsize=7)
        axs[1].text(k + 0.2, insulated[k] + (0.03 if insulated[k] >= 0 else -0.07), f"{insulated[k]:+.2f}", ha="center", fontsize=7)
    axs[1].axhline(0, color="k", lw=0.8)
    axs[1].set_xticks(x); axs[1].set_xticklabels(labels, fontsize=7)
    top = max(with_edge + insulated)
    axs[1].set_ylim(min(with_edge + insulated) - 0.2, top + 0.45)
    axs[1].set_ylabel("Analytic against FVM 0.25 mm (%)")
    axs[1].set_title("Uniform boards: the gap is the edge loss, not the mesh", fontsize=9)
    axs[1].legend(fontsize=7.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig_32_analytic_modes_and_edges.png", dpi=110)
    plt.close(fig)


def fig_thick_plate():
    """!
    @brief The through-thickness correction q'' t / (2 k) of a plate against its thickness, with the 5 % limit of the rise of the example board.
    @return None.
    """
    p = example_board()
    u1 = p.heaters[0]
    x, y = u1.polygon[:, 0], u1.polygon[:, 1]
    area = float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2.0)     # Shoelace area of the footprint in m2
    flux = u1.power / area                                                                     # W/m2 through the footprint
    rise = fvm.solve_steady(p, 0.5).t_max - p.board.ambient                                    # Rise of the hottest point in K
    limit = checks.THICK_PLATE_LIMIT * rise
    mats = {"copper": p.board.materials.k_copper, "aluminium": metal_k("Aluminium"), "steel": metal_k("Carbon"),
            "FR-4": p.board.materials.k_fr4_through}
    t_mm = np.logspace(-2, 1.4, 200)                                   # 0.01 mm to 25 mm
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    print(f"\nU1: {u1.power:.1f} W over {area * 1e6:.0f} mm2, q'' = {flux:.0f} W/m2; rise of the example board {rise:.2f} K; 5 % limit {limit:.2f} K")
    print("| Material | k (W/mK) | thickness at the limit (mm) |\n| :-- | --: | --: |")
    for name, k in mats.items():
        drop = [checks.thick_plate_bound(u1.power, area, t / 1000.0, k) for t in t_mm]
        ax.plot(t_mm, drop, color=COLORS[name], lw=2, label=f"{name} (k = {k:.3g} W/mK)")
        t_lim = 2.0 * k * limit / flux * 1000.0                         # Invert q'' t / (2 k) = limit
        print(f"| {name} | {k:.3g} | {t_lim:.3g} |")
        if t_mm[0] <= t_lim <= t_mm[-1]:
            ax.plot([t_lim], [limit], "o", color=COLORS[name], ms=7)
    ax.axhline(limit, color="#d62728", ls="--", lw=1.2)
    # Placed where no curve crosses it: FR-4 is already above the limit and the steel line is still below it
    ax.text(0.09, limit * 1.12, f"5 % of the rise ({rise:.1f} K) = {limit:.2f} K: the thick-plate warning", color="#d62728", fontsize=8)
    # The program's own plate thicknesses
    cu = p.board.copper_thickness[0] * 1000.0
    ax.axvline(cu, color=COLORS["copper"], lw=0.8, ls=":")
    ax.text(cu * 1.05, 1.5e-4, f"copper layer\n{cu * 1000:.0f} um", fontsize=7.5, color=COLORS["copper"])
    ax.axvline(p.board.thickness * 1000.0, color=COLORS["FR-4"], lw=0.8, ls=":")
    ax.text(p.board.thickness * 1000.0 * 1.05, 1.5e-4, f"board\n{p.board.thickness * 1000:.1f} mm", fontsize=7.5, color=COLORS["FR-4"])
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_ylim(1e-4, 1e2)
    ax.set_xlabel("Thickness of the plate t (mm)")
    ax.set_ylabel("Surface hotter than the mean by up to q'' t / (2 k)  (K)")
    ax.set_title(f"Heat flux of U1 of the example board: q'' = {flux / 1000:.0f} kW/m2 ({u1.power:.0f} W over {area * 1e6:.0f} mm2)", fontsize=9)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "fig_33_thick_plate_correction.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Draw the three data figures of the folder.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_fins()
    fig_series_edges()
    fig_thick_plate()


if __name__ == "__main__":
    main()
