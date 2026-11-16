#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the data of research/lumped-edge-link: error of the Lumped part read-out against the gap to the side, and against the independent 3D reference.
@details Reads out/remeasure_first.json (study_remeasure.py with REMEASURE_VARIANTS=program,first,first:zone) and out/reference3d.json (study_reference3d.py). Figure 2: hottest-point
         error against the gap (100 x 80 mm, 2 layers, 6 mm part, edge film 10 W/m2K) at a side and at a corner, program and the first-link correction. Figure 3: the same part on the 40 x 40 mm
         board against the converged 3D solver. Run from the repository root: .venv/bin/python research/lumped-edge-link/scripts/make_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"


def fig_02():
    """!
    @brief Figure 2: error against the gap to the side.
    @return None.
    """
    rows = json.loads((ROOT / "out" / "remeasure_first.json").read_text())
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for a, place in zip(ax, ("edge", "corner")):
        for hs, ls in ((10.0, "-"), (200.0, "--")):
            sel = sorted([r for r in rows if r["W"] == 100.0 and r["side"] == 6.0 and r["layers"] == 2 and r["place"] == place and r["h_side"] == hs], key=lambda r: r["d"])
            xs = [r["d"] for r in sel]
            a.plot(xs, [r["program"][1] for r in sel], "o" + ls, color="#c0392b", label=f"program, edge film {hs:g}")
            a.plot(xs, [r["first"][1] for r in sel], "s" + ls, color="#2471a3", label=f"first link corrected, edge film {hs:g}")
        a.axhline(0, color="k", lw=0.6)
        a.set_xscale("symlog", linthresh=1.0)
        a.set_xlim(-0.2, 30)
        a.set_xlabel("gap from the part to the nearest side (mm)")
        a.set_title(f"6 mm part, 100 x 80 mm, 2 layers: {place}", fontsize=9)
        a.grid(alpha=0.3)
    ax[0].set_ylabel("hottest point of the part, Lumped / FVM - 1 (%)")
    ax[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_02_error_against_gap.png", dpi=130)


def fig_03():
    """!
    @brief Figure 3: error against the independent 3D solver on the 40 x 40 mm board.
    @return None.
    """
    rows = json.loads((ROOT / "out" / "reference3d.json").read_text())
    labels = [f"{r['place']} {r['gap']:g}" for r in rows]
    fig, a = plt.subplots(figsize=(9, 4))
    w = 0.2
    for i, (v, c) in enumerate((("fvm_0.5", "#7f8c8d"), ("program", "#c0392b"), ("pot", "#e59866"), ("first", "#2471a3"))):
        vals = [100 * ((r[v][1] if v != "fvm_0.5" else r[v][1]) / r["3d_converged"]["peak"] - 1) for r in rows]
        a.bar([k + (i - 1.5) * w for k in range(len(rows))], vals, w, color=c, label={"fvm_0.5": "FVM 0.5 mm", "program": "Lumped, program", "pot": "Lumped, potential links (earlier candidate)", "first": "Lumped, first link corrected"}[v])
    a.set_xticks(range(len(rows)))
    a.set_xticklabels(labels, rotation=30, fontsize=8)
    a.axhline(0, color="k", lw=0.6)
    a.set_ylabel("hottest point of the part against the 3D solver (%)")
    a.set_title("6 mm part, 40 x 40 mm, insulated sides, converged 3D (labels: place, gap in mm)", fontsize=9)
    a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_03_against_3d.png", dpi=130)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_03()
    if (ROOT / "out" / "remeasure_first.json").exists():
        fig_02()
