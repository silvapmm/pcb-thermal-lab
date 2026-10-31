#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the investigation, drawn from the tables of data/ written by the study scripts (git-ignored, regenerated) (and, for the profile of figure 07, one run of the references and models).
@details Figures 04 to 08 of figures/ (01 to 03 are the drawings of make_diagrams.py). Run the study scripts first (study_baseline.py, study_causes.py, study_candidate.py, study_rows.py).
         Files: fig_04_error_against_pad_size.png, fig_05_decomposition_of_the_error.png, fig_06_fill_that_reproduces_the_reference.png, fig_07_profile_through_the_centre.png,
         fig_08_candidate_nodes_tiles_and_range.png.
         Usage: .venv/bin/python research/analytic-partial-copper/scripts/make_figures.py   (from the repository root; the profile needs about a minute).
"""

import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402
import numpy as np                                                          # noqa: E402

import _bootstrap as BS                                                     # noqa: E402


def table(name):
    """!
    @brief Read a table of data/.
    @param name File stem in data/.
    @return list of dict rows with numbers converted where possible.
    """
    rows = []
    with open(BS.DATA / f"{name}.csv") as fh:
        for r in csv.DictReader(fh):
            row = {}
            for k, v in r.items():
                try:
                    row[k] = float(v)
                except ValueError:
                    row[k] = v
            rows.append(row)
    return rows


def pct(a, b):
    """!
    @brief Relative difference in percent.
    @param a Value.
    @param b Reference.
    @return 100 (a / b - 1).
    """
    return 100.0 * (a / b - 1.0)


def fig_error_against_pad_size(path):
    """!
    @brief Figure 04: error against the resolved reference of the program's Analytic, the FVM and the candidate (1, 4, 8 nodes) on the three kinds of board, against the pad size.
    @param path Output file.
    @return None.
    """
    rows = [r for r in table("candidate_pads") if r["pad_mm"] > 0]
    kinds = ["1 layer", "2 layers, bare second", "2 layers, full second"]
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
    for ax, kind in zip(axs, kinds):
        rs = [r for r in rows if r["kind"] == kind]
        x = [r["pad_mm"] for r in rs]
        ax.plot(x, [pct(r["analytic_K"], r["ref_K"]) for r in rs], "o-", color="#d62728", label="Analytic (program)")
        ax.plot(x, [pct(r["fvm_K"], r["ref_K"]) for r in rs], "s--", color="#7f7f7f", label="FVM (program)")
        for n, c in ((1, "#9ecae1"), (4, "#3182bd"), (8, "#08306b")):
            ax.plot(x, [pct(r[f"cand{n}_K"], r["ref_K"]) for r in rs], "^-", color=c, label=f"candidate, {n} node(s) in the laminate")
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(kind, fontsize=10)
        ax.set_xlabel("copper pad side (mm)")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("error against the resolved 3D solution (%)")
    axs[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_decomposition(path):
    """!
    @brief Figure 05: the error of the program's Analytic split into the cost of the uniform sheet and the cost of the nodes (structure with exact copper against the reference).
    @param path Output file.
    @return None.
    """
    rows = table("causes")
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
    for ax, (layers, second, title) in zip(axs, ((1, "full", "1 layer"), (2, "empty", "2 layers, bare second"), (2, "full", "2 layers, full second"))):
        rs = [r for r in rows if r["layers"] == layers and r["second"] == second]
        x = np.arange(len(rs))
        ax.bar(x - 0.2, [r["cost_sheet_pct"] for r in rs], 0.4, color="#d62728", label="uniform sheet (Analytic - structure)")
        ax.bar(x + 0.2, [r["cost_nodes_pct"] for r in rs], 0.4, color="#1f77b4", label="nodes (structure - reference)")
        ax.plot(x, [r["analytic_pct"] for r in rs], "k_", markersize=18, label="Analytic total")
        ax.set_xticks(x, [f"{r['pad_mm']:.0f}" for r in rs])
        ax.set_xlabel("copper pad side (mm)")
        ax.set_title(title, fontsize=10)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.grid(alpha=0.3, axis="y")
    axs[0].set_ylabel("share of the error (points of the reference rise)")
    axs[0].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_fill(path):
    """!
    @brief Figure 06: the fill of the top copper that makes the uniform sheet reproduce the reference, against the program's weighted fill and the area of the pad.
    @param path Output file.
    @return None.
    """
    rows = table("causes")
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.0), sharey=True)
    for ax, (layers, second, title) in zip(axs, ((1, "full", "1 layer"), (2, "empty", "2 layers, bare second"), (2, "full", "2 layers, full second"))):
        rs = [r for r in rows if r["layers"] == layers and r["second"] == second]
        x = [r["pad_mm"] for r in rs]
        ax.plot(x, [r["fill_fitted"] for r in rs], "ko-", label="fitted (reproduces the reference)")
        ax.plot(x, [r["fill_weighted"] for r in rs], "s--", color="#d62728", label="program (weighted by K0)")
        ax.plot(x, [r["fill_area"] for r in rs], "^:", color="#7f7f7f", label="area of the pad / area of the board")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("copper pad side (mm)")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("fill of the top copper layer")
    axs[0].legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_profile(path):
    """!
    @brief Figure 07: the temperature of the top face along a line through the centre of the 10 mm pad board (one layer): resolved reference, program's Analytic, FVM and candidate.
    @param path Output file.
    @return None.
    """
    import defect as D
    import modal as M
    import pads as P
    from pcbthermal import SolverOptions, simulate
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=False)
    for ax, pad in zip(axs, (10.0, 20.0)):
        bd = P.Pad(layers=1, pad=pad)
        p = P.problem(bd)
        import resolved3d as r3
        # Reference profile on the quadrant, 0.25 mm cells
        dx_mm, n = 0.25, int(round(bd.size / 2 / 0.25))
        b = p.board
        xs = (np.arange(n) + 0.5) * dx_mm
        inside = xs < pad / 2
        f = (inside[None, :] & inside[:, None]).astype(float)
        kcu = float(b.materials.k_copper)
        slabs = [(float(b.copper_thickness[0]), bd.k_inplane + f * (kcu - bd.k_inplane), bd.k_through + f * (kcu - bd.k_through), 1), (bd.thickness * 1e-3 - float(b.copper_thickness[0]), bd.k_inplane, bd.k_through, 8)]
        res = r3.solve(dx_mm * 1e-3, n, n, slabs, (0, 0, bd.source / 2e3, bd.source / 2e3), bd.power / 4, b.h_top, b.h_bottom)
        ax.plot(xs, res["surf"][0], "k-", linewidth=2, label="resolved 3D (reference)")
        for model, style, label in (("fvm", "--", "FVM"), ("analytic", "-", "Analytic")):
            r = simulate(p, SolverOptions(models=(model,), cell_mm=0.5)).results[model]
            T = r.T[0] - p.board.ambient
            ny = T.shape[0]
            line = T[ny // 2, ny // 2:]
            ax.plot((np.arange(len(line)) + 0.5) * 0.5, line, style, label=f"{label} (program)", color="#d62728" if model == "analytic" else "#7f7f7f")
        c = D.solve(p, n_sub=4, tile_mm=1.0)
        line = c["T"][0][c["T"].shape[1] // 2, c["T"].shape[2] // 2:]
        ax.plot((np.arange(len(line)) + 0.5) * 0.5, line, "-", color="#3182bd", linewidth=1.6, label="candidate (4 laminate nodes)")
        ax.axvline(pad / 2, color="#e0a458", linestyle=":")
        ax.text(pad / 2 + 0.3, ax.get_ylim()[1] * 0.9, "pad edge", fontsize=7, color="#a06a20")
        ax.set_xlim(0, 30)
        ax.set_xlabel("distance from the centre (mm)")
        ax.set_ylabel("rise of the top face (K)")
        ax.set_title(f"{pad:.0f} mm pad, one layer", fontsize=10)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_candidate_range(path):
    """!
    @brief Figure 08: the candidate against the number of nodes and the tile (one-layer pads), and over the out-of-sample cases.
    @param path Output file.
    @return None.
    """
    t2 = table("candidate_tiles_nodes")
    oos = table("candidate_out_of_sample")
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.4), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axs[0]
    ns = (1, 2, 4, 8)
    for r, c in zip(t2, ("#08306b", "#3182bd", "#6baed6", "#c6dbef")):
        ax.plot(ns, [pct(r[f"t1.0_n{n}_K"], r["ref_K"]) for n in ns], "o-", color=c, label=f"pad {r['pad_mm']:.0f} mm, tile 1 mm")
        ax.plot(ns, [pct(r[f"t0.5_n{n}_K"], r["ref_K"]) for n in ns], "x--", color=c, label=f"pad {r['pad_mm']:.0f} mm, tile 0.5 mm")
    ax.axhline(0, color="k", linewidth=0.6)
    ax.set_xscale("log", base=2)
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("nodes in the laminate")
    ax.set_ylabel("error against the resolved 3D solution (%)")
    ax.set_title("Nodes and tile (one layer, 6 mm part)", fontsize=10)
    ax.legend(fontsize=6, ncol=2)
    ax.grid(alpha=0.3)
    ax = axs[1]
    x = np.arange(len(oos))
    ax.bar(x - 0.27, [pct(r["analytic_K"], r["ref_K"]) for r in oos], 0.27, color="#d62728", label="Analytic (program)")
    ax.bar(x, [pct(r["fvm_K"], r["ref_K"]) for r in oos], 0.27, color="#7f7f7f", label="FVM (program)")
    ax.bar(x + 0.27, [pct(r["cand4_K"], r["ref_K"]) for r in oos], 0.27, color="#3182bd", label="candidate, 4 nodes")
    ax.set_xticks(x, [r["case"] for r in oos], rotation=60, ha="right", fontsize=7)
    ax.axhline(0, color="k", linewidth=0.6)
    ax.set_ylabel("error (%)")
    ax.set_title("One-layer 14 mm pad, one parameter changed at a time", fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    BS.FIGURES.mkdir(exist_ok=True)
    fig_error_against_pad_size(BS.FIGURES / "fig_04_error_against_pad_size.png")
    fig_decomposition(BS.FIGURES / "fig_05_decomposition_of_the_error.png")
    fig_fill(BS.FIGURES / "fig_06_fill_that_reproduces_the_reference.png")
    fig_profile(BS.FIGURES / "fig_07_profile_through_the_centre.png")
    fig_candidate_range(BS.FIGURES / "fig_08_candidate_nodes_tiles_and_range.png")
    print("figures written to", BS.FIGURES)
