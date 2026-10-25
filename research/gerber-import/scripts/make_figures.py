"""!
@file make_figures.py
@brief The data figures of phase 1 (figures 1 to 5 and 9 to 15): our IC board, the validation summary, the Stormduino nets, the mask, the reader, the four tools pixel by pixel, the KiCad nets pixel by pixel and the board outline.
@details Figures are committed on purpose (the README files link to them); the caches they read are in out/ and are made by the studies. Run: .venv/bin/python research/gerber-import/scripts/make_figures.py (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import native_gerber as ng
import our_board

from paths import FIGURES as OUT, OUT as CACHE                           # kept in the repository on purpose: the README files link to them


def fig_gerber_render():
    """!
    @brief The Gerber of our IC board drawn like a Gerber viewer shows it: copper on the board, plated holes, net names at the test points, and a close-up of the IC with its pads and thermal vias (0.0125 mm pixels).
    @return None.
    """
    layer = ng.Layer(our_board.gerber_text())
    green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
    fig, axs = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.0, 1.0]})
    for ax, (x0, y0, size, pix) in zip(axs, ((0.0, 0.0, our_board.SIZE, 0.025), (14.0, 14.0, 12.0, 0.0125))):
        cv = ng.Canvas(x0, y0 + size, size, size, pix)
        layer.draw(cv)
        img = np.where(cv.mask[..., None], gold, green)
        ax.imshow(img, extent=(x0, x0 + size, y0, y0 + size), interpolation="nearest")
        for x, y, d in our_board.holes():
            if x0 - 1 < x < x0 + size + 1 and y0 - 1 < y < y0 + size + 1:
                ax.add_patch(plt.Circle((x, y), d / 2.0, facecolor="#101010", edgecolor="none"))
        ax.set_xlim(x0, x0 + size)
        ax.set_ylim(y0, y0 + size)
        ax.set_xlabel("mm")
    for k in range(our_board.N_SIG):
        x, y = our_board.end_point(k)
        axs[0].annotate(our_board.net_name(k), (x, y), textcoords="offset points", xytext=(5, 5), color="w", fontsize=8)
        px, py = our_board.ic_pad(k)
        axs[1].annotate(our_board.net_name(k), (px, py), textcoords="offset points", xytext=(6, 6), color="w", fontsize=8)
    axs[0].annotate("GND ring and spoke", (1.0, 1.0), color="w", fontsize=8)      # in the corner: on the ring the white text overlapped the copper
    axs[0].set_title("our IC board as a Gerber viewer would draw it: copper (gold), plated holes (black), 40 x 40 mm", fontsize=9)
    axs[1].set_title("close-up of the IC: exposed pad with four thermal vias and eight pads (12 x 12 mm)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_gerber_render.png", dpi=110)
    plt.close(fig)


def fig_validation():
    """!
    @brief The validation summary (needs out/validation_boards.json from study_validation_boards.py and out/compare_synthetic.txt from compare_readers.py): the area error of the readers on files of known area, and of our reader on every copper layer of the eight boards.
    @return None.
    """
    import json
    import re
    jp, cp = CACHE / "validation_boards.json", CACHE / "compare_synthetic.txt"
    if not (jp.exists() and cp.exists()):
        print("figure 02 skipped: run study_validation_boards.py and compare_readers.py first")
        return
    rows = json.loads(jp.read_text())
    tools = ["native", "gerbonara vector", "gerbonara sampled", "pygerber cleaned >50%", "pcb-tools >50%"]
    acc = {p: {t: [] for t in tools} for p in ("0.1", "0.05", "0.025")}
    for line in cp.read_text().splitlines():                               # the summary table of compare_readers.py (means over the 14 files, unrounded)
        for t in tools:
            if line.startswith(t + " ") and "%" in line:
                vals = re.findall(r"([\d.]+) % \(", line[len(t):])
                for p, v in zip(("0.1", "0.05", "0.025"), vals):
                    acc[p][t].append(float(v))
    fig, axs = plt.subplots(1, 3, figsize=(17, 4.8), gridspec_kw={"width_ratios": [1, 1.5, 0.8]})
    x = np.arange(3)
    for k, t in enumerate(tools):
        axs[0].bar(x + (k - 2) * 0.16, [np.mean(acc[p][t]) if acc[p][t] else np.nan for p in ("0.1", "0.05", "0.025")], 0.16, label=t)
    axs[0].set_yscale("log")                                               # log, not symlog: the vector area (0.01 %) must stay visible
    axs[0].set_ylim(0.005, 60)
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(["0.1 mm", "0.05 mm", "0.025 mm"])
    axs[0].set_xlabel("pixel")
    axs[0].set_ylabel("mean absolute area error (%)")
    axs[0].set_title("14 files of known area (binary masks):\nthe error is the pixel, not the reader", fontsize=9)
    axs[0].legend(fontsize=6)
    lab = [f"{r['board']} {r['layer']}" for r in rows]
    xx = np.arange(len(rows))
    for k, (key, name) in enumerate((("err_bin_0.1", "binary 0.1 mm"), ("err_bin_0.05", "binary 0.05 mm"), ("err_cov_0.1", "coverage 0.1 mm"))):
        axs[1].bar(xx + (k - 1) * 0.27, [r[key] for r in rows], 0.27, label=name)
    axs[1].axhline(0, color="k", linewidth=0.6)
    axs[1].set_xticks(xx)
    axs[1].set_xticklabels(lab, rotation=60, ha="right", fontsize=7)
    axs[1].set_ylabel("copper area against the vector area (%)")
    axs[1].set_title("our reader on every copper layer of the 8 real boards (12 layers; pieces: 12 of 12 identical)", fontsize=9)
    axs[1].legend(fontsize=7)
    px = [r["pieces_vector"] for r in rows]
    py = [r["pieces_native"] for r in rows]
    axs[2].scatter(px, py, s=30)
    axs[2].plot([20, 500], [20, 500], color="k", linewidth=0.7)
    axs[2].set_xscale("log")
    axs[2].set_yscale("log")
    from matplotlib.ticker import NullFormatter, ScalarFormatter
    for axis in (axs[2].xaxis, axs[2].yaxis):                              # plain numbers, no crowded minor labels
        axis.set_major_formatter(ScalarFormatter())
        axis.set_minor_formatter(NullFormatter())
        axis.set_ticks([20, 50, 100, 200, 500])
    axs[2].set_xlabel("copper pieces, vector union\n(gerbonara + shapely)")
    axs[2].set_ylabel("pieces, our 0.05 mm mask (8-connected)")
    axs[2].set_title("connected pieces, 12 layers: all on the line", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_validation_summary.png", dpi=105)
    plt.close(fig)


def fig_stormduino_nets():
    """!
    @brief The Stormduino (MIT) read by the converter and coloured by the net of the KiCad file: the pieces of both layers joined through the plated holes, each with the net of the CAD objects it holds (needs data/storm with the `.kicad_pcb`).
    @return None.
    """
    import importer
    import kicad_pcb
    import study_kicad_nets as sk
    from collections import Counter, defaultdict
    from paths import DATA
    pcb = DATA / "storm" / "stormduino.kicad_pcb"
    if not pcb.exists():
        print("figure 03 skipped: fetch the Stormduino files (scripts/fetch_boards.py storm)")
        return
    ib = importer.import_board(importer.roles_of_downloaded("storm"), pix=0.1, cell=1.0)
    kc = kicad_pcb.read(pcb)
    lays = sk.layer_pieces(ib)
    names = ["F.Cu", "B.Cu"]
    par = {}

    def find(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for h in ib.holes:
        ps = [(li, sk.piece_at(lays[li][0], *sk.pixel(ib, h["x"], h["y"]), reach=3)) for li in range(2)]
        if all(l for _, l in ps):
            par[find(ps[0])] = find(ps[1])
    votes = defaultdict(Counter)
    for sg in kc["segments"]:
        if sg["layer"] in names:
            li = names.index(sg["layer"])
            votes[find((li, sk.piece_at(lays[li][0], *sk.pixel(ib, sg["a"][0], -sg["a"][1]))))][sg["net"]] += 1
    for p_ in kc["pads"]:
        if p_["net"]:
            for li, n in enumerate(names):
                if n in p_["layers"] or "*.Cu" in p_["layers"]:
                    votes[find((li, sk.piece_at(lays[li][0], *sk.pixel(ib, p_["p"][0], -p_["p"][1]))))][p_["net"]] += 1
    net_of = {g: c.most_common(1)[0][0] for g, c in votes.items()}
    area = Counter()
    for li in range(2):
        for lab in range(1, lays[li][1] + 1):
            g = find((li, lab))
            area[net_of.get(g, 0)] += int((lays[li][0] == lab).sum())
    top = [n for n, _ in area.most_common(9) if n]
    cmap = plt.get_cmap("tab10")
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.6))
    for li, ax in enumerate(axs):
        img = np.ones(lays[li][0].shape + (3,)) * 0.12
        for lab in range(1, lays[li][1] + 1):
            g = find((li, lab))
            n = net_of.get(g, 0)
            col = cmap(top.index(n)) [:3] if n in top else (0.6, 0.6, 0.6)
            img[lays[li][0] == lab] = col
        ax.imshow(img, extent=(0, ib.width, 0, ib.height), interpolation="nearest")
        for h in ib.holes:
            ax.add_patch(plt.Circle((h["bx"], h["by"]), max(h["d"], 0.35) / 2.0, facecolor="k", edgecolor="w", linewidth=0.3))
        ax.set_title(f"Stormduino {names[li]}: pieces joined through the {len(ib.holes)} plated holes, coloured by the net of the KiCad file", fontsize=8)
        ax.set_xlabel("mm")
    handles = [plt.Line2D([0], [0], marker="s", linestyle="", color=cmap(i), label=kc["nets"][n]) for i, n in enumerate(top)]
    handles.append(plt.Line2D([0], [0], marker="s", linestyle="", color=(0.6, 0.6, 0.6), label="other nets (small)"))
    axs[1].legend(handles=handles, fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_stormduino_nets.png", dpi=105)
    plt.close(fig)


def fig_mask_explained():
    """!
    @brief The mask explained on one thin track: the vector of the file, the binary mask at 0.1 mm (centre sampling) with its pieces, the coverage mask (4 x 4 sub-samples) and the copper fraction of each 1 mm cell.
    @return None.
    """
    import math
    from scipy import ndimage
    from boards_synthetic import HEAD, mm
    size, w, th = 4.0, 0.075, 20.0
    c, s_ = math.cos(math.radians(th)), math.sin(math.radians(th))
    text = HEAD + f"%ADD10C,{w}*%\nD10*\nX{mm(0.2)}Y{mm(1.0)}D02*\nX{mm(0.2 + 3.7 * c)}Y{mm(1.0 + 3.7 * s_)}D01*\nM02*\n"
    layer = ng.Layer(text)
    cv = ng.Canvas(0.0, size, size, size, 0.1)
    layer.draw(cv)
    binary = cv.mask
    cov = ng.render_coverage(layer, 0.0, size, size, size, 0.1, 4)
    _, pieces = ndimage.label(binary, structure=np.ones((3, 3)))
    ext = (0, size, 0, size)
    fig, axs = plt.subplots(1, 4, figsize=(18, 4.9))
    x0, y0, x1, y1 = 0.2, 1.0, 0.2 + 3.7 * c, 1.0 + 3.7 * s_
    nx_, ny_ = -s_ * w / 2, c * w / 2
    for ax in axs:
        ax.set_xlim(0, size)
        ax.set_ylim(0, size)
        ax.set_aspect("equal")
        for k in range(int(size) + 1):
            ax.axhline(k, color="k", linewidth=0.8)
            ax.axvline(k, color="k", linewidth=0.8)
        ax.set_xlabel("mm; black lines: the 1 mm cells of the thermal grid")
    axs[0].add_patch(plt.Polygon([(x0 + nx_, y0 + ny_), (x1 + nx_, y1 + ny_), (x1 - nx_, y1 - ny_), (x0 - nx_, y0 - ny_)], facecolor="#b8651b"))
    axs[0].set_title(f"1. the Gerber: a vector, a stroke 0.075 mm wide at {th:.0f} degrees\n(exact width and angle, no pixels)", fontsize=9)
    axs[1].imshow(binary, extent=ext, cmap="Greys", vmin=0, vmax=1.6, interpolation="nearest")
    for k in range(41):
        axs[1].axhline(k * 0.1, color="0.85", linewidth=0.2)
        axs[1].axvline(k * 0.1, color="0.85", linewidth=0.2)
    axs[1].set_title(f"2. binary mask, 0.1 mm pixel (centre sampling):\n{pieces} separate pieces, the track is broken", fontsize=9)
    im = axs[2].imshow(cov, extent=ext, cmap="YlOrBr", vmin=0, vmax=1, interpolation="nearest")
    fig.colorbar(im, ax=axs[2], fraction=0.046, label="copper fraction of the pixel")
    exact = w * 3.7 + math.pi * (w / 2) ** 2                          # stroke with round ends: the exact area of the track
    cov_err = 100.0 * (cov.sum() * 0.01 / exact - 1.0)
    axs[2].set_title(f"3. coverage mask, 0.1 mm pixel (4 x 4 sub-samples):\nevery pixel keeps its share of copper, the area is kept\n(to the 4 x 4 sampling; {cov_err:+.1f} % here)", fontsize=9)
    n = 10
    frac = cov.reshape(int(size), n, int(size), n).mean(axis=(1, 3))
    axs[3].imshow(frac, extent=ext, cmap="YlOrBr", vmin=0, vmax=0.12, interpolation="nearest")
    for i in range(int(size)):
        for j in range(int(size)):
            axs[3].text(j + 0.5, size - i - 0.5, f"{frac[i, j]:.3f}", ha="center", va="center", fontsize=7)
    axs[3].set_title("4. what the program uses today:\nthe copper fraction of each cell (one number:\nit does not say whether the copper is connected)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_mask_explained.png", dpi=105)
    plt.close(fig)


def fig_reader_pipeline():
    """!
    @brief The reader as a diagram: how the commands of a Gerber file become copper pixels, how an Excellon file becomes holes, and how a hole, a pad and a net are matched by position.
    @return None.
    """
    from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
    fig, axs = plt.subplots(1, 2, figsize=(17, 6.6), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axs[0]
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8)
    ax.axis("off")

    def box(x, y, w, h, text, color="#cfe3f5", bold=False):
        """!
        @brief A box with a text.
        @param x Left.
        @param y Bottom.
        @param w Width.
        @param h Height.
        @param text Label.
        @param color Fill.
        @param bold True for a key step.
        @return None.
        """
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12", facecolor=color, edgecolor="k", linewidth=2 if bold else 0.9))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.5)

    def arrow(x0, y0, x1, y1):
        """!
        @brief An arrow.
        @param x0 Start x.
        @param y0 Start y.
        @param x1 End x.
        @param y1 End y.
        @return None.
        """
        ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": "->", "linewidth": 1.3})
    box(0.1, 5.2, 3.4, 2.4, "Gerber file (RS-274X)\n%FSLAX46Y46*%  %MOMM*%\n%ADD10C,0.2*%   aperture\nD10*  X1Y1D02*  X5Y3D01*   draw\nX2Y2D03*   flash\nG36 ... G37*   region\n%LPC*%   clear polarity\n%TO.N,GND*%   net")
    box(4.2, 5.2, 3.0, 2.4, "state of the file\nunits, format, current\naperture, polarity,\nnet attribute,\nstep and repeat", bold=True)
    box(7.9, 5.2, 3.2, 2.4, "primitives drawn on a canvas\nstroke with a round or\nrectangular aperture,\nflash, arc, region,\nmacro; dark adds,\nclear removes", bold=True)
    box(11.8, 5.2, 3.0, 2.4, "copper MASK\nbinary (centre of the\npixel) and coverage\n(4 x 4 sub-samples)\n+ the net of every\nobject", "#fbe3c2", True)
    for x0, x1 in ((3.5, 4.2), (7.2, 7.9), (11.1, 11.8)):
        arrow(x0, 6.4, x1, 6.4)
    box(0.1, 1.6, 3.4, 2.4, "Excellon drill file\nM71 / METRIC   unit\nT1C0.300   tool, diameter\nX044500Y002000   hole\n; #@! TF.FileFunction,\nPlated,1,2,PTH")
    box(4.2, 1.6, 3.0, 2.4, "zero omission, format,\nunit, repeat, routed\nslots; a file with no\nunit is refused", bold=True)
    box(7.9, 1.6, 3.2, 2.4, "holes\n(x, y, diameter,\nplated or not)")
    box(11.8, 1.6, 3.0, 2.4, "matched by POSITION\nwith the pads of every\ncopper layer: hole + pad\n+ net = via or\ncomponent hole", "#d6ecd0", True)
    for x0, x1 in ((3.5, 4.2), (7.2, 7.9), (11.1, 11.8)):
        arrow(x0, 2.8, x1, 2.8)
    arrow(13.3, 5.2, 13.3, 4.0)
    ax.text(7.4, 0.6, "everything is written to be tolerant of the CAD tool and strict about what it cannot do:\nunsupported features (aperture blocks, mirrored or rotated apertures, ...) are reported and the file refused", ha="center", fontsize=8, style="italic")
    ax.set_title("the reader: from the commands of the files to the mask, the holes and the nets", fontsize=10)
    ax = axs[1]
    ax.set_xlim(-6, 6)
    ax.set_ylim(-5.2, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    for k, (y, name) in enumerate(((2.2, "top copper (F)"), (-2.6, "bottom copper (B)"))):
        ax.add_patch(Rectangle((-5, y - 1.7), 10, 3.4, facecolor="#e0a458", alpha=0.35, edgecolor="k"))
        ax.add_patch(Circle((0, y), 1.2, facecolor="#e0a458", edgecolor="k"))
        ax.add_patch(Circle((0, y), 0.5, facecolor="k"))
        ax.text(-4.8, y + 1.45, name, fontsize=8)
        ax.text(2.0, y, "pad (any shape) on the hole: its net\n(X2 aperture function ViaPad / ComponentPad\nand TO.N when written; the Stormduino has none)" if k == 0 else "pad on the hole: the same net", fontsize=7.5, va="center",
                bbox={"fc": "white", "ec": "none", "pad": 2.0})     # the text is longer than the layer rectangle: a white ground keeps its border from cutting through it
    ax.plot([0, 0], [-1.9, 1.7], color="k", linestyle=":")
    ax.text(0, 4.2, "hole at (x, y), 0.4 mm, plated (drill file)\nits centre lies on a pad on every layer, with the same net:\nthe hole is a via and the layers are joined", ha="center", fontsize=8)
    ax.set_title("matching a hole, its pads and the net by position\n(Stormduino: 109 of 109 holes join the two layers)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_reader_pipeline.png", dpi=105)
    plt.close(fig)


def _paint(mask):
    """!
    @brief Colour a copper mask like a board viewer: gold copper on dark green.
    @param mask Boolean array.
    @return numpy.ndarray RGB image.
    """
    green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
    return np.where(mask[..., None], gold, green)


def _diff_image(mask, truth, grow):
    """!
    @brief The pixels where a tool and the vector truth disagree, on white: red where only the tool has copper, blue where only the truth has it (enlarged so that single pixels can be seen).
    @param mask Boolean array of the tool.
    @param truth Boolean array of the vector truth.
    @param grow Radius in pixels by which each differing pixel is enlarged for display.
    @return numpy.ndarray RGB image.
    """
    from scipy import ndimage
    img = np.ones(mask.shape + (3,))
    only_tool, only_truth = mask & ~truth, ~mask & truth
    if grow:
        k = np.ones((2 * grow + 1, 2 * grow + 1), bool)
        only_tool, only_truth = ndimage.binary_dilation(only_tool, k), ndimage.binary_dilation(only_truth, k)
    img[only_truth] = (0.1, 0.3, 0.9)
    img[only_tool] = (0.9, 0.1, 0.1)
    return img


def _render_compare_data():
    """!
    @brief The masks and the numbers written by study_render_compare.py.
    @return Tuple (dict of boolean masks by tool, dict of results).
    """
    import json
    z = np.load(CACHE / "render_compare.npz")
    shape = tuple(int(v) for v in z["storm_shape"])
    masks = {}
    for key, label in (("storm_independent", "independent reader"), ("storm_gerbonara", "gerbonara + shapely (truth)"), ("storm_pygerber", "pygerber"), ("storm_pcb-tools", "pcb-tools"), ("storm_gerbonara16", "gerbonara + shapely, default 16 segments")):
        masks[label] = np.unpackbits(z[key])[: shape[0] * shape[1]].reshape(shape).astype(bool)
    return masks, json.loads((CACHE / "render_compare.json").read_text())


def fig_render_compare():
    """!
    @brief The same board drawn by four tools, and where each differs from the vector truth: the whole top copper of the Stormduino, then a close-up.
    @return None.
    """
    masks, res = _render_compare_data()
    truth = masks["gerbonara + shapely (truth)"]
    names = [n for n in masks if "16 segments" not in n]
    rows = res["storm_top"]["tools"]
    # the close-up: the 12 x 8 mm window with the most copper edge, found on a coarse grid
    from scipy import ndimage
    edge = ndimage.binary_dilation(truth, iterations=1) ^ truth
    win_h, win_w = int(8 / 0.025), int(12 / 0.025)
    integral = edge.astype(np.int32).cumsum(0).cumsum(1)
    best, at = -1, (0, 0)
    for r in range(0, truth.shape[0] - win_h, 80):
        for c in range(0, truth.shape[1] - win_w, 80):
            v = integral[r + win_h, c + win_w] - integral[r, c + win_w] - integral[r + win_h, c] + integral[r, c]
            if v > best:
                best, at = v, (r, c)
    for tag, crop, grow, size, fname in (("whole", (slice(None), slice(None)), 5, (15, 7.4), "fig_09_render_compare_whole_board.png"), ("close-up", (slice(at[0], at[0] + win_h), slice(at[1], at[1] + win_w)), 0, (15, 5.6), "fig_10_render_compare_close_up.png")):
        fig, axs = plt.subplots(2, 4, figsize=size)
        for j, name in enumerate(names):
            axs[0, j].imshow(_paint(masks[name][crop]), interpolation="antialiased")
            shown = {"independent reader": "OUR reader\n(native_gerber.py, NumPy only)", "gerbonara + shapely (truth)": "REFERENCE: gerbonara + shapely\n(exact vector geometry)", "pygerber": "pygerber\n(other tool, raster)", "pcb-tools": "pcb-tools\n(other tool, raster)"}
            axs[0, j].set_title(shown.get(name, name), fontsize=9, fontweight="bold" if name == "independent reader" else "normal")
            if name.startswith("gerbonara"):
                # the reference has no difference with itself: the panel shows its own polygon approximation of circles (16 segments per quarter turn) against the finer one
                coarse = masks["gerbonara + shapely, default 16 segments"]
                n_diff = int((coarse[crop] ^ truth[crop]).sum())
                axs[1, j].imshow(_diff_image(coarse[crop], truth[crop], grow), interpolation="nearest")
                axs[1, j].set_title(f"the reference itself: default 16-segment circles\nagainst 64: {n_diff:,} pixels differ", fontsize=8.5)
            else:
                axs[1, j].imshow(_diff_image(masks[name][crop], truth[crop], grow), interpolation="nearest")
                n_diff = int((masks[name][crop] ^ truth[crop]).sum())
                share = 100.0 * n_diff / max(int(truth[crop].sum()), 1)
                axs[1, j].set_title(f"{n_diff:,} pixels differ ({share:.3f} % of the copper shown)", fontsize=8.5)
            for a in (axs[0, j], axs[1, j]):
                a.set_xticks([])
                a.set_yticks([])
        fig.suptitle(f"The same Gerber file (Stormduino top copper) drawn by our reader and three others ({tag}). \nTop: the picture each draws. Bottom: the pixels where it differs from the reference (red: only that tool has copper, blue: only the reference has it)", fontsize=10)
        fig.tight_layout(rect=(0, 0, 1, 0.94), h_pad=4.5)
        fig.savefig(OUT / fname, dpi=110)
        plt.close(fig)


def fig_how_equal():
    """!
    @brief How equal the independent reader is: the pixels that differ on 12 copper layers (aligned grid and shifted grid), how far each lies from the exact edge, the effect of the truth's own circle approximation and of the pixel size.
    @return None.
    """
    import json
    res = json.loads((CACHE / "render_compare.json").read_text())
    layers = res["layers"]
    labels = [f"{r['board']} {r['layer']}" for r in layers]
    fig, axs = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.5, 1, 1]})
    x = np.arange(len(layers))
    axs[0].bar(x - 0.2, [r["aligned"]["differing_fraction_percent"] for r in layers], 0.4, label="grid lined up with the file's coordinates", color="#e0a458")
    axs[0].bar(x + 0.2, [r["shifted"]["differing_fraction_percent"] for r in layers], 0.4, label="grid shifted by an odd amount", color="#2a6f97")
    axs[0].set_yscale("log")
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    axs[0].set_ylabel("pixels that differ (% of the copper)")
    axs[0].set_title("12 copper layers, 0.1 mm pixels: the reader against the vector truth", fontsize=9)
    axs[0].legend(fontsize=7)
    dist = np.concatenate([np.array(r["shifted"]["edge_distance_px"]) for r in layers])
    axs[1].hist(dist, bins=40, color="#2a6f97")
    axs[1].set_yscale("log")
    axs[1].set_xlabel("distance of a differing pixel to the exact edge (pixels)")
    axs[1].set_ylabel("pixels")
    axs[1].set_title(f"{dist.size:,} differing pixels, the farthest {dist.max():.3f} px from an edge\n(a reading error would sit far from any edge)", fontsize=9)
    seg = res["truth_segments"]
    axs[2].bar([str(r["segments_per_quarter"]) for r in seg], [r["differing_pixels"] for r in seg], color="#6a994e")
    axs[2].set_yscale("log")
    axs[2].set_xlabel("segments per quarter circle in the vector truth")
    axs[2].set_ylabel("pixels that differ (Stormduino top, 0.025 mm)")
    axs[2].set_title("the truth draws circles as polygons: finer polygons,\nfewer differences", fontsize=9)
    for i, r in enumerate(seg):
        axs[2].text(i, r["differing_pixels"], f"{r['area_difference_percent']:+.4f} %", ha="center", va="bottom", fontsize=7)
    fig.suptitle("How equal is the independent reader to the vector truth (README 4.45)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig_11_how_equal_the_reader_is.png", dpi=110)
    plt.close(fig)


def fig_tools_and_pixel():
    """!
    @brief The share of the copper that differs from the vector truth for each tool (whole Stormduino top layer) and the pixels that differ against the pixel size.
    @return None.
    """
    import json
    res = json.loads((CACHE / "render_compare.json").read_text())
    tools = res["storm_top"]["tools"]
    names = [n for n in tools if not n.startswith("gerbonara")]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    vals = [tools[n]["differing_fraction_percent"] for n in names]
    axs[0].bar(names, vals, color=["#2a6f97", "#c9a227", "#b5651d"])
    axs[0].set_yscale("log")
    axs[0].set_ylabel("pixels that differ (% of the copper)")
    axs[0].set_title("Stormduino top copper, 0.025 mm pixels,\nwhole layer on the grid lined up with the file", fontsize=9)
    for i, v in enumerate(vals):
        axs[0].text(i, v, f"{v:.3f} %", ha="center", va="bottom", fontsize=8)
    sweep = res["pixel_sweep"]
    axs[1].bar([f"{r['pixel_mm']} mm" for r in sweep], [r["differing_pixels"] for r in sweep], color="#2a6f97")
    axs[1].set_ylabel("pixels that differ")
    axs[1].set_xlabel("pixel size")
    for i, r in enumerate(sweep):
        axs[1].text(i, r["differing_pixels"], f"{r['differing_area_mm2']:.3f} mm2", ha="center", va="bottom", fontsize=8)
    axs[1].set_title(f"independent reader against the vector truth: of {sweep[0]['area_truth_mm2']:.0f} mm2 of copper,\nat most {max(r['differing_area_mm2'] for r in sweep):.2f} mm2 differ at any pixel size (shifted grid: no ties)", fontsize=9)
    fig.suptitle("The independent reader and two raster renderers against the vector truth (README 4.45)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig_12_tools_and_pixel_size.png", dpi=110)
    plt.close(fig)


def fig_kicad_pixels():
    """!
    @brief The nets against the KiCad project, pixel by pixel: the copper drawn from the `.kicad_pcb` (coloured by net) next to the Gerber copper and the pixels where they differ, for both layers; then the share of every net's CAD pixels that lie on Gerber copper.
    @return None.
    """
    import json
    z = np.load(CACHE / "kicad_pixels.npz")
    res = json.loads((CACHE / "kicad_pixels.json").read_text())
    shape = tuple(int(v) for v in z["shape"])

    def unp(key):
        """!
        @brief Unpack a stored boolean mask.
        @param key Name in the archive.
        @return Boolean array.
        """
        return np.unpackbits(z[key])[: shape[0] * shape[1]].reshape(shape).astype(bool)

    palette = {"GND": "#1f77b4", "+5V": "#ff7f0e", "/DTR": "#2ca02c", "+3V3": "#d62728", "/D13": "#9467bd", "/VIN": "#8c564b", "/D12": "#e377c2", "/D11": "#7f7f7f"}
    import kicad_pcb
    from paths import DATA
    nets = kicad_pcb.read(DATA / "storm" / "stormduino.kicad_pcb")["nets"]
    colour = np.full((len(nets) + 1, 3), 0.62)
    for nid, nm in nets.items():
        if nm in palette:
            colour[nid] = matplotlib.colors.to_rgb(palette[nm])
    from scipy import ndimage
    fig, axs = plt.subplots(2, 3, figsize=(15, 9.6))
    for li, name in enumerate(("F.Cu (top)", "B.Cu (bottom)")):
        net, kind = z[f"net_{li}"], z[f"kind_{li}"]
        cad_img = np.where((kind > 0)[..., None], colour[np.clip(net, 0, len(nets))], np.array([0.04, 0.26, 0.13]))
        gerber = unp(f"gerber_{li}")
        green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
        diff = np.ones(shape + (3,))
        grow = np.ones((7, 7), bool)
        diff[ndimage.binary_dilation(unp(f"onlyk_far_{li}"), grow)] = (0.1, 0.3, 0.9)
        diff[ndimage.binary_dilation(unp(f"onlyg_far_{li}"), grow)] = (0.9, 0.1, 0.1)
        r = res["layers"]["F.Cu" if li == 0 else "B.Cu"]
        axs[li, 0].imshow(cad_img, interpolation="antialiased")
        axs[li, 0].set_title(f"{name}: copper drawn from the .kicad_pcb, coloured by net\n(grey: the other 50 nets)", fontsize=9)
        axs[li, 1].imshow(np.where(gerber[..., None], gold, green), interpolation="antialiased")
        axs[li, 1].set_title(f"{name}: copper our reader draws from the Gerber", fontsize=9)
        axs[li, 2].imshow(diff, interpolation="nearest")
        axs[li, 2].set_title(f"where they differ by more than one pixel (0.05 mm)\nred: only Gerber {r['only_gerber_beyond_one_pixel']:,} px; blue: only CAD {r['only_cad_beyond_one_pixel']:,} px (of {r['gerber_pixels']:,})", fontsize=8.5)
        for a in axs[li]:
            a.set_xticks([])
            a.set_yticks([])
    fig.suptitle("Stormduino (KiCad 5, MIT): the nets of the CAD file against the copper of the Gerbers, pixel by pixel", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "fig_13_kicad_nets_against_gerber.png", dpi=105)
    plt.close(fig)
    # per net: the share of the CAD pixels of the net that lie on Gerber copper
    items = sorted(((v["on_gerber_copper"] / v["cad_pixels"], k, v["cad_pixels"]) for k, v in res["nets"].items()))
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4), gridspec_kw={"width_ratios": [1.6, 1]})
    axs[0].bar(range(len(items)), [100 * (1 - r) for r, _, _ in items], color="#2a6f97")
    axs[0].set_yscale("log")
    axs[0].set_xlabel("the 57 nets of the project with copper, sorted")
    axs[0].set_ylabel("CAD pixels of the net without Gerber copper (%)")
    axs[0].set_title("every net: how much of the copper the CAD file draws is missing in the Gerber", fontsize=9)
    for i, (r, k, px) in enumerate(items[-4:]):
        axs[0].text(len(items) - 4 + i, 100 * (1 - r), k, rotation=90, ha="center", va="bottom", fontsize=6)
    layers = res["layers"]
    labels = ["F.Cu", "B.Cu"]
    both = [layers[n]["both"] for n in labels]
    only_g = [layers[n]["only_gerber"] - layers[n]["only_gerber_beyond_one_pixel"] for n in labels]
    only_g_far = [layers[n]["only_gerber_beyond_one_pixel"] for n in labels]
    only_k = [layers[n]["only_cad"] for n in labels]
    x = np.arange(2)
    axs[1].bar(x, both, color="#e0a458", label="on both")
    axs[1].bar(x, only_g, bottom=both, color="#f4b6b6", label="only Gerber, within 1 px of a CAD edge")
    axs[1].bar(x, only_g_far, bottom=np.array(both) + np.array(only_g), color="#d62728", label="only Gerber, farther")
    axs[1].set_ylim(min(both) * 0.97, (max(both) + max(only_g) + max(only_g_far)) * 1.04)      # head-room for the legend; the axis does not start at zero (said in the label)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(labels)
    axs[1].set_ylabel("copper pixels (0.05 mm); the axis does not start at zero")
    axs[1].set_title(f"pixels on each layer; only CAD: {only_k[0]} and {only_k[1]} px, all within one pixel\nof Gerber copper (none farther: the 0 px of figure 13)", fontsize=9)
    axs[1].legend(fontsize=7, loc="upper left")
    fig.suptitle("The nets of the KiCad project against the Gerber copper (README 4.46)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig_14_kicad_nets_per_net.png", dpi=105)
    plt.close(fig)


def fig_board_outline():
    """!
    @brief The board outline read from the profile layer: the Stormduino (strokes, board region, polygon against the bounding box), a synthetic board with rounded corners and a slot, and the same board with a gap in the contour (flagged as not closed).
    @return None.
    """
    import json
    import outline
    z = np.load(CACHE / "outline.npz")
    recs = {r["label"]: r for r in json.loads((CACHE / "outline.json").read_text()) if "error" not in r}
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.6))
    for ax, label, title in zip(axs, ("storm", "synthetic slot", "synthetic gap0.2"), ("Stormduino (MIT): the board is not its bounding box", "synthetic board: rounded corners (arcs) and a slot", "synthetic board with a gap of 0.2 mm in the bottom side")):
        shape = tuple(int(v) for v in z[label + "|shape"])
        win = tuple(float(v) for v in z[label + "|window"])
        mask = np.unpackbits(z[label])[: shape[0] * shape[1]].reshape(shape).astype(bool)
        strokes = np.unpackbits(z[label + "|strokes"])[: shape[0] * shape[1]].reshape(shape).astype(bool)
        img = np.ones(shape + (3,)) * 0.97
        img[mask] = (0.62, 0.78, 0.55)
        img[strokes] = (0.1, 0.1, 0.1)
        extent = (win[0], win[0] + win[2], win[1] - win[3], win[1])
        ax.imshow(img, extent=extent, interpolation="nearest")
        for poly in outline.polygons(mask, win, recs[label]["pixel_mm"], 0.7)[:3]:
            ax.plot(poly[:, 0], poly[:, 1], "-", color="#d62728", linewidth=1.2)
            ax.plot(poly[:, 0], poly[:, 1], "o", color="#d62728", markersize=3.5)
        r, c = np.where(strokes)
        px = recs[label]["pixel_mm"]
        x0, x1, y0, y1 = win[0] + c.min() * px, win[0] + c.max() * px, win[1] - r.max() * px, win[1] - r.min() * px
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], "--", color="#1f77b4", linewidth=1.0)
        rec = recs[label]
        txt = f"board {rec['board_area_mask_mm2']:.0f} mm2, bounding box {(x1 - x0) * (y1 - y0):.0f} mm2\n" + ("contour closed" if rec["closed_found"] else f"contour NOT closed: {rec['leaked_pixels']:,} board pixels connect to the outside")
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.set_xlabel(txt + ("; polygon: " + ", ".join(f"{q['vertices']} vertices" for q in rec["polygons"][:2]) if rec["polygons"] else ""), fontsize=8)
        ax.set_aspect("equal")
    fig.suptitle("The board outline from the profile layer (README 4.47): black strokes, green board region (even-odd rule), red polygon extracted, blue dashed bounding box", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OUT / "fig_15_board_outline.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Make the figures of this investigation.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_gerber_render()
    fig_validation()
    fig_stormduino_nets()
    fig_mask_explained()
    fig_reader_pipeline()
    fig_render_compare()
    fig_how_equal()
    fig_tools_and_pixel()
    fig_kicad_pixels()
    fig_board_outline()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
