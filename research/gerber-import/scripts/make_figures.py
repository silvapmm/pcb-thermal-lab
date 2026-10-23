"""!
@file make_figures.py
@brief The picture of phase 1: our IC board drawn from its Gerber by the independent reader.
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
    axs[0].annotate("GND ring and spoke", (our_board.CX - 14, our_board.CY + 17.2), color="w", fontsize=8)
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
    for line in cp.read_text().splitlines():
        m = re.match(r"\s+pix (0\.1|0\.05|0\.025): (.*)", line)
        if not m:
            continue
        for part in m.group(2).split(", "):
            for t in tools:
                if part.startswith(t):
                    acc[m.group(1)][t].append(abs(float(part.split()[-1].rstrip("%"))))
    fig, axs = plt.subplots(1, 3, figsize=(17, 4.8), gridspec_kw={"width_ratios": [1, 1.5, 0.8]})
    x = np.arange(3)
    for k, t in enumerate(tools):
        axs[0].bar(x + (k - 2) * 0.16, [np.mean(acc[p][t]) if acc[p][t] else np.nan for p in ("0.1", "0.05", "0.025")], 0.16, label=t)
    axs[0].set_yscale("symlog", linthresh=0.1)
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
    axs[2].set_xlabel("separate copper pieces, vector union (gerbonara + shapely)")
    axs[2].set_ylabel("separate pieces, our 0.05 mm mask (8-connected)")
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


def main():
    """!
    @brief Make the figures of this investigation.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_gerber_render()
    fig_validation()
    fig_stormduino_nets()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
