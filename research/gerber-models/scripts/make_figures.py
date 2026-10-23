"""!
@file make_figures.py
@brief The pictures of phase 2: the mapping of real copper to cells, the thermal maps of our board, the import end to end and its set-up, the five models on our board and on the rectangle board.
@details Figures are committed on purpose (the README files link to them); the caches they read are in out/ and are made by the studies. Run: .venv/bin/python research/gerber-models/scripts/make_figures.py (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import conduction as cd
import native_gerber as ng
import our_board
import scenarios as sc
import windows

from paths import FIGURES as OUT, OUT as CACHE                           # kept in the repository on purpose: the README files link to them


def fig_mapping():
    """!
    @brief One real window: the 0.1 mm copper mask, the fill fraction per 1 mm cell (today) and the ratio of the flow-based cell conductance to the arithmetic one.
    @return None.
    """
    windows.BOARDS = ["storm"]                                          # Stormduino (MIT): the only board whose licence allows a picture of it
    windows.FILE = windows.OUT / "windows_storm.npz"
    masks, meta = windows.load()
    k = 1
    mask = masks[k]
    S = cd.sheet_of(mask[::-1])
    n = 10                                                              # pixels per 1 mm cell
    a, b = float(S.max()), float(S.min())
    f = (cd.cell_blocks(S, n) == a).mean(axis=(2, 3))
    gx, gy = cd.dual_faces(S, n, 0)
    tot = np.zeros(f.shape); cnt = np.zeros(f.shape)
    tot[:, :-1] += gx; cnt[:, :-1] += 1; tot[:, 1:] += gx; cnt[:, 1:] += 1
    tot[:-1, :] += gy; cnt[:-1, :] += 1; tot[1:, :] += gy; cnt[1:, :] += 1
    flow = tot / cnt
    arith = cd.map_power(f, 1.0, a, b)
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
    axs[0].imshow(mask, cmap="copper", interpolation="nearest", extent=(0, 36, 0, 36))
    axs[0].set_title("Stormduino (MIT): 36 x 36 mm of real copper, 0.1 mm pixels", fontsize=9)
    im = axs[1].imshow(f[::-1], cmap="viridis", vmin=0, vmax=1, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[1].set_title("copper fraction of each 1 mm cell (what the program uses today)", fontsize=9)
    fig.colorbar(im, ax=axs[1])
    im = axs[2].imshow((flow / arith)[::-1], cmap="RdBu", vmin=0.2, vmax=1.8, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[2].set_title("flow-based / arithmetic cell conductance\nred (< 1): the fraction overestimates it (board too cool)\nblue (> 1): it underestimates it", fontsize=9)
    fig.colorbar(im, ax=axs[2])
    for ax in axs:
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_copper_mapping_to_cells.png", dpi=110)
    plt.close(fig)


def fig_board_thermal():
    """!
    @brief The IC board of our own (our_board.py) as a thermal problem: 1 W under the IC, border held at 0 K, h = 10 W/m2K. The temperature rise resolved pixel by pixel, and the difference of the 1 mm cell models (fill fraction today, flow-based faces) from it.
    @return None.
    """
    layer = ng.Layer(our_board.gerber_text())
    cv = ng.Canvas(0.0, our_board.SIZE, our_board.SIZE, our_board.SIZE, 0.1)
    layer.draw(cv)
    S = cd.sheet_of(cv.mask[::-1])
    power, fixed, (y0, y1, x0, x1) = sc.box_scenario(S.shape, 0.1, 6.0)
    ref = sc.pixel_reference(S, 0.1, power, 10.0, fixed)
    n = 10
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power.reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed, n).mean(axis=(2, 3)) >= 0.5
    ref_cells = ref.reshape(cy, n, cx, n).mean(axis=(1, 3))
    faces = sc.coarse_faces(S, n, cd.S_CU, cd.S_LAM)
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
    ext = (0, our_board.SIZE, 0, our_board.SIZE)
    im = axs[0].imshow(ref[::-1], cmap="inferno", interpolation="nearest", extent=ext)
    axs[0].contour(cv.mask[::-1].astype(float), levels=[0.5], colors="w", linewidths=0.3, extent=ext, origin="lower")
    axs[0].set_title("resolved temperature rise (K): 1 W under the IC, border at 0 K", fontsize=9)
    fig.colorbar(im, ax=axs[0])
    for ax, key, label in ((axs[1], "fill fraction (today)", "fill fraction per 1 mm cell (today)"), (axs[2], "flow-based faces", "flow-based faces on 1 mm cells")):
        gx, gy = faces[key]
        T = sc.solve_general(gx, gy, 1.0, pw, 10.0, fx)
        d = T - ref_cells
        im = ax.imshow(d[::-1], cmap="RdBu_r", vmin=-15, vmax=15, interpolation="nearest", extent=ext)
        ax.set_title(f"{label}: difference from the resolved field (K)\nheater mean {100 * (T[y0 // n:y1 // n, x0 // n:x1 // n].mean() / ref[y0:y1, x0:x1].mean() - 1):+.1f} %", fontsize=9)
        fig.colorbar(im, ax=ax)
    for ax in axs:
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_ic_board_thermal.png", dpi=110)
    plt.close(fig)


def fig_import_end_to_end():
    """!
    @brief The import path end to end on two boards (needs out/import_end_to_end.npz from study_import_end_to_end.py): the copper and holes imported from the files, the temperature of the top layer resolved at the pixel grid, and the difference of the program as it is and of the imported path from it.
    @return None.
    """
    path = CACHE / "import_end_to_end.npz"
    if not path.exists():
        print("figure 03 skipped: run study_import_end_to_end.py first")
        return
    d = np.load(path)
    fig, axs = plt.subplots(2, 4, figsize=(17, 8.6))
    for r, (tag, name) in enumerate((("storm", "Stormduino (MIT), 2 layers, 109 plated holes"), ("ours", "our IC board, 1 layer, 16 plated holes"))):
        cov, holes, hx = d[f"{tag}_cov"], d[f"{tag}_holes"], d[f"{tag}_heater"]
        ref, today, imp = d[f"{tag}_fine"], d[f"{tag}_today"], d[f"{tag}_flow_coverage"]
        h, w = ref.shape
        ext = (0, w, 0, h)
        green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
        axs[r, 0].imshow(np.where(cov[..., None] > 0.5, gold, green), extent=ext, interpolation="nearest")      # the mask has 10 pixels per mm, the board h x w mm
        for x, y, dd in holes:
            axs[r, 0].add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0 + 0.2, facecolor="#101010", edgecolor="w", linewidth=0.3))
        axs[r, 0].add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.2))
        axs[r, 0].set_title(f"{name}\ntop copper from the Gerber, holes from the drill file, heater (cyan)", fontsize=8)
        im = axs[r, 1].imshow(ref, origin="lower", extent=ext, cmap="inferno")
        axs[r, 1].set_title("temperature rise of the top layer (K)\nreference: the program on the pixel grid (0.1 mm)", fontsize=8)
        fig.colorbar(im, ax=axs[r, 1], fraction=0.046)
        lim = 0.15 * ref.max()
        for c, (fld, label) in enumerate(((today, "the program as it is (one zone per cell, fill = copper fraction)"), (imp, "imported path (flow-based faces, coverage mask)")), start=2):
            sl = (slice(int(hx[1] - 3), int(hx[1] + 3)), slice(int(hx[0] - 3), int(hx[0] + 3)))
            err = 100 * (fld[sl].mean() / ref[sl].mean() - 1)
            im = axs[r, c].imshow(fld - ref, origin="lower", extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim)
            axs[r, c].set_title(f"{label}\ndifference from the reference (K); heater mean {err:+.1f} %", fontsize=8)
            fig.colorbar(im, ax=axs[r, c], fraction=0.046)
        for c in range(4):
            axs[r, c].set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_import_end_to_end.png", dpi=105)
    plt.close(fig)


def fig_import_setup():
    """!
    @brief The set-up of the end-to-end runs (needs out/import_end_to_end.npz): where the 6 x 6 mm heater is on each board, the holes, a 20 mm window round the heater with the 1 mm thermal cells, the copper fraction per cell that the program uses today, and the reference temperature in the window.
    @return None.
    """
    path = CACHE / "import_end_to_end.npz"
    if not path.exists():
        print("figure 04 skipped: run study_import_end_to_end.py first")
        return
    d = np.load(path)
    fig, axs = plt.subplots(2, 4, figsize=(17, 8.6))
    green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
    for r, (tag, name) in enumerate((("storm", "Stormduino (MIT)"), ("ours", "our IC board"))):
        cov, holes, hx, ref = d[f"{tag}_cov"], d[f"{tag}_holes"], d[f"{tag}_heater"], d[f"{tag}_fine"]
        h, w = ref.shape
        x0, x1 = max(0, int(hx[0] - 10)), min(w, int(hx[0] + 10))
        y0, y1 = max(0, int(hx[1] - 10)), min(h, int(hx[1] + 10))
        rgb = np.where(cov[..., None] > 0.5, gold, green)
        # overview: whole board, window (white) and heater (cyan)
        a = axs[r, 0]
        a.imshow(rgb, extent=(0, w, 0, h), interpolation="nearest")
        for x, y, dd in holes:
            a.add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0 + 0.2, facecolor="#101010", edgecolor="w", linewidth=0.3))
        a.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="w", linewidth=1.0, linestyle="--"))
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.4))
        a.set_title(f"{name}: top copper, {len(holes)} plated holes (black)\nwindow 20 x 20 mm (dashed), heater 6 x 6 mm, 1 W (cyan)", fontsize=8)
        # zoom with the 1 mm thermal cells
        a = axs[r, 1]
        a.imshow(rgb[::-1][h * 10 - y1 * 10: h * 10 - y0 * 10][:, x0 * 10: x1 * 10] if False else rgb[(h - y1) * 10:(h - y0) * 10, x0 * 10:x1 * 10], extent=(x0, x1, y0, y1), interpolation="nearest")
        for x, y, dd in holes:
            if x0 <= x <= x1 and y0 <= y <= y1:
                a.add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0, facecolor="#101010", edgecolor="w", linewidth=0.3))
        a.set_xticks(range(x0, x1 + 1)); a.set_yticks(range(y0, y1 + 1)); a.grid(color="w", linewidth=0.3, alpha=0.6)
        a.tick_params(labelsize=5)
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.6))
        a.set_title("window with the 1 mm cells of the thermal grid\n(copper from the 0.1 mm mask; heater = 6 x 6 cells)", fontsize=8)
        # copper fraction per cell: what the program's one-zone-per-cell path would use
        frac = cov.reshape(h, 10, w, 10).mean(axis=(1, 3))[::-1]
        a = axs[r, 2]
        im = a.imshow(frac[h - y1:h - y0, x0:x1], extent=(x0, x1, y0, y1), cmap="viridis", vmin=0, vmax=1, interpolation="nearest")
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="w", linewidth=1.4))
        a.set_title(f"copper fraction per cell (the program's fill today)\nmean under the heater {frac[int(hx[1]-3):int(hx[1]+3), int(hx[0]-3):int(hx[0]+3)].mean():.2f}", fontsize=8)
        fig.colorbar(im, ax=a, fraction=0.046)
        # reference temperature in the window
        a = axs[r, 3]
        im = a.imshow(ref[y0:y1, x0:x1], origin="lower", extent=(x0, x1, y0, y1), cmap="inferno", interpolation="nearest")
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.4))
        a.set_title(f"reference temperature rise (K), max {ref.max():.0f} K\nheater block mean {ref[int(hx[1]-3):int(hx[1]+3), int(hx[0]-3):int(hx[0]+3)].mean():.0f} K", fontsize=8)
        fig.colorbar(im, ax=a, fraction=0.046)
        for c in range(4):
            axs[r, c].set_xlabel("mm")
    fig.suptitle("Set-up of the end-to-end runs: heater 6 x 6 mm, 1 W on the top layer; 10 W/m2K on both faces; insulated edges; 1.6 mm board, 35 um copper; plated holes as vias", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_import_setup.png", dpi=105)
    plt.close(fig)


def fig_models_our_board():
    """!
    @brief The five models of the program on our IC board (needs out/models_our_board.npz from study_models_our_board.py): the mean rise of the heater from the fine mask and from the four cell mappings, and the error of each mapping against the model's own fine run.
    @return None.
    """
    path = CACHE / "models_our_board.npz"
    if not path.exists():
        print("figure 05 skipped: run study_models_our_board.py first")
        return
    d = np.load(path)
    models, maps, truth, coarse = list(d["models"]), list(d["maps"]), d["truth"], d["coarse"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(models))
    wd = 0.15
    cols = ["#222222", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    series = [("fine mask (own truth)", truth)] + [(m, coarse[i]) for i, m in enumerate(maps)]
    for k, (lab, v) in enumerate(series):
        axs[0].bar(x + (k - 2) * wd, v, wd, label=lab, color=cols[k])
    axs[0].set_ylim(0, 160)                                                   # the 3D solid is far above (260 to 390 K) and is cut
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(models)
    axs[0].set_ylabel("mean rise over the heater (K)")
    axs[0].set_title("our IC board, 1 W in 6 x 6 mm: the 3D solid (262 to 392 K) is cut", fontsize=9)
    axs[0].legend(fontsize=7)
    for k, i in enumerate(range(len(maps))):
        err = 100 * (coarse[i] / truth - 1)
        axs[1].bar(x + (k - 1.5) * 0.18, err, 0.18, label=maps[i], color=cols[k + 1])
    axs[1].axhline(0, color="k", linewidth=0.6)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(models)
    axs[1].set_ylabel("error against the model's own fine run (%)")
    axs[1].set_title("1 mm cells with the cell value of each mapping (positive = too hot)", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_models_our_board.png", dpi=105)
    plt.close(fig)


def fig_rect_board():
    """!
    @brief The board of squares and rectangles and the five models on it (needs out/models_rect_board_2l.npz and _1l.npz from study_models_rect_board.py): the layout with the heater, and the error of the program's own zones on 1 mm cells against each model's fine run for copper on the cell edges and between them.
    @return None.
    """
    p2, p1 = CACHE / "models_rect_board_2l.npz", CACHE / "models_rect_board_1l.npz"
    if not (p2.exists() and p1.exists()):
        print("figure 06 skipped: run study_models_rect_board.py 1 and 2 first")
        return
    import rect_board as rb
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    a = axs[0]
    a.imshow(rb.mask(0.0), origin="lower", extent=(0, rb.W, 0, rb.H), cmap="YlOrBr", vmin=-0.2, vmax=1.3)
    for r in rb.rects(0.4):
        a.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, edgecolor="k", linestyle="--", linewidth=0.7))
    hx = rb.heater(0.0)
    a.add_patch(plt.Rectangle((hx[0], hx[1]), hx[2] - hx[0], hx[3] - hx[1], fill=False, edgecolor="c", linewidth=1.6))
    a.set_xticks(range(0, 41, 5)); a.set_yticks(range(0, 31, 5)); a.grid(color="w", linewidth=0.3)
    a.set_title("rect_board: copper (gold), heater 6 x 6 mm 1 W (cyan);\nthe same copper moved 0.4 mm (dashed): off the 1 mm cell edges", fontsize=8)
    models = ["fvm", "fdm", "lumped", "analytic", "solid3d"]
    for ax, path, title in ((axs[1], p1, "one copper layer"), (axs[2], p2, "two layers (bottom empty)")):
        d = np.load(path)
        x = np.arange(len(models))
        for k, (tag, lab, col) in enumerate((("s0", "edges on the cells", "#2ca02c"), ("s4", "edges between cells (0.4 mm)", "#d62728"))):
            err = 100 * (d[f"{tag}_native"] / d[f"{tag}_truth"] - 1)
            ax.bar(x + (k - 0.5) * 0.35, err, 0.35, label=lab, color=col)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xticks(x); ax.set_xticklabels(models)
        ax.set_ylabel("program's own zones, 1 mm cells, against fine run (%)")
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_rect_board_models.png", dpi=105)
    plt.close(fig)


def fig_track_width_angle():
    """!
    @brief The thinnest track and the angle (needs out/track_width_angle.json from study_track_width_angle.py): what a track does to the heater, whether the binary mask keeps it in one piece, and the share of its cooling that the 1 mm cells reproduce at 0 and 45 degrees.
    @return None.
    """
    import json
    import study_track_width_angle as st
    path = CACHE / "track_width_angle.json"
    if not path.exists():
        print("figure 07 skipped: run study_track_width_angle.py first")
        return
    d = json.loads(path.read_text())
    W, A = st.WIDTHS, st.ANGLES
    fig, axs = plt.subplots(2, 2, figsize=(13, 9))
    for th in A:
        axs[0, 0].plot(W, [d[f"{w}/{th}"]["effect"] for w in W], marker="o", label=f"{th} deg")
    axs[0, 0].set_xscale("log")
    axs[0, 0].set_xlabel("track width (mm)")
    axs[0, 0].set_ylabel("heater temperature change with the track (%)")
    axs[0, 0].set_title("what one track across a 6 mm heater does (reference): even 0.05 mm cools it by 2 to 3 %", fontsize=8)
    axs[0, 0].legend(fontsize=7)
    x = np.arange(len(W))
    for k, th in enumerate(A):
        axs[0, 1].bar(x + (k - 1.5) * 0.2, [d[f"{w}/{th}"]["pieces"]["0.1"] for w in W], 0.2, label=f"{th} deg")
    axs[0, 1].axhline(1, color="k", linewidth=0.6)
    axs[0, 1].set_yscale("symlog", linthresh=1)
    axs[0, 1].set_xticks(x)
    axs[0, 1].set_xticklabels([str(w) for w in W], fontsize=7)
    axs[0, 1].set_xlabel("track width (mm)")
    axs[0, 1].set_ylabel("8-connected pieces in the binary mask at 0.1 mm")
    axs[0, 1].set_title("recognition: 1 = the track is one piece; 0 = lost; many = broken (at 0.05 mm pixels every track is 1)", fontsize=8)
    axs[0, 1].legend(fontsize=7)
    names = {"fill fraction (today)": "fill fraction (today)", "geometric mean": "geometric mean", "lambda 0.5": "lambda 0.5", "flow-based faces": "flow-based faces", "flow-based, margin 20 %": "flow-based, margin 20 %"}
    for ax, th in ((axs[1, 0], 0), (axs[1, 1], 45)):
        for m in st.METHODS:
            ax.plot(W, [st.capture(d, "coverage 0.1", m, w, th) for w in W], marker="o", label=names[m])
        ax.axhline(100, color="k", linewidth=0.6)
        ax.set_xscale("log")
        ax.set_ylim(0, 130)
        ax.set_xlabel("track width (mm)")
        ax.set_ylabel("share of the track's cooling reproduced by the 1 mm cells (%)")
        ax.set_title(f"track at {th} degrees (coverage mask at 0.1 mm)", fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_track_width_angle.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Make the figures of this investigation.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_mapping()
    fig_board_thermal()
    fig_import_end_to_end()
    fig_import_setup()
    fig_models_our_board()
    fig_rect_board()
    fig_track_width_angle()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
