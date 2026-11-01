#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures of the real-boards investigation, drawn from the JSON results of the studies in out/ (run the studies first; a figure whose result file is missing is skipped with a message).
@details Figures (numbering continues after the diagrams of make_diagrams.py): fig_04 the error of each copper mapping on the real windows (study_copper_mapping), fig_05 memory against the unknowns
         with the fitted line (study_time_memory), fig_06 the step response of the heater by cell size (study_transient_fine), fig_07 the fine-copper indicator against the error of the cell model with
         the threshold (study_fine_copper_warning). Every number in a figure comes from the printed results; a curve that is only illustrative is not drawn here.
         fig_14 to fig_16 the 30 parts of the RP2040 board against the prototype's group rule and the envelope rule (lib/component_match.py, lib/component_views.py), fig_17 box or hull as the heat-source shape,
         fig_18 and fig_19 screenshots of the import window prototype (lib/window_shots.py); these need data/rp2040 (git-ignored; fetch_boards.py) and are skipped with a message without it; fig_18 and fig_19 also need PySide 6 (QT_QPA_PLATFORM=offscreen is set).
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/make_figures.py   (matplotlib and NumPy only)
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
import numpy as np                                                # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT, FIG = ROOT / "out", ROOT / "figures"


def load(name):
    """!
    @brief Read a result file of out/.
    @param name File name.
    @return The parsed JSON, or None with a message when the file is missing.
    """
    p = OUT / name
    if not p.exists():
        print(f"skipped: {p} is missing (run the study first)")
        return None
    return json.loads(p.read_text())


def fig_mapping():
    """!
    @brief Boxplot of the error of the mapping methods against the program's pixel run (Part B) and against the pixel reference (Part A).
    @return None.
    """
    d = load("copper_mapping.json")
    if d is None:
        return
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    a = d["part_a"]
    for cell, ax in zip(sorted({c for r in a for c in r["errors"]}), axs[:1]):
        methods = sorted({m for r in a for m in r["errors"].get(cell, {})})
        ax.boxplot([[r["errors"][cell][m]["5"] for r in a if cell in r["errors"]] for m in methods])
        ax.set_xticklabels(methods)
        ax.set_title(f"one sheet, cell {cell} mm, against the five-point pixel reference", fontsize=8)
        ax.tick_params(axis="x", labelrotation=25, labelsize=7)
        ax.set_ylabel("heater mean rise error (%)")
    b = d["part_b"]
    methods = ("today", "flow", "lambda")
    axs[1].boxplot([[r["errors_percent"][m] for r in b] for m in methods])
    axs[1].set_xticklabels(methods)
    axs[1].set_title("program network, all layers, against its pixel run", fontsize=8)
    for ax in axs:
        ax.axhline(0, color="k", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_mapping_errors.png", dpi=105)


def fig_memory():
    """!
    @brief Peak memory against unknowns, one point per case, with the fitted line.
    @return None.
    """
    d = load("time_memory.json")
    if d is None or not d["cases"]:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    u = np.array([c["unknowns_faces"] for c in d["cases"]], float)
    pk = np.array([c["phases"][-1]["peak_bytes"] for c in d["cases"]], float) / 1e9
    ax.scatter(u / 1e6, pk)
    if d["fit"]:
        base = np.median([c["baseline_bytes"] for c in d["cases"]]) / 1e9
        xs = np.linspace(0, u.max(), 20)
        ax.plot(xs / 1e6, base + xs * d["fit"]["bytes_per_unknown"] / 1e9, "k--", label=f"{d['fit']['bytes_per_unknown'] / 1e3:.1f} KB per unknown")
        ax.legend()
    ax.set_xlabel("unknowns (millions)")
    ax.set_ylabel("peak resident memory (GB)")
    ax.set_title("imported board, flow-based faces, direct solve", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_memory_per_unknown.png", dpi=105)


def fig_transient():
    """!
    @brief The heater step response at the listed times for the reference and the cell sizes.
    @return None.
    """
    d = load("transient_fine.json")
    if d is None:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for r in d:
        if not r["copper_capacity"]:
            continue
        t, v = zip(*r["samples"])
        ax.plot(t, v, marker="o", label=r["name"])
    ax.set_xscale("log")
    ax.set_xlabel("time (s)")
    ax.set_ylabel("heater mean rise (K)")
    ax.legend(fontsize=7)
    ax.set_title("step response of the imported board by cell size", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_transient_by_cell.png", dpi=105)


def fig_fine():
    """!
    @brief The thin-copper share against the error of the cell model, with the threshold of the 10 % limit.
    @return None.
    """
    d = load("fine_copper_warning.json")
    if d is None:
        return
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for ax, method in zip(axs, ("fill", "flow")):
        for cell, col in ((0.5, "tab:blue"), (1.0, "tab:orange"), (2.0, "tab:green")):
            pts = [(c["thin_share"], abs(c[f"{method}_error_percent"])) for c in d["cases"] if c["cell"] == cell]
            if pts:
                ax.scatter(*zip(*pts), s=14, color=col, label=f"cell {cell} mm")
        cal = d["calibration"].get(f"cell all | {method} model | thin_share | error above 10 %")
        if cal and not np.isnan(cal["threshold"]):
            ax.axvline(cal["threshold"], color="k", linestyle="--", linewidth=1)
        ax.axhline(10, color="grey", linewidth=0.6)
        ax.set_xlabel("share of the copper thinner than the cell")
        ax.set_ylabel("absolute error of the heater rise (%)")
        ax.set_title(f"{method} model", fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_07_fine_copper_threshold.png", dpi=105)


def fig_paste_window():
    """!
    @brief fig_08: a window of the ISASTM top paste layer with the groups of TO.C (one box per part), the groups by proximity (link 1.0 mm, dashed) and the placement origins (crosses); needs the board in data/ and the research environment (the reader), skipped otherwise.
    @return None.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import _bootstrap  # noqa: F401
        import native_gerber as ng
        import paste
        import pnp
        import registry
        r = registry.roles("isastm")
    except Exception as exc:                                       # no data or no reader: skip, as for the missing results
        print(f"skipped fig_08: {exc}")
        return
    refs = paste.by_reference(r["paste_top"])
    box = ng.layer_bbox(r["outline"])
    groups = paste.by_proximity(r["paste_top"], box, pix=0.05, link_mm=1.0)
    parts = {q["ref"]: q for q in pnp.read_placement(r["placement"]) if q["side"] == "top"}
    cx, cy, w = 60.0, -90.0, 22.0                                 # a dense window under the large chips (the paste of the big parts and of their capacitors)
    fig, ax = plt.subplots(figsize=(8.5, 8.5))
    layer = ng.Layer(r["paste_top"].read_text(errors="replace"))
    x0, y1 = cx - w / 2, cy + w / 2
    cv = ng.Canvas(x0, y1, w, w, 0.05)
    layer.draw(cv)
    ax.imshow(cv.mask, extent=(x0, x0 + w, y1 - w, y1), cmap="Greys", alpha=0.55)
    rng = np.random.default_rng(2)
    for k, g in refs.items():
        b = g["bbox"]
        if b[2] < x0 or b[0] > x0 + w or b[3] < y1 - w or b[1] > y1:
            continue
        col = plt.cm.tab20(rng.integers(0, 20))
        ax.add_patch(plt.Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec=col, lw=1.6))
        if k in parts:
            ax.plot(parts[k]["x"], parts[k]["y"], "+", color=col, ms=9, mew=1.8)
        if b[2] - b[0] > 1.5:
            ax.text(b[0], b[3] + 0.1, k, fontsize=7, color=col)
    for g in groups:
        b = g["bbox"]
        if b[2] < x0 or b[0] > x0 + w or b[3] < y1 - w or b[1] > y1:
            continue
        ax.add_patch(plt.Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="k", lw=1.0, ls="--"))
    ax.set_xlim(x0, x0 + w)
    ax.set_ylim(y1 - w, y1)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("ISASTM top paste: boxes by TO.C (colour), proximity 1.0 mm (dashed), placement (+)")
    fig.tight_layout()
    fig.savefig(FIG / "fig_08_paste_groups_window.png", dpi=105)
    plt.close(fig)


def fig_project_and_links():
    """!
    @brief fig_09: left, the size of the embedded masks of the project file against the pixel (study_project_file); right, the references of TO.C that land in exactly one proximity group against the link distance (study_paste_footprints).
    @return None.
    """
    pf, pp = load("project_file.json"), load("paste_footprints.json")
    if pf is None or pp is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    for board in sorted({r["board"] for r in pf}):
        rows = [r for r in pf if r["board"] == board]
        ax[0].plot([r["pix"] for r in rows], [r["binary_json_bytes"] / 1e6 for r in rows], "o-", label=board)
    ax[0].set_xscale("log")
    ax[0].set_yscale("log")
    ax[0].invert_xaxis()
    ax[0].set_xlabel("pixel of the embedded mask (mm)")
    ax[0].set_ylabel("binary masks, JSON text (MB)")
    ax[0].axhline(20, color="r", ls=":")
    ax[0].text(0.1, 21, "criterion 20 MB", color="r", fontsize=8)
    ax[0].legend(fontsize=7)
    ax[0].set_title("project file: size of the embedded copper")
    for board in ("isastm", "cmm2", "oswlight", "stickhub"):
        g = pp[board]["top"]["groups"]
        n = g["references_in_file"]
        links = sorted(g["links"], key=float)
        ax[1].plot([float(l) for l in links], [100.0 * g["links"][l]["parts_intact"] / n for l in links], "o-", label=f"{board} ({n} parts)")
    ax[1].axhline(95, color="r", ls=":")
    ax[1].text(0.32, 96, "criterion 95 %", color="r", fontsize=8)
    ax[1].set_xlabel("link distance of the proximity groups (mm)")
    ax[1].set_ylabel("parts whose group is exactly the part (%)")
    ax[1].legend(fontsize=7)
    ax[1].set_title("does the proximity group equal the part (TO.C)?")
    fig.tight_layout()
    fig.savefig(FIG / "fig_09_project_size_and_links.png", dpi=105)
    plt.close(fig)


RULE_VARIANTS = ("today_off", "today_on", "flow_off", "flow_naive", "flow_on", "lambda_on")
RULE_LABELS = ("fill\nrule off", "fill\nrule on", "faces\nrule off", "faces, old\nsheet, on", "faces, reduced\nsheet, on", "lambda 0.5\nreduced, on")


def fig_rule_on():
    """!
    @brief The error of every mapping against the independent 3D reference with the laminate rule on and off (study_rule_on_faces): real two-layer windows, real four-layer windows and the synthetic boards, at the two cells.
    @return None.
    """
    real = load("rule_on_faces_real.json")
    syn = load("rule_on_faces_synthetic.json")
    if real is None or syn is None:
        return
    rows = real["rows"] + syn["rows"]
    groups = (("real, 2 layers", "real", 2), ("real, 4 layers", "real", 4), ("synthetic (2 and 4 layers)", "synthetic", None))
    fig, axs = plt.subplots(2, 3, figsize=(12, 6.2), sharey=True)
    for i, cell in enumerate((0.6, 1.2)):
        for j, (title, kind, layers) in enumerate(groups):
            ax = axs[i, j]
            sel = [r for r in rows if r["kind"] == kind and r["cell"] == cell and (layers is None or r["layers"] == layers)]
            rng = np.random.default_rng(3)
            for x, v in enumerate(RULE_VARIANTS):
                e = np.array([r["error"][v] for r in sel])
                ax.plot(x + rng.uniform(-0.15, 0.15, e.size), e, "o", color="#1f77b4", alpha=0.55, markersize=4)
                ax.plot([x - 0.3, x + 0.3], [np.abs(e).mean() * -1] * 2, color="#d62728", linewidth=2)      # minus the mean absolute error: the red bar is how far, on average, the points are from zero
            ax.axhline(0, color="k", linewidth=0.6)
            ax.set_xticks(range(len(RULE_VARIANTS)))
            ax.set_xticklabels(RULE_LABELS, fontsize=6)
            ax.set_title(f"{title}, cell {cell} mm (n = {len(sel)})", fontsize=8)
            if j == 0:
                ax.set_ylabel("heater mean rise error (%)")
    fig.suptitle("Blue: one window each; red bar: minus the mean absolute error of the variant", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_10_rule_on_errors.png", dpi=105)
    plt.close(fig)


def fig_rule_shift():
    """!
    @brief How much the laminate rule moves the answer of the program as it is ("today") and of the faces, window by window (rule off against rule on).
    @return None.
    """
    real = load("rule_on_faces_real.json")
    if real is None:
        return
    rows = real["rows"]
    fig, axs = plt.subplots(1, 2, figsize=(9, 4))
    for ax, (a, b, title) in zip(axs, (("today_off", "today_on", "fill fraction (the program as it is)"), ("flow_off", "flow_on", "flow-based faces (old sheet, off; reduced sheet, on)"))):
        for layers, color in ((2, "#d62728"), (4, "#1f77b4")):
            sel = [r for r in rows if r["layers"] == layers]
            ax.plot([r["error"][a] for r in sel], [r["error"][b] for r in sel], "o", color=color, label=f"{layers} layers", alpha=0.7)
        ax.plot([-9, 3], [-9, 3], "k", linewidth=0.6)
        ax.set_xlabel("error with the rule off (%)")
        ax.set_ylabel("error with the rule on (%)")
        ax.set_title(title, fontsize=8)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_11_rule_shift.png", dpi=105)
    plt.close(fig)


def fig_network_split():
    """!
    @brief Review of README 10 (study_rule_network_split): the error against the 3D reference split into the program's network at the pixel (left column of each panel) and the mapping alone
           (every variant against that pixel network), real and synthetic windows, two and four layers, at the two cells.
    @return None.
    """
    real = load("rule_on_faces_real.json")
    syn = load("rule_on_faces_synthetic.json")
    split = load("rule_network_split.json")
    if real is None or syn is None or split is None:
        return
    pixel = split["pixel"]
    rows = real["rows"] + syn["rows"]
    cols = ("network", "today_on", "flow_naive", "flow_on", "lambda_on")
    labels = ("network at\nthe pixel\n(against 3D)", "fill\nrule on", "faces, old\nsheet, on", "faces, reduced\nsheet, on", "lambda 0.5\nreduced, on")
    fig, axs = plt.subplots(2, 2, figsize=(10.5, 6.4), sharey=True)
    for i, cell in enumerate((0.6, 1.2)):
        for j, kind in enumerate(("real", "synthetic")):
            ax = axs[i, j]
            rng = np.random.default_rng(5)
            for layers, color in ((2, "#d62728"), (4, "#1f77b4")):
                sel = [r for r in rows if r["kind"] == kind and r["cell"] == cell and r["layers"] == layers]
                for x, v in enumerate(cols):
                    if v == "network":
                        e = [100 * (pixel[r["name"]]["on"] / r["ref_mean"] - 1) for r in sel]
                    else:
                        e = [100 * (r["mean"][v] / pixel[r["name"]]["on"] - 1) for r in sel]
                    ax.plot(x + (layers - 3) * 0.12 + rng.uniform(-0.05, 0.05, len(e)), e, "o", color=color, alpha=0.6, markersize=4, label=f"{layers} layers" if x == 0 else None)
            ax.axhline(0, color="k", linewidth=0.6)
            ax.axvline(0.5, color="0.6", linewidth=0.8, linestyle="--")
            ax.set_xticks(range(len(cols)))
            ax.set_xticklabels(labels, fontsize=6)
            ax.set_title(f"{kind} windows, cell {cell} mm", fontsize=8)
            if j == 0:
                ax.set_ylabel("error (% of the heater mean rise)")
            ax.legend(fontsize=6, loc="lower right")
    fig.suptitle("Left of the dashed line: the program's network on the 0.1 mm pixel against the 3D reference; right: each mapping against that pixel network (the mapping alone)", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_13_network_and_mapping.png", dpi=105)
    plt.close(fig)


def fig_components():
    """!
    @brief Figures 14 to 17: the matching of the paste openings to the parts of the RP2040 board (two overviews, three crops) and the box-or-hull sheet.
    @return None
    """
    if not (ROOT / "data" / "rp2040" / "pos.csv").exists():
        print("skipped: data/rp2040 is missing (run fetch_boards.py)")
        return
    sys.path[:0] = [str(ROOT / "lib"), str(ROOT.parents[1])]
    import component_views as cv
    cv.setup("rp2040")
    cv.draw_overviews(FIG / "fig_14_component_match_prototype.png", FIG / "fig_15_component_match_improved.png")
    cv.draw_crops(FIG / "fig_16_component_match_crops.png")
    for r in cv.draw_source_shape(FIG / "fig_17_source_shape_box_hull.png"):
        print("source shape %s: %d openings, paste %.1f, box %.1f, hull %.1f mm2 (%+.1f %%), T box %.1f hull %.1f openings %.1f K" % r)


def fig_window():
    """!
    @brief Figures 18 and 19: the three steps of the hybrid import window and the three re-import dialogs (screenshots of the prototype, offscreen Qt).
    @return None
    """
    if not (ROOT / "data" / "rp2040" / "pos.csv").exists():
        print("skipped: data/rp2040 is missing (run fetch_boards.py)")
        return
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path[:0] = [str(ROOT / "lib"), str(ROOT.parents[1])]
    import window_shots as ws
    ws.draw_window_figures(FIG / "fig_18_import_window_hybrid_steps.png", FIG / "fig_19_import_window_reimport.png")


def main():
    """!
    @brief Draw every figure whose results exist.
    @return None.
    """
    FIG.mkdir(parents=True, exist_ok=True)
    for f in (fig_mapping, fig_memory, fig_transient, fig_fine, fig_paste_window, fig_project_and_links, fig_rule_on, fig_rule_shift, fig_network_split, fig_components, fig_window):
        f()


if __name__ == "__main__":
    main()
    sys.exit(0)
