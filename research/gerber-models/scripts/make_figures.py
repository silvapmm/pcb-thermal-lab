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


def fig_diagonal():
    """!
    @brief The nine-point experiment (needs out/diagonal.json from study_diagonal.py): the share of a track's cooling reproduced at 30 and 45 degrees by the five-point mappings and by the diagonal variants, and the error of every method on the 42 real windows.
    @return None.
    """
    import json
    import study_track_width_angle as st
    path = CACHE / "diagonal.json"
    if not path.exists():
        print("figure 08 skipped: run study_diagonal.py first")
        return
    d = json.loads(path.read_text())
    a, b = d["a"], d["b"]
    W = st.WIDTHS
    names = ["fill fraction (today)", "flow-based faces", "tensor, nine-point", "flow + diagonal 0.25", "flow + diagonal 0.5", "flow + diagonal"]
    labels = ["fill fraction (today)", "flow-based faces", "tensor, nine-point", "flow + diagonal, 0.25", "flow + diagonal, 0.5", "flow + diagonal, 1.0"]
    fig, axs = plt.subplots(1, 3, figsize=(17, 5.2), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    for ax, th in ((axs[0], 30), (axs[1], 45)):
        for m, lab in zip(names, labels):
            ax.plot(W, [a[f"{w}/{th}"][m]["9"] for w in W], marker="o", label=lab)
        ax.axhline(100, color="k", linewidth=0.6)
        ax.set_xscale("log")
        ax.set_ylim(0, 135)
        ax.set_xlabel("track width (mm)")
        ax.set_ylabel("share of the track's cooling reproduced (%)")
        ax.set_title(f"track at {th} degrees (nine-point reference)", fontsize=9)
    axs[0].legend(fontsize=7)
    use = ["fill fraction (today)", "lambda 0.5", "flow-based faces", "cell problem", "tensor, nine-point", "flow + diagonal 0.25", "flow + diagonal 0.5", "flow + diagonal"]
    x = np.arange(len(use))
    mae = [np.abs(np.array(b[m]["9"])).mean() for m in use]
    bias = [np.array(b[m]["9"]).mean() for m in use]
    axs[2].bar(x, mae, color="#1f77b4", label="mean absolute error")
    axs[2].plot(x, bias, "o", color="#d62728", label="bias (negative = too cool)")
    axs[2].axhline(0, color="k", linewidth=0.6)
    axs[2].set_ylim(-6, 8)
    axs[2].set_xticks(x)
    axs[2].set_xticklabels(["fill (today)", "lambda 0.5", "flow", "cell problem", "tensor 9-pt", "flow+diag 0.25", "flow+diag 0.5", "flow+diag 1.0"], rotation=40, ha="right", fontsize=7)
    axs[2].set_ylabel("error of the heater rise on 42 real windows (%)")
    axs[2].set_title("42 real windows, 1 mm cells (the fill fraction, 21 %, is cut)", fontsize=9)
    axs[2].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_08_diagonal.png", dpi=105)
    plt.close(fig)


def fig_diagonal_faces():
    """!
    @brief Diagrams of the cell network: the five-point and the nine-point links of a cell, the staircase that heat follows along a diagonal track, and the real face conductances (line width) of a 0.3 mm track at 45 degrees with the five-point flow-based faces and with the diagonal faces added.
    @return None.
    """
    import math
    import diagonal as dg
    from boards_synthetic import HEAD, mm
    fig = plt.figure(figsize=(17, 9.5))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1.15])
    # (a) the five-point cell
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-2.1, 1.6)
    ax.set_aspect("equal")
    ax.axis("off")
    for gx in (-1, 0, 1):
        for gy in (-1, 0, 1):
            ax.add_patch(plt.Rectangle((gx - 0.45, gy - 0.45), 0.9, 0.9, fill=(gx == 0 and gy == 0), facecolor="#f2c27b", edgecolor="k", linewidth=0.8))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ax.annotate("", (dx * 0.98, dy * 0.98), (dx * 0.5, dy * 0.5), arrowprops={"arrowstyle": "<->", "color": "#1f77b4", "linewidth": 2})
    ax.set_title("the program's network: a cell is linked to its 4 neighbours\n(one x face and one y face per cell pair)", fontsize=9)
    ax.text(0, -1.85, "heat on a diagonal must zig-zag through x and y faces", ha="center", fontsize=8)
    # (b) the nine-point cell
    ax = fig.add_subplot(gs[0, 1])
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-2.1, 1.6)
    ax.set_aspect("equal")
    ax.axis("off")
    for gx in (-1, 0, 1):
        for gy in (-1, 0, 1):
            ax.add_patch(plt.Rectangle((gx - 0.45, gy - 0.45), 0.9, 0.9, fill=(gx == 0 and gy == 0), facecolor="#f2c27b", edgecolor="k", linewidth=0.8))
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ax.annotate("", (dx * 0.98, dy * 0.98), (dx * 0.5, dy * 0.5), arrowprops={"arrowstyle": "<->", "color": "#1f77b4", "linewidth": 2})
    for dx, dy in ((1, -1), (-1, 1)):
        ax.annotate("", (dx * 0.98, dy * 0.98), (dx * 0.42, dy * 0.42), arrowprops={"arrowstyle": "<->", "color": "#d62728", "linewidth": 2})
    for dx, dy in ((1, 1), (-1, -1)):
        ax.annotate("", (dx * 0.98, dy * 0.98), (dx * 0.42, dy * 0.42), arrowprops={"arrowstyle": "<->", "color": "#2ca02c", "linewidth": 2})
    ax.set_title("the experiment: 4 more links to the diagonal neighbours\n(red: d1 pair, falling to the right; green: d2 pair, rising; blue: axial, as before)", fontsize=9)
    ax.text(0, -1.85, "diagonal conductance = what the cell tensor says\nthe axial faces do not already deliver", ha="center", fontsize=8)
    # (c) the staircase
    ax = fig.add_subplot(gs[0, 2])
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    ax.set_aspect("equal")
    ax.set_xticks(range(7))
    ax.set_yticks(range(7))
    ax.grid(color="0.8")
    ax.tick_params(labelsize=6)
    ax.plot([0.3, 5.7], [5.7, 0.3], color="#b8651b", linewidth=9, alpha=0.6, solid_capstyle="round")
    pts = [(0.5 + i, 5.5 - i) for i in range(6)]
    for i in range(5):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        ax.annotate("", (x1, y0), (x0, y0), arrowprops={"arrowstyle": "->", "color": "#1f77b4", "linewidth": 1.8})
        ax.annotate("", (x1, y1), (x1, y0), arrowprops={"arrowstyle": "->", "color": "#1f77b4", "linewidth": 1.8})
        ax.annotate("", (x1 - 0.08, y1 + 0.08), (x0 + 0.08, y0 - 0.08), arrowprops={"arrowstyle": "->", "color": "#d62728", "linewidth": 1.8, "linestyle": "--"})
    ax.set_title("a track at 45 degrees (brown) across 1 mm cells:\nblue = x then y faces (staircase), red = one diagonal face", fontsize=9)
    # real faces, five-point and hybrid
    size = 10.0
    c, s_ = math.cos(math.radians(135)), math.sin(math.radians(135))             # falling to the right, the d1 direction of the array
    text = HEAD + "%ADD10C,0.3*%\nD10*\n" + f"X{mm(size / 2 - 8 * c)}Y{mm(size / 2 - 8 * s_)}D02*\nX{mm(size / 2 + 8 * c)}Y{mm(size / 2 + 8 * s_)}D01*\nM02*\n"
    layer = ng.Layer(text)
    cov = ng.render_coverage(layer, 0.0, size, size, size, 0.1, 4)
    S = cd.S_LAM + cov * (cd.S_CU - cd.S_LAM)
    gx, gy = cd.dual_faces(S, 10, 0)
    hx, hy, d1, d2 = dg.hybrid_faces(S, 10, 1.0)
    ny, nx = gx.shape[0], gy.shape[1]
    def lw(g):
        """!
        @brief Line width in points of a face: thin for the laminate, thick for a face that carries copper.
        @param g Face conductance (W/K).
        @return float Width.
        """
        return 0.3 + 16.0 * max(g - cd.S_LAM, 0.0) / (cd.S_CU - cd.S_LAM)
    for k, (title, diag) in enumerate((("a 0.3 mm track falling at 45 degrees: the flow-based faces of the five-point network\n(line width = conductance above the laminate)", False), ("the same plus the diagonal faces (red: d1, along the track)\nall the missing conduction, share 1", True))):
        ax = fig.add_subplot(gs[1, k if k == 0 else 1:3 if k == 1 else 2])
        ax.imshow(cov, extent=(0, nx, 0, ny), cmap="YlOrBr", vmin=-0.3, vmax=1.4, interpolation="nearest", alpha=0.55)
        for i in range(ny):
            for j in range(nx - 1):
                ax.plot([j + 0.5, j + 1.5], [ny - i - 0.5, ny - i - 0.5], color="#1f77b4", linewidth=lw(gx[i, j]), solid_capstyle="butt")
        for i in range(ny - 1):
            for j in range(nx):
                ax.plot([j + 0.5, j + 0.5], [ny - i - 0.5, ny - i - 1.5], color="#1f77b4", linewidth=lw(gy[i, j]), solid_capstyle="butt")
        if diag:
            for i in range(ny - 1):
                for j in range(nx - 1):
                    ax.plot([j + 0.5, j + 1.5], [ny - i - 0.5, ny - i - 1.5], color="#d62728", linewidth=lw(d1[i, j]) if d1[i, j] > 1e-9 else 0.0, solid_capstyle="butt")
                    ax.plot([j + 1.5, j + 0.5], [ny - i - 0.5, ny - i - 1.5], color="#2ca02c", linewidth=lw(d2[i, j]) if d2[i, j] > 1e-9 else 0.0, solid_capstyle="butt")
        ax.set_xlim(0, nx)
        ax.set_ylim(0, ny)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("mm (1 mm cells)")
    fig.tight_layout()
    fig.savefig(OUT / "fig_09_diagonal_faces.png", dpi=105)
    plt.close(fig)


def fig_pipeline():
    """!
    @brief The data flow of the whole Gerber research as a diagram: files, mask, conductance of the pixels, cells, mappings, the program's network and, in parallel, the nets and the electrical side, with the folder of each step.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(17, 8.2))
    ax.set_xlim(0, 17)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    cols = {"1": "#cfe3f5", "2": "#fbe3c2", "3": "#d6ecd0"}

    def box(x, y, w, h, text, phase, bold=False):
        """!
        @brief A rounded box with a text.
        @param x Left.
        @param y Bottom.
        @param w Width.
        @param h Height.
        @param text Label.
        @param phase "1", "2" or "3" (colour).
        @param bold True for a key step.
        @return None.
        """
        ax.add_patch(plt.matplotlib.patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15", facecolor=cols[phase], edgecolor="k", linewidth=2.0 if bold else 0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    def arrow(x0, y0, x1, y1, label=""):
        """!
        @brief An arrow with an optional label.
        @param x0 Start x.
        @param y0 Start y.
        @param x1 End x.
        @param y1 End y.
        @param label Text near the middle.
        @return None.
        """
        ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "->", "linewidth": 1.4})
        if label:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.18, label, ha="center", fontsize=7, style="italic")
    box(0.2, 6.0, 2.4, 1.5, "Gerber and Excellon files\n(copper layers, drills,\nX2 attributes)", "1")
    box(3.3, 6.0, 2.6, 1.5, "independent reader\nnative_gerber.py\n(NumPy only)", "1", True)
    box(6.6, 6.0, 2.8, 1.5, "MASK per layer\nbinary and coverage\n(pixel <= half the\nthinnest track)", "1", True)
    box(6.6, 3.9, 2.8, 1.5, "holes, pads, nets\n(position, aperture\nfunction, X2 nets;\nchecked on a KiCad file)", "1")
    arrow(2.6, 6.75, 3.3, 6.75)
    arrow(5.9, 6.75, 6.6, 6.75)
    arrow(4.6, 6.0, 7.0, 5.4, "")
    box(10.1, 6.0, 2.6, 1.5, "sheet conductance\nof every pixel\nS = S_lam + f (S_cu - S_lam)", "2")
    box(13.2, 6.0, 3.5, 1.5, "cut into cells (n x n pixels)\nand MAPPED to face conductances:\nfill (today), lambda 0.5,\ncell problem, flow-based faces", "2", True)
    arrow(9.4, 6.75, 10.1, 6.75)
    arrow(12.7, 6.75, 13.2, 6.75)
    box(13.2, 3.9, 3.5, 1.5, "optional: diagonal faces\n(tensor of the cell, share 0.5)\nfor diagonal tracks", "2")
    arrow(14.95, 6.0, 14.95, 5.4, "")
    box(10.1, 1.7, 3.0, 1.6, "the program's FVM network\n(faces replaced; vias,\nconvection and sources\nare the program's)", "2", True)
    arrow(14.2, 3.9, 12.6, 3.3)
    arrow(13.9, 6.0, 12.0, 3.3, "")
    box(13.9, 1.7, 2.8, 1.6, "temperatures\nof the five models,\nerror against the\npixel-by-pixel reference", "2")
    arrow(13.1, 2.5, 13.9, 2.5)
    box(3.3, 3.9, 2.8, 1.5, "net of a piece of copper\n(mask of one net)", "3")
    arrow(7.0, 4.65, 6.1, 4.65, "")
    box(3.3, 1.7, 2.8, 1.6, "current and Joule heat:\nsources, sinks, links\n(pdn.py, joule.py)", "3", True)
    arrow(4.7, 3.9, 4.7, 3.3)
    box(6.6, 1.7, 2.8, 1.6, "heat per cell\n(sums to I^2 R)\nadded as a source", "3")
    arrow(6.1, 2.5, 6.6, 2.5)
    arrow(9.4, 2.5, 10.1, 2.5, "heat source")
    ax.text(0.2, 0.9, "blue: phase 1, research/gerber-import (no program needed)     orange: phase 2, research/gerber-models     green: phase 3, research/gerber-nets (prototype)", fontsize=9)
    ax.text(0.2, 0.4, "thick boxes: the key steps. The mask is the common currency of the research: the mapping to the cells and the nets are two uses of it.", fontsize=8, style="italic")
    ax.set_title("From the Gerber file to the temperature: the whole chain and where each step lives", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_10_pipeline.png", dpi=105)
    plt.close(fig)


def fig_zone_union():
    """!
    @brief How the program combines the zones of a layer, drawn for two cases: two zones that abut (each covers half of the cell) and two zones that overlap (fill 0.5 each): the maximum per cell, the additive rule and the maximum per sample point, with the fill each gives.
    @return None.
    """
    from matplotlib.patches import Rectangle
    fig, axs = plt.subplots(2, 3, figsize=(15, 8.5))
    cases = (("two zones that abut: each covers half of the cell, fill 1", [(0.0, 0.5, 1.0), (0.5, 1.0, 1.0)], (0.5, 1.0, 1.0), 1.0),
             ("two zones that overlap: the same area, fill 0.5 each", [(0.0, 1.0, 0.5), (0.0, 1.0, 0.5)], (0.5, 1.0, 0.5), 0.5))
    methods = ("maximum per cell (the program today)", "additive rule (the first idea)", "maximum per sample point (the correction)")
    for r, (title, zones, fills, right) in enumerate(cases):
        for m, method in enumerate(methods):
            ax = axs[r, m]
            ax.set_xlim(-0.35, 2.3)
            ax.set_ylim(-0.25, 1.1)
            ax.set_aspect("equal")
            ax.axis("off")
            ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, edgecolor="k", linewidth=1.6))
            for k, (z0, z1, f) in enumerate(zones):
                ax.add_patch(Rectangle((z0, 0.04 * k), z1 - z0, 0.92, facecolor="#e0a458", alpha=0.5, edgecolor="#b8651b"))
            ok = abs(fills[m] - right) < 1e-9
            ax.add_patch(Rectangle((1.5, 0), 0.6, fills[m], facecolor="#2ca02c" if ok else "#d62728", edgecolor="k"))
            ax.add_patch(Rectangle((1.5, 0), 0.6, right, fill=False, edgecolor="k", linestyle="--"))
            ax.text(1.8, -0.15, f"cell fill {fills[m]:.1f}" + ("" if ok else "  (wrong)"), ha="center", fontsize=9)
            if r == 0:
                ax.set_title(method, fontsize=9)
            if m == 0:
                ax.text(-0.12, 0.5, title.replace(": ", ":\n"), fontsize=8, va="center", ha="right", rotation=90, transform=ax.transData)
    fig.suptitle("how the zones of a layer are combined cell by cell (dashed: the right fill); the per-sample rule is right in both cases", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig_11_zone_union.png", dpi=105)
    plt.close(fig)


def fig_clearance_cell():
    """!
    @brief What the copper fraction hides: one cell of 10 x 10 pixels with a clearance across it and a narrow neck, and the conductance along x that each mapping gives it.
    @return None.
    """
    n = 10
    mask = np.ones((n, n), bool)
    mask[:, 4:6] = False
    mask[4:6, 4:6] = True
    S = cd.S_LAM + mask * (cd.S_CU - cd.S_LAM)
    blk = S[None, None, :, :]
    f = float(mask.mean())
    fill = float(cd.map_power(np.array([[f]]), 1.0, cd.S_CU, cd.S_LAM)[0, 0])
    lo, up = float(cd.map_bounds(blk)[0][0, 0]), float(cd.map_bounds(blk)[2][0, 0])
    lam, cp = float(cd.map_lambda(blk, 0.5)[0][0, 0]), float(cd.map_cell_problem(blk)[0][0, 0])
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1, 1.6]})
    axs[0].imshow(mask, cmap="YlOrBr", vmin=-0.3, vmax=1.3, interpolation="nearest")
    axs[0].set_title(f"one 1 mm cell (10 x 10 pixels): copper brown, a 0.2 mm clearance\nacross it with a 0.2 mm neck; copper fraction {f:.2f}", fontsize=9)
    axs[0].set_xlabel("heat flows left to right and has to pass through the neck")
    axs[0].set_xticks([])
    axs[0].set_yticks([])
    names = ["fill fraction\n(the program today)", "Wiener low\n(a bound)", "lambda 0.5", "cell problem", "Wiener up\n(a bound)"]
    vals = [fill, lo, lam, cp, up]
    axs[1].bar(names, [v / cd.S_LAM for v in vals], color=["#d62728", "#999999", "#1f77b4", "#1f77b4", "#999999"])
    for i, v in enumerate(vals):
        axs[1].text(i, v / cd.S_LAM + 0.1, f"{v / cd.S_LAM:.1f}", ha="center", fontsize=9)
    axs[1].set_ylabel("conductance along x of the cell\n(in units of the laminate's)")
    axs[1].set_title("what each mapping says: the fill fraction averages the copper as if it were joined,\nthe others see the neck. Too high a conductance means too cool a board:\nthat is the bias of the fill fraction on real copper", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_12_clearance_cell.png", dpi=105)
    plt.close(fig)


def _flow_window(mask):
    """!
    @brief Heat conduction across one square window of the copper mask: potential 1 on the left edge, 0 on the right, no flow through the top and bottom, pixel faces with the harmonic mean of the two sheet conductances (the local problem of the flow-based faces).
    @param mask Boolean array (rows, cols), True = copper.
    @return Tuple (potential, flux x, flux y at the pixel centres, effective sheet conductance of the window in W/K).
    """
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    n, m = mask.shape
    S = cd.sheet_of(mask)
    idx = np.arange(n * m).reshape(n, m)
    gx = 2 * S[:, :-1] * S[:, 1:] / (S[:, :-1] + S[:, 1:])
    gy = 2 * S[:-1, :] * S[1:, :] / (S[:-1, :] + S[1:, :])
    rows, cols, vals = [], [], []
    for a, b, g in ((idx[:, :-1], idx[:, 1:], gx), (idx[:-1, :], idx[1:, :], gy)):
        a, b, g = a.ravel(), b.ravel(), g.ravel()
        rows += [a, b, a, b]
        cols += [a, b, b, a]
        vals += [g, g, -g, -g]
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n * m, n * m))
    fixed = np.zeros((n, m), bool)
    fixed[:, 0] = fixed[:, -1] = True
    v = np.zeros((n, m))
    v[:, 0] = 1.0
    free = ~fixed.ravel()
    rhs = -K[:, ~free] @ v.ravel()[~free]
    sol = spla.spsolve(K[free][:, free].tocsc(), rhs[free])
    v = v.ravel()
    v[free] = sol
    v = v.reshape(n, m)
    qx = np.zeros((n, m))
    qy = np.zeros((n, m))
    fx = gx * (v[:, :-1] - v[:, 1:])
    fy = gy * (v[:-1, :] - v[1:, :])
    qx[:, :-1] += fx / 2
    qx[:, 1:] += fx / 2
    qy[:-1, :] += fy / 2
    qy[1:, :] += fy / 2
    return v, qx, -qy, float(fx[:, 0].sum())


def fig_cell_flow():
    """!
    @brief What the flow-based face conductance looks at: heat crossing a window of three copper patterns (stripes across the flow, stripes along it, a bar with a clearance), with the heat-flow lines and the effective conductance next to the fill-fraction average.
    @return None.
    """
    n = 60
    across = np.zeros((n, n), bool)
    for k in range(6):
        across[:, 10 * k + 2:10 * k + 7] = True
    along = np.zeros((n, n), bool)
    for k in range(6):
        along[10 * k + 2:10 * k + 7, :] = True
    detour = np.zeros((n, n), bool)
    detour[22:38, :] = True
    detour[:, 28:32] = False
    detour[28:32, 28:32] = True                      # a clearance across the bar with a thin neck left in it
    cases = (("stripes across the heat flow", across), ("stripes along the heat flow", along), ("a bar cut by a clearance with a thin neck", detour))
    fig, axs = plt.subplots(1, 3, figsize=(15, 6.4))
    for ax, (title, mask) in zip(axs, cases):
        v, qx, qy, s_eff = _flow_window(mask)
        f = mask.mean()
        s_fill = f * cd.S_CU + (1 - f) * cd.S_LAM
        s_geo = cd.S_CU ** f * cd.S_LAM ** (1 - f)
        mag = np.hypot(qx, qy)
        green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
        ax.imshow(np.where(mask[..., None], gold, green), extent=(0, n, 0, n))
        grid = np.arange(n) + 0.5
        # the width of a line follows the heat flux in that pixel, so the heat is seen going where the copper is
        ax.streamplot(grid, grid, qx[::-1], qy[::-1], color="white", density=1.6, linewidth=2.2 * (mag[::-1] / mag.max()) ** 0.5 + 0.2, arrowsize=0.8)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.set_xlabel(f"copper fraction {f:.2f}\nheat actually crosses with S = {s_eff * 1e3:.2f} mW/K\nfill fraction would say {s_fill * 1e3:.2f} ({s_fill / s_eff:.1f} x), geometric mean {s_geo * 1e3:.2f} ({s_geo / s_eff:.1f} x)", fontsize=8)
    fig.suptitle("What the flow-based face conductance computes: heat crossing a window (hot on the left, cold on the right; white lines: heat flow, thicker where more heat passes)", fontsize=10)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    fig.savefig(OUT / "fig_18_cell_flow_lines.png", dpi=110)
    plt.close(fig)


def fig_diagonal_gate():
    """!
    @brief The detector of the cells that get diagonal faces: on a real window, the copper, the coherence of every 1 mm cell (cross term of the cell tensor over its mean conductance) and the share of diagonal conduction the gate gives it; then the results of the gates on the 42 windows and on the tracks.
    @return None.
    """
    import json
    import diagonal as dg
    windows.BOARDS = ["storm"]                                          # Stormduino (MIT): the only board whose licence allows a picture of it
    windows.FILE = windows.OUT / "windows_storm.npz"
    masks, meta = windows.load()
    mask = masks[1]
    S = cd.sheet_of(mask[::-1])
    kxx, kyy, kxy = dg.cell_tensor(S, 10)
    rho = np.abs(kxy) / (0.5 * (kxx + kyy))
    gate = np.clip((rho - 0.05) / 0.20, 0, 1)
    res = json.loads((CACHE / "diagonal_gate.json").read_text())
    fig = plt.figure(figsize=(16, 9.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 0.9])
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(mask, cmap="copper", interpolation="nearest", extent=(0, 36, 0, 36))
    ax.set_title("Stormduino (MIT): 36 x 36 mm of real copper", fontsize=9)
    ax = fig.add_subplot(gs[0, 1])
    im = ax.imshow(rho[::-1], cmap="magma", vmin=0, vmax=0.5, interpolation="nearest", extent=(0, 36, 0, 36))
    ax.set_title("coherence of each 1 mm cell: |kxy| / mean(kxx, kyy)\n(0: uniform, crossing or axis-aligned; high: one diagonal conductor)", fontsize=9)
    fig.colorbar(im, ax=ax)
    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(mask, cmap="copper", interpolation="nearest", extent=(0, 36, 0, 36), alpha=0.55)
    ys, xs = np.nonzero(gate[::-1] > 0)
    ax.scatter(xs + 0.5, ys + 0.5, s=18 + 60 * gate[::-1][ys, xs], c=gate[::-1][ys, xs], cmap="cool", vmin=0, vmax=1, edgecolors="k", linewidths=0.3)
    ax.set_title(f"cells that get diagonal faces (gate > 0): {int((gate > 0).sum())} of {gate.size}\ncolour and size: the share of the missing diagonal conduction added", fontsize=9)
    for a in fig.axes[:3]:
        a.set_xlabel("mm")
    ax = fig.add_subplot(gs[1, 0])
    b = res["b"]
    names = list(b)
    mae = [np.mean(np.abs(b[m])) for m in names]
    ax.barh(range(len(names)), mae, color=["#9bbf8a" if "coherence" in m or "ramp" in m else "#c9c9c9" for m in names])
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels([m.replace("coherence ramp", "ramp") for m in names], fontsize=7.5)
    ax.invert_yaxis()
    for i, m in enumerate(names):
        ax.text(mae[i], i, f"  {mae[i]:.2f} (bias {np.mean(b[m]):+.2f})", va="center", fontsize=7.5)
    ax.set_xlabel("mean absolute error of the heater rise, 42 real windows (%)")
    ax.set_title("42 real windows against the nine-point pixel reference", fontsize=9)
    ax.set_xlim(0, max(mae) * 1.6)
    ax = fig.add_subplot(gs[1, 1:])
    a_ = res["a"]
    widths = sorted({float(k.split("/")[0]) for k in a_})
    for m, colour in (("flow-based, no diagonals", "#7f7f7f"), ("fixed 1.0", "#d62728"), ("fixed 0.5", "#ff7f0e"), ("coherence ramp 0.05 to 0.25", "#2ca02c"), ("coherence ramp 0.10 to 0.40", "#1f77b4")):
        ax.plot(widths, [a_[f"{w}/45"][m] for w in widths], "o-", color=colour, label=m, linewidth=1.6)
    ax.axhline(100, color="k", linewidth=0.8, linestyle="--")
    ax.set_xscale("log")
    ax.set_xlabel("track width (mm)")
    ax.set_ylabel("share of the track's cooling reproduced (%)")
    ax.set_title("a track at 45 degrees (the gates leave the 0 degree results unchanged); 100 % is right", fontsize=9)
    ax.legend(fontsize=7.5)
    fig.suptitle("A detector for the diagonal faces: the cell's own conductance tensor decides where they are added (README 4.48)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig_19_diagonal_gate.png", dpi=105)
    plt.close(fig)


def _cell_field(mask):
    """!
    @brief The heat flux in a cell of copper when the potential on the whole boundary of the cell is x (an affine boundary condition, the condition the cell tensor is built from): pixel faces with the harmonic mean of the sheet conductances, five-point stencil.
    @param mask Boolean array (rows, cols), True = copper.
    @return tuple (qx, qy) heat flux per pixel, qx along the columns, qy upwards.
    """
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    n, m = mask.shape
    S = cd.sheet_of(mask)
    idx = np.arange(n * m).reshape(n, m)
    gx = 2 * S[:, :-1] * S[:, 1:] / (S[:, :-1] + S[:, 1:])
    gy = 2 * S[:-1, :] * S[1:, :] / (S[:-1, :] + S[1:, :])
    rows, cols, vals = [], [], []
    for a, b, g in ((idx[:, :-1], idx[:, 1:], gx), (idx[:-1, :], idx[1:, :], gy)):
        a, b, g = a.ravel(), b.ravel(), g.ravel()
        rows += [a, b, a, b]
        cols += [a, b, b, a]
        vals += [g, g, -g, -g]
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n * m, n * m))
    ring = np.zeros((n, m), bool)
    ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
    v = np.where(ring, np.tile(np.arange(m, dtype=float), (n, 1)), 0.0).ravel()
    free = ~ring.ravel()
    rhs = -K[:, ~free] @ v[~free]
    v[free] = spla.spsolve(K[free][:, free].tocsc(), rhs[free])
    v = v.reshape(n, m)
    qx = np.zeros((n, m))
    qy = np.zeros((n, m))
    fx = gx * (v[:, :-1] - v[:, 1:])
    fy = gy * (v[:-1, :] - v[1:, :])
    qx[:, :-1] += fx / 2
    qx[:, 1:] += fx / 2
    qy[:-1, :] += fy / 2
    qy[1:, :] += fy / 2
    return qx, -qy


def _tensor_cells(n=40, pix=0.025):
    """!
    @brief Four 1 mm cells at 0.025 mm pixels: a track at 45 degrees, a track along x, two crossing diagonals and a copper plane with a round clearance, with their cell tensors.
    @param n Pixels per cell side.
    @param pix Pixel size (mm).
    @return list of (title, mask, (kxx, kyy, kxy) as multiples of the sheet conductance of copper).
    """
    import diagonal as dg
    y, x = np.mgrid[0:n, 0:n]
    xc, yc = (x + 0.5) * pix, (y + 0.5) * pix
    w = 0.2
    diag1 = np.abs((xc - 0.5) - (yc - 0.5)) / np.sqrt(2) <= w / 2
    diag2 = np.abs((xc - 0.5) + (yc - 0.5)) / np.sqrt(2) <= w / 2
    along = np.abs(yc - 0.5) <= w / 2
    plane = np.hypot(xc - 0.5, yc - 0.5) > 0.22
    out = []
    for title, m in (("a track at 45 degrees", diag1), ("a track along x", along), ("two crossing diagonals", diag1 | diag2), ("a plane with a round clearance", plane)):
        kxx, kyy, kxy = dg.cell_tensor(cd.sheet_of(m), n)
        out.append((title, m, tuple(float(v[0, 0] / cd.S_CU) for v in (kxx, kyy, kxy))))
    return out


def fig_mapping_curves():
    """!
    @brief The mapping formulas explained: the cell conductance (in laminates) against the copper fraction for the arithmetic mean (fill fraction), the geometric mean, the harmonic mean, Bruggeman and the Hashin-Shtrikman bounds, with the numerical cell problem of four arrangements of the same fraction (stripes along and across the flow, checkerboard, random) as points, and the four arrangements drawn.
    @return None.
    """
    n = 20
    f = np.linspace(0.02, 0.98, 97)
    sc_, sl_ = cd.S_CU, cd.S_LAM
    fig = plt.figure(figsize=(15, 6.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[2.6, 0.9, 0.9, 0.0001], wspace=0.25, hspace=0.35)
    ax = fig.add_subplot(gs[:, 0])
    ref = sl_
    ax.semilogy(f, cd.map_power(f, 1) / ref, color="#d62728", lw=2, label="arithmetic = fill fraction (today)")
    ax.semilogy(f, cd.map_power(f, 0) / ref, color="#1f77b4", lw=1.6, label="geometric mean")
    ax.semilogy(f, cd.map_power(f, -1) / ref, color="#2ca02c", lw=1.6, label="harmonic mean")
    ax.semilogy(f, cd.map_bruggeman(f) / ref, "k--", lw=1.4, label="Bruggeman (random mixture)")
    ax.fill_between(f, cd.map_hashin_shtrikman(f, "lower") / ref, cd.map_hashin_shtrikman(f, "upper") / ref, color="grey", alpha=0.25, label="Hashin-Shtrikman bounds")
    rng = np.random.default_rng(3)
    pats = {}
    fs = [0.15, 0.3, 0.5, 0.7, 0.85]
    marks = {"along": ("^", "#d62728"), "across": ("v", "#2ca02c"), "checker": ("s", "#1f77b4"), "random": ("o", "k")}
    pts = {k: [] for k in marks}
    for fr in fs:
        w = int(round(fr * n))
        al = np.zeros((n, n), bool); al[:w, :] = True                  # stripes along x: rows of copper in parallel
        ac = np.zeros((n, n), bool); ac[:, :w] = True                  # stripes across x: copper and laminate in series
        ck = (np.add.outer(np.arange(n) // 2, np.arange(n) // 2) % 2 == 0)
        rd = rng.random((n, n)) < fr
        for key, m in (("along", al), ("across", ac), ("checker", ck), ("random", rd)):
            S = np.where(m, sc_, sl_)[None]
            sx, _ = cd.map_cell_problem(S.reshape(1, 1, n, n))
            pts[key].append((m.mean(), float(sx[0, 0]) / ref))
            if fr == 0.5:
                pats[key] = m
    for key, (mk, col) in marks.items():
        xs, ys = zip(*pts[key])
        ax.plot(xs, ys, mk, color=col, ms=7, mfc="none", mew=1.6, label=f"cell problem: {key}")
    ax.set_xlabel("copper fraction of the cell")
    ax.set_ylabel("cell conductance for flow along x (laminates)")
    ax.set_title("one number per cell from the fraction alone, against the cell problem", fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    ax.grid(alpha=0.3, which="both")
    for i, key in enumerate(("along", "across", "checker", "random")):
        a2 = fig.add_subplot(gs[i // 2, 1 + i % 2])
        a2.imshow(pats[key], cmap="copper", interpolation="nearest")
        a2.set_xticks([]); a2.set_yticks([])
        a2.annotate("", (n - 0.5, -2.2), (-0.5, -2.2), arrowprops={"arrowstyle": "->", "color": "#d62728"}, annotation_clip=False)
        a2.set_title(f"{key} (f = 0.5; orange = copper)" + ("\ncorners only touch" if key == "checker" else ""), fontsize=7.5, color=marks[key][1])
    fig.suptitle("The mapping formulas: the fraction alone cannot tell the arrangements apart, the cell problem can (README 4.4)", fontsize=10)
    fig.subplots_adjust(top=0.86, bottom=0.1, left=0.06, right=0.97)
    fig.savefig(OUT / "fig_22_mapping_formulas.png", dpi=105)
    plt.close(fig)


def fig_cell_tensor():
    """!
    @brief What the cell tensor is: four 1 mm cells with the heat flux inside them when the boundary potential is x, and each cell's conductance ellipse (axes: the eigenvalues of the tensor, orientation: the principal direction) with its coherence.
    @return None.
    """
    from matplotlib.patches import Ellipse
    cells = _tensor_cells()
    fig, axs = plt.subplots(2, 4, figsize=(16, 8.2), gridspec_kw={"height_ratios": [1.1, 1]})
    for j, (title, mask, (kxx, kyy, kxy)) in enumerate(cells):
        qx, qy = _cell_field(mask)
        green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
        ax = axs[0, j]
        ax.imshow(np.where(mask[..., None], gold, green), extent=(0, 1, 0, 1), origin="upper")
        step = 3
        yy, xx = np.mgrid[0:mask.shape[0]:step, 0:mask.shape[1]:step]
        mag = np.hypot(qx, qy)
        sel = (slice(None, None, step), slice(None, None, step))
        scale = mag.max()
        ax.quiver((xx + 0.5) / mask.shape[1], 1 - (yy + 0.5) / mask.shape[0], (qx[sel] / scale), (qy[sel] / scale), color="white", scale=22, width=0.004, headwidth=3.5, pivot="mid")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(title, fontsize=9.5, fontweight="bold")
        ax.set_xlabel(f"kxx {kxx:.3f}   kyy {kyy:.3f}   kxy {kxy:+.3f}  (x S_Cu)", fontsize=8.5)
        # the conductance ellipse: half axes proportional to the eigenvalues of [[kxx, kxy], [kxy, kyy]]
        a2 = axs[1, j]
        T = np.array([[kxx, kxy], [kxy, kyy]])
        lam, vec = np.linalg.eigh(T)
        ang = np.degrees(np.arctan2(vec[1, 1], vec[0, 1]))
        coh = abs(kxy) / (0.5 * (kxx + kyy))
        a2.add_patch(Ellipse((0, 0), 2 * max(lam[1], 1e-3), 2 * max(lam[0], 1e-3), angle=-ang, facecolor="#9bbf8a", edgecolor="k", alpha=0.85))
        a2.add_patch(plt.Circle((0, 0), 0.5 * (kxx + kyy), fill=False, linestyle="--", edgecolor="grey"))
        a2.axhline(0, color="k", linewidth=0.6)
        a2.axvline(0, color="k", linewidth=0.6)
        a2.set_xlim(-1.05, 1.05)
        a2.set_ylim(-1.05, 1.05)
        a2.set_aspect("equal")
        a2.set_xticks([])
        a2.set_yticks([])
        a2.set_xlabel(f"eigenvalues {lam[1]:.3f}, {lam[0]:.3f}; principal axis {ang % 180:.0f} deg (y down)\ncoherence |kxy| / mean(kxx, kyy) = {coh:.2f}", fontsize=8.5)
    axs[0, 0].set_ylabel("heat flux inside the cell\n(boundary potential = x:\nthe gradient points along x)", fontsize=8.5)
    axs[1, 0].set_ylabel("conductance ellipse\n(dashed: a uniform cell of\nthe same mean)", fontsize=8.5)
    fig.suptitle("The cell tensor: how a cell of real copper conducts heat in x, in y and across (white arrows: the heat flux when the potential on the boundary is x; a track at 45 degrees sends the heat along itself, not along the gradient)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94), h_pad=3.5)
    fig.savefig(OUT / "fig_20_cell_tensor.png", dpi=105)
    plt.close(fig)


def fig_tensor_in_use():
    """!
    @brief How the tensor is used: the nine-point stencil it gives to a cell with a 45-degree track (axial links kxx - |kxy|, kyy - |kxy| and a diagonal link |kxy|), and the temperature of a 6 mm heater over a 0.2 mm track at 45 degrees on 1 mm cells with the five-point network, with the gated nine-point network, and the resolved reference.
    @return None.
    """
    import diagonal as dg
    import scenarios as sc
    import study_diagonal_gate as sg
    import study_track_width_angle as st
    cells = _tensor_cells()
    kxx, kyy, kxy = cells[0][2]
    fig = plt.figure(figsize=(17, 9.2))
    gs = fig.add_gridspec(2, 5, height_ratios=[1, 1], width_ratios=[1, 1, 1, 1, 0.04], hspace=0.5, wspace=0.28, left=0.03, right=0.97, top=0.9, bottom=0.07)
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlim(-0.4, 2.4)
    ax.set_ylim(-0.6, 2.4)
    ax.set_aspect("equal")
    ax.axis("off")
    xs, ys = np.meshgrid([0, 1, 2], [0, 1, 2])
    cx_, cy_, dd = kxx - abs(kxy), kyy - abs(kxy), abs(kxy)
    for i in range(3):
        for j in range(3):
            if i < 2:
                ax.plot([i, i + 1], [j, j], color="#1f77b4", linewidth=1 + 14 * cx_ / (kxx + 1e-9))
            if j < 2:
                ax.plot([i, i], [j, j + 1], color="#1f77b4", linewidth=1 + 14 * cy_ / (kyy + 1e-9))
            if i < 2 and j < 2:
                ax.plot([i, i + 1], [j + 1, j], color="#d62728", linewidth=1 + 14 * dd / (kxx + 1e-9), alpha=0.9)       # copper runs from top left to bottom right
    ax.scatter(xs.ravel(), ys.ravel(), s=70, color="k", zorder=3)
    ax.text(1.0, -0.35, f"axial links: kxx - |kxy| = {cx_:.3f}, kyy - |kxy| = {cy_:.3f}\ndiagonal link: |kxy| = {dd:.3f}   (x S_Cu)\n(the track of the experiment runs the other way:\nthe other diagonal pair)", ha="center", va="top", fontsize=8)
    ax.set_title("the stencil of a cell with a 45-degree track:\nblue axial links, red diagonal link", fontsize=9, fontweight="bold")
    ax = fig.add_subplot(gs[1, 0])
    ax.axis("off")
    ax.text(0.0, 1.0, "how the tensor becomes links\n\nflux q = - K grad(u), K = [[kxx, kxy], [kxy, kyy]]\nthe five-point network only has kxx and kyy:\nheat that follows a diagonal track has to\nzigzag through x and y faces, and each face is\nshort of the real conduction\n\nthe nine-point stencil adds the diagonal link:\naxial = kxx - |kxy|, kyy - |kxy|, diagonal = |kxy|\n(the standard stencil of kxx uxx + kyy uyy + 2 kxy uxy)", va="top", fontsize=8.8)
    # the experiment: a 6 mm heater on a track at 45 degrees on a 16 mm window
    layer = st.ng.Layer(st.track_text(0.2, 45))
    _, ct = st.masks(layer, st.PIX_TRUTH)
    Sc = st.sheet(ct)
    p_t, f_t, h_t = sc.box_scenario(Sc.shape, st.PIX_TRUTH, 6.0)
    Tref = dg.pixel_reference9(Sc, st.PIX_TRUTH, p_t, 10.0, f_t)
    nref = int(round(1.0 / st.PIX_TRUTH))
    ref_cells = Tref.reshape(Tref.shape[0] // nref, nref, Tref.shape[1] // nref, nref).mean(axis=(1, 3))
    _, c01 = st.masks(layer, 0.1)
    S = st.sheet(c01)
    p0, f0, h0 = sc.box_scenario(S.shape, 0.1, 6.0)
    n = 10
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = p0[:cy * n, :cx * n].reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(f0, n).mean(axis=(2, 3)) >= 0.5
    gx, gy = cd.dual_faces(S, n, 0)
    T5 = dg.solve9(*dg.faces5_as9(gx, gy), 0.1 * n, pw, 10.0, fx)
    Tg = dg.solve9(*dg.hybrid_faces(S, n, gate=sg.GATES["coherence ramp 0.05 to 0.25"]), 0.1 * n, pw, 10.0, fx)
    y0, y1, x0, x1 = h0[0] // n, h0[1] // n, h0[2] // n, h0[3] // n
    mean = lambda T: T[y0:y1, x0:x1].mean()
    # the temperature the heater would have without the track, for the coarse network and for the fine reference: how much of the track's cooling each reproduces (as in study_diagonal_gate.py)
    S0 = np.full(S.shape, cd.S_LAM)
    gx0, gy0 = cd.dual_faces(S0, n, 0)
    T0 = dg.solve9(*dg.faces5_as9(gx0, gy0), 0.1 * n, pw, 10.0, fx)
    Tref0 = dg.pixel_reference9(np.full(Sc.shape, cd.S_LAM), st.PIX_TRUTH, p_t, 10.0, f_t)
    ref_effect = 1 - Tref[h_t[0]:h_t[1], h_t[2]:h_t[3]].mean() / Tref0[h_t[0]:h_t[1], h_t[2]:h_t[3]].mean()
    vmax = float(ref_cells.max())
    for k, (T, name) in enumerate(((ref_cells, "resolved reference (0.025 mm pixels, nine-point)"), (T5, "1 mm cells, five-point network"), (Tg, "1 mm cells, nine-point with the gate"))):
        a = fig.add_subplot(gs[0, k + 1])
        im = a.imshow(T, cmap="inferno", vmin=0, vmax=vmax, extent=(0, 16, 0, 16), interpolation="nearest")
        a.add_patch(plt.Rectangle((5, 5), 6, 6, fill=False, edgecolor="cyan", linewidth=1.2))
        a.plot([0, 16], [0, 16], "--", color="white", linewidth=0.9, alpha=0.8)                      # the track (0.2 mm wide, 45 degrees)
        share = 100 * (1 - mean(T) / mean(T0)) / ref_effect
        a.set_title(f"{name}\nmean rise under the heater {mean(T):.1f} K", fontsize=9)
        a.set_xlabel(f"share of the track's cooling reproduced: {share:.0f} %" if k else "mm", fontsize=8.5)
        a.contour(np.linspace(0, 16, T.shape[1]) + 0, np.linspace(16, 0, T.shape[0]) + 0, T, levels=6, colors="white", linewidths=0.4)
    fig.colorbar(im, cax=fig.add_subplot(gs[0, 4]), label="temperature rise (K)")
    ax = fig.add_subplot(gs[1, 1:4])
    d5, dg9 = T5 - ref_cells, Tg - ref_cells
    lim = max(abs(d5).max(), abs(dg9).max())
    xs_ = np.arange(cx) + 0.5
    ax.plot(xs_, np.diag(ref_cells[::-1]), "k-", linewidth=2, label="reference, along the diagonal (the track)")
    ax.plot(xs_, np.diag(T5[::-1]), "o-", color="#d62728", label="five-point network")
    ax.plot(xs_, np.diag(Tg[::-1]), "s-", color="#2ca02c", label="nine-point with the gate")
    ax.set_xlabel("position along the track's diagonal (1 mm cells)")
    ax.set_ylabel("temperature rise (K)")
    ax.set_title("temperature along the track: the track is a heat path; the five-point network misses it (red), the nine-point stencil with the gate follows the reference", fontsize=8.8)
    ax.legend(fontsize=8)
    fig.suptitle("How the cell tensor is used: it gives each cell diagonal links, and a heater over a diagonal track is cooled the way the real copper cools it (README 4.49)", fontsize=10)
    fig.savefig(OUT / "fig_21_tensor_in_use.png", dpi=105)
    plt.close(fig)
    print("tensor in use: mean rise reference %.2f, five-point %.2f, gated %.2f, no track %.2f; track effect in the reference %.1f %%" % (mean(ref_cells), mean(T5), mean(Tg), mean(T0), 100 * ref_effect))


def fig_diagonal_heldout():
    """!
    @brief The held-out test of the diagonal gate: the mean absolute error of every variant on 60 new windows at three cell sizes, on the layers of the Allegro board, and the share of the cooling of a tilted track reproduced at 15, 30, 60 and 75 degrees.
    @return None.
    """
    import json
    d = json.loads((CACHE / "diagonal_heldout.json").read_text())
    names = ["flow-based, no diagonals", "fixed 1.0", "fixed 0.5", "coherence ramp 0.05 to 0.25", "coherence ramp 0.10 to 0.40"]
    labels = ["no diagonals", "fixed 1.0", "fixed 0.5", "gate 0.05 to 0.25", "gate 0.10 to 0.40"]
    cols = ["#7f7f7f", "#d62728", "#ff9896", "#1f77b4", "#aec7e8"]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.0), gridspec_kw={"width_ratios": [1.3, 0.8, 1.1]})
    ax = axs[0]
    sizes = ["5", "10", "20"]
    w = 0.16
    for k, nm in enumerate(names):
        ys = [np.mean([abs(x[1]) for x in d["windows"][sz][nm]]) for sz in sizes]
        ax.bar(np.arange(3) + (k - 2) * w, ys, w, color=cols[k], label=labels[k])
    ax.set_xticks(range(3)); ax.set_xticklabels(["0.5 mm cells", "1.0 mm (the size it was chosen at)", "2.0 mm cells"], fontsize=8)
    ax.set_ylabel("mean absolute error of the heater rise (%)")
    ax.set_title("60 new windows (42 of the same boards, 18 of an unused board)", fontsize=9); ax.legend(fontsize=7.5); ax.grid(alpha=0.3, axis="y")
    ax = axs[1]
    for k, nm in enumerate(names):
        e = [x[1] for x in d["windows"]["10"][nm] if x[0].startswith("alleg")]
        ax.bar(k, np.mean(np.abs(e)), color=cols[k])
    ax.set_xticks(range(5)); ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=7.5)
    ax.set_title("only the Allegro layers (never used), 1 mm", fontsize=9); ax.grid(alpha=0.3, axis="y")
    ax = axs[2]
    angs = ["15", "30", "60", "75"]
    for k, nm in enumerate(names):
        ys = [np.mean([d["tracks"][f"{wd}/{a}"][nm] for wd in (0.15, 0.2, 0.3)]) for a in angs]
        ax.plot(angs, ys, "o-", color=cols[k], label=labels[k])
    ax.axhline(100, color="k", lw=0.6, ls=":")
    ax.set_xlabel("track angle (degrees)"); ax.set_ylabel("share of the track's cooling reproduced (%)")
    ax.set_title("tilted tracks of 0.15 to 0.3 mm (angles the gate never saw)", fontsize=9); ax.grid(alpha=0.3)
    fig.suptitle("Held-out test of the diagonal gate (README 4.50): the gain seen on the 42 windows does not carry over", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig_24_diagonal_heldout.png", dpi=105)
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
    fig_diagonal()
    fig_diagonal_faces()
    fig_pipeline()
    fig_zone_union()
    fig_clearance_cell()
    fig_cell_flow()
    fig_diagonal_gate()
    fig_mapping_curves()
    fig_cell_tensor()
    fig_tensor_in_use()
    fig_diagonal_heldout()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
