#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the memory guard, drawn from out/ladder.jsonl and out/fit.json (run study_memory_ladder.py --run, study_class_fit.py and study_sor_block.py first): peak memory against unknowns with the fitted law and the limits of three machines, and the time against the unknowns with the cell-major series.
@details Files: fig_04_memory_against_unknowns.png (three panels, the class laws of out/class_fit.json), fig_05_time_and_cell_major.png, fig_06_bytes_per_unknown_against_t.png, fig_07_sor_block_memory.png (the numbers 01 to 03 belong to make_diagrams.py).
         Usage: python research/memory-guard/scripts/make_figures.py   (from the repository root).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import matplotlib                                          # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                            # noqa: E402
import numpy as np                                         # noqa: E402

import memory_model as mm                                  # noqa: E402

OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"


def main():
    """!
    @brief Draw the four data figures.
    @return None.
    """
    recs = [json.loads(line) for line in (OUT / "ladder.jsonl").read_text().splitlines() if line.strip()]
    cls = json.loads((OUT / "class_fit.json").read_text())
    ok = [r for r in recs if r["status"] == "ok" and r["spec"].get("mode", "solve") == "solve" and r["spec"]["series"] != "baseline"]
    killed = [r for r in recs if r["status"] == "killed_memory"]
    FIG.mkdir(exist_ok=True)

    # Figure 4: peak memory against the unknowns, one panel per model, the points coloured by series, the class laws dashed, the 70 % limits
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.0), sharey=True)
    n = np.geomspace(2e4, 3e6, 100)
    for ax, model, prefix in zip(axs, ("fvm", "fdm", "solid3d"), ("fvm", "fdm", "solid3d")):
        for series in sorted({r["spec"]["series"] for r in ok if r["spec"]["model"] == model and r["spec"]["order"] == "layer"}):
            pts = sorted((r["unknowns"], r["peak_bytes"] / 1e9) for r in ok if r["spec"]["series"] == series)
            ax.plot(*zip(*pts), "o-", ms=3, lw=0.8, label=series)
        for r in killed:
            if r["spec"]["model"] == model and r["spec"]["order"] == "layer":
                ax.plot(r.get("unknowns", np.nan), r["peak_bytes"] / 1e9, "kx", ms=7)
        for key, v in cls.items():
            if key.startswith(prefix + "_") and isinstance(v, dict) and "k" in v:
                ax.plot(n, [(v["base"] + v["k"] * x * (x / 5e5) ** (v["p"] - 1)) * v["safety"] / 1e9 for x in n], "--", lw=0.7, color="0.3")
        for ram in (8, 16, 64):
            ax.axhline(0.7 * ram, color="r", lw=0.8, ls=":")
            ax.text(2.2e4, 0.7 * ram * 1.05, f"70 % of {ram} GB", color="r", fontsize=7)
        ax.set_xscale("log"), ax.set_yscale("log"), ax.set_xlabel("unknowns"), ax.set_title(model, fontsize=9)
        ax.set_ylim(0.05, 60)
        ax.legend(fontsize=6)
    axs[0].set_ylabel("peak resident memory (GB)")
    fig.suptitle("Peak memory against the unknowns (points: measured; dashed: class law times its safety factor; x: stopped at the cutoff, the true peak is above)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_memory_against_unknowns.png", dpi=105)
    plt.close(fig)

    # Figure 5: time and memory, layer-major against cell-major
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    for series in sorted({r["spec"]["series"] for r in ok if r["spec"]["model"] == "fvm"}):
        pts = sorted((r["unknowns"], r.get("t_solve", np.nan), r["peak_bytes"] / 1e9) for r in ok if r["spec"]["series"] == series)
        style = "--" if series.endswith("cellmajor") else "-"
        axs[0].plot([p[0] for p in pts], [p[1] for p in pts], style, marker="o", ms=3, lw=0.8, label=series)
        axs[1].plot([p[0] for p in pts], [p[2] for p in pts], style, marker="o", ms=3, lw=0.8)
    for ax in axs:
        ax.set_xscale("log"), ax.set_yscale("log"), ax.set_xlabel("unknowns")
    axs[0].set_ylabel("solve time (s)"), axs[1].set_ylabel("peak memory (GB)")
    axs[0].legend(fontsize=5, ncol=2)
    fig.suptitle("FVM solve time and peak memory, layer-major (solid) and cell-major (dashed) numbering", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_time_and_cell_major.png", dpi=105)
    plt.close(fig)

    # Figure 6: bytes per unknown against the nodes per column t (why the classes are by t and not by the layer count)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for model, mk in (("fvm", "o"), ("fdm", "s"), ("solid3d", "^")):
        pts = [r for r in ok if r["spec"]["model"] == model and r["spec"]["order"] == "layer" and 3e5 <= r["unknowns"] <= 7e5]
        ax.plot([r["unknowns"] / r["cells"] for r in pts], [r["peak_bytes"] / r["unknowns"] / 1e3 for r in pts], mk, label=f"{model}, 300 000 to 700 000 unknowns")
    ax.set_xlabel("nodes per plan cell t = unknowns / cells"), ax.set_ylabel("peak bytes per unknown (KB)")
    ax.set_xscale("log"), ax.legend(fontsize=7)
    ax.set_title("The memory per unknown follows the thickness of the graph, not the model alone", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_bytes_per_unknown_against_t.png", dpi=105)
    plt.close(fig)

    # Figure 7: the dense inverse of the SOR block
    sor = json.loads((OUT / "sor_block.json").read_text())
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    nb = np.array([r["n_block"] for r in sor], float)
    ax.plot(nb, [r["diff"] / 1e9 for r in sor], "o", label="measured (peak of one SOR iteration minus the peak of the build)")
    x = np.linspace(500, 13000, 100)
    ax.plot(x, 16 * x ** 2 / 1e9, "--", label="16 n^2 (the first estimate)")
    ax.plot(x, 72 * x ** 2 / 1e9, "-", label="72 n^2 (proposed)")
    ax.axvline(5000, color="r", ls=":", lw=0.8)
    ax.text(5050, 0.2, "MAX_SOR_BLOCK = 5000", color="r", fontsize=7)
    ax.set_xlabel("unknowns n of the largest via block"), ax.set_ylabel("memory of the block inverse (GB)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_07_sor_block_memory.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    main()
