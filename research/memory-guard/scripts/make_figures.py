#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the memory guard, drawn from out/ladder.jsonl and out/fit.json (run study_memory_ladder.py --run --fit first): peak memory against unknowns with the fitted law and the limits of three machines, and the time against the unknowns with the cell-major series.
@details Files: fig_04_memory_against_unknowns.png, fig_05_time_and_cell_major.png (the numbers 01 to 03 belong to make_diagrams.py).
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
    @brief Draw the two data figures.
    @return None.
    """
    recs = [json.loads(line) for line in (OUT / "ladder.jsonl").read_text().splitlines() if line.strip()]
    fit = json.loads((OUT / "fit.json").read_text())
    ok = [r for r in recs if r["status"] == "ok" and r["spec"].get("mode", "solve") == "solve" and r["spec"]["series"] != "baseline"]
    FIG.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for series in sorted({r["spec"]["series"] for r in ok}):
        pts = sorted((r["unknowns"], r["peak_bytes"] / 1e9) for r in ok if r["spec"]["series"] == series)
        ax.plot(*zip(*pts), "o-", ms=3, lw=0.8, label=series)
    n = np.geomspace(1e4, 3e6, 100)
    for key, v in fit.items():
        if isinstance(v, dict) and "@cell_major" not in key:
            c = mm.Coeffs(v["base"], v["k"], v["p"])
            ax.plot(n, [mm.estimate_bytes(x, "c", {"c": c}) / 1e9 for x in n], "k--", lw=0.6)
    for ram in (8, 16, 64):
        ax.axhline(0.7 * ram, color="r", lw=0.8, ls=":")
        ax.text(1.1e4, 0.7 * ram * 1.04, f"70 % of {ram} GB", color="r", fontsize=7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("unknowns")
    ax.set_ylabel("peak resident memory (GB)")
    ax.legend(fontsize=5, ncol=2)
    ax.set_title("Peak memory of a solve against the unknowns (dashed: fitted law per class)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_memory_against_unknowns.png", dpi=105)
    plt.close(fig)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.6))
    for series in sorted({r["spec"]["series"] for r in ok if r["spec"]["model"] in ("fvm", "fdm")}):
        pts = sorted((r["unknowns"], r.get("t_solve", np.nan), r["peak_bytes"] / 1e9) for r in ok if r["spec"]["series"] == series)
        style = "--" if series.endswith("cellmajor") else "-"
        axs[0].plot([p[0] for p in pts], [p[1] for p in pts], style, marker="o", ms=3, lw=0.8, label=series)
        axs[1].plot([p[0] for p in pts], [p[2] for p in pts], style, marker="o", ms=3, lw=0.8)
    axs[0].set_xscale("log"), axs[0].set_yscale("log"), axs[1].set_xscale("log"), axs[1].set_yscale("log")
    axs[0].set_xlabel("unknowns"), axs[0].set_ylabel("solve time (s)"), axs[1].set_xlabel("unknowns"), axs[1].set_ylabel("peak memory (GB)")
    axs[0].legend(fontsize=5, ncol=2)
    fig.suptitle("Solve time and peak memory, layer-major (solid) and cell-major (dashed) numbering", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_time_and_cell_major.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    main()
