#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures of the investigation (06 to 13), drawn from the printed outputs of the studies in out/ (the markdown tables the scripts print), so that a figure quotes only numbers a script printed.
@details Inputs (written by `run_all.sh`): out/edge_distance.txt, out/edge_outline.txt, out/fillin.txt, out/real_effect.txt, out/sor_real.txt, out/spy_*.npz, out/maps_*.npz.
         A figure whose input file is missing is skipped with a message. The temperature maps are drawn only for the Stormduino (MIT) and the own via field: the Allegro board has no
         stated licence and no picture of it is made.
         Files: fig_06_edge_error_against_cell.png, fig_07_edge_error_against_distance.png, fig_08_outline_footprint_variants.png, fig_09_sparsity_against_vias.png,
         fig_10_unknowns_nnz_against_vias.png, fig_11_sor_sweeps_real_boards.png, fig_12_temperature_maps_before_after.png, fig_13_via_effect_against_cell.png.
         Usage: `.venv/bin/python research/via-real-board/scripts/make_figures.py` (from the repository root, after the studies).
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402
import numpy as np                                                          # noqa: E402

import paths                                                                # noqa: E402

OUT, FIG = paths.OUT, paths.FIGURES
NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:e[-+]?\d+)?")
COLOURS = {"program": "#d62728", "mw": "#1f77b4", "mw+image": "#2ca02c", "mw+fold": "#9467bd", "mw+board": "#ff7f0e", "recommended": "#1f77b4"}


def tables(path):
    """!
    @brief Read the markdown tables of a study output.
    @param path Text file written by a study.
    @return list of dicts {title, header, rows}; title is the last "## " line before the table; rows are lists of cell strings.
    """
    out, title, cur = [], "", None
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cur is None:
                cur = {"title": title, "header": cells, "rows": []}
                out.append(cur)
            elif not set("".join(cells)) <= set(":- "):
                cur["rows"].append(cells)
        else:
            cur = None
    return out


def pct(cell):
    """!
    @brief The per-cent figure in parentheses of a cell like "3.21 (+12.3 %)".
    @param cell Cell text.
    @return float or nan.
    """
    m = re.search(r"\(([-+]?\d+\.?\d*) %\)", cell)
    return float(m.group(1)) if m else float("nan")


def first_number(cell):
    """!
    @brief The first number of a cell (thousands separators allowed).
    @param cell Cell text.
    @return float or nan.
    """
    m = NUM.search(cell)
    return float(m.group(0).replace(",", "")) if m else float("nan")


def need(*names):
    """!
    @brief The existing paths among out/ file names; prints a message for the missing ones.
    @param names File names in out/.
    @return list of Path, or None when any is missing.
    """
    p = [OUT / n for n in names]
    miss = [x.name for x in p if not x.exists()]
    if miss:
        print("skipped (missing):", ", ".join(miss))
        return None
    return p


def fig_edge_cell(path):
    """!
    @brief Error of the via effect against the cell for a via 0.16, 0.5 and 2 mm from the edge, with and without the image (S1).
    @param path Output file.
    @return None.
    """
    p = need("edge_distance.txt")
    if not p:
        return
    ts = [t for t in tables(p[0]) if t["header"][0].startswith("d (mm)")]
    t = ts[0]                                                               # the insulated edge (first h_side)
    cells = [float(re.sub(r"[^\d.]", "", h)) for h in t["header"][3:]]
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, d in zip(axs, ("0.16", "0.5", "2")):
        for r in t["rows"]:
            if r[0] == d:
                ax.plot(cells, [pct(c) for c in r[3:]], "o-", label=r[2], color=COLOURS.get(r[2]))
        ax.set_xscale("log")
        ax.invert_xaxis()
        ax.set_xticks(cells)
        ax.set_xticklabels([f"{c:g}" for c in cells])
        ax.minorticks_off()
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(f"via {d} mm from the edge", fontsize=9)
        ax.set_xlabel("cell (mm)")
    axs[0].set_ylabel("error of the via effect (%)")
    axs[0].legend(fontsize=7)
    fig.suptitle("S1: via effect against the resolved reference, with and without the image of the edge", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_edge_distance(path):
    """!
    @brief Error at 1 mm and 0.25 mm against the distance to the edge, for each variant and edge film (S1).
    @param path Output file.
    @return None.
    """
    p = need("edge_distance.txt")
    if not p:
        return
    ts = [t for t in tables(p[0]) if t["header"][0].startswith("d (mm)")]
    cells = [float(re.sub(r"[^\d.]", "", h)) for h in ts[0]["header"][3:]]
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, want in zip(axs, (1.0, 0.25)):
        col = 3 + (cells.index(want) if want in cells else 0)
        for k, t in enumerate(ts):
            for name in ("program", "mw", "mw+image"):
                rows = [r for r in t["rows"] if r[2] == name]
                ax.plot([float(r[0]) for r in rows], [pct(r[col]) for r in rows], "o-" if k == 0 else "s--", color=COLOURS.get(name), label=f"{name}, table {k + 1}")
        ax.set_xscale("log")
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xlabel("distance of the via from the edge (mm)")
        ax.set_title(f"cell {want:g} mm", fontsize=9)
    axs[0].set_ylabel("error of the via effect (%)")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_outline(path):
    """!
    @brief Error of the variants for an outline edge off the grid lines: footprint on the board, image, fold (S1).
    @param path Output file.
    @return None.
    """
    p = need("edge_outline.txt")
    if not p:
        return
    ts = tables(p[0])
    fig, ax = plt.subplots(figsize=(9, 3.8))
    width = 0.15
    names = ["program", "mw", "mw+board", "mw+image", "mw+fold"]
    for k, n in enumerate(names):
        vals, labels = [], []
        for t in ts:
            for r in t["rows"]:
                if r[0] == n:
                    vals.append(pct(r[1]))                                   # first cell (coarsest)
                    labels.append(t["title"].split(",")[0].replace("outline at ", "").replace("x = ", ""))
        ax.bar(np.arange(len(vals)) + k * width, vals, width, label=n, color=COLOURS.get(n))
    ax.set_xticks(np.arange(len(labels)) + 2 * width)
    ax.set_xticklabels(labels, fontsize=6, rotation=20)
    ax.axhline(0, color="k", linewidth=0.6)
    ax.set_ylabel("error of the via effect at the coarsest cell (%)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_spy(path):
    """!
    @brief Sparsity of the matrix of a 3 x 3 and a 9 x 9 via array without and with the couplings (coarse pattern: non-zero counts per block).
    @param path Output file.
    @return None.
    """
    files = [(n, tr) for n in (3, 9) for tr in ("program", "mw")]
    if not all((OUT / f"spy_{n}x{n}_{tr}.npz").exists() for n, tr in files):
        print("skipped (missing): spy_*.npz")
        return
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6))
    for ax, (n, tr) in zip(axs, files):
        d = np.load(OUT / f"spy_{n}x{n}_{tr}.npz")
        ax.imshow(np.log10(d["pattern"] + 1.0), cmap="viridis")
        ax.set_title(f"{n * n} vias, {'program (stencil + point via)' if tr == 'program' else 'couplings'}\n{int(d['unknowns'])} unknowns, nnz {int(d['nnz']):,}", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Sparsity of K (log10 of non-zeros per block): the via blocks sit away from the stencil bands", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_scaling(path):
    """!
    @brief Unknowns, non-zeros of K and of the LU factors against the number of vias (S2 part 1).
    @param path Output file.
    @return None.
    """
    p = need("fillin.txt")
    if not p:
        return
    ts = [t for t in tables(p[0]) if t["title"].startswith("own via field")]
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
    for t in ts:
        cell = ("pitch " if "fixed pitch" in t["title"] else "pad ") + t["title"].split("cell")[1].strip()
        for tr, ls in (("program", "--"), ("mw", "-")):
            rows = [r for r in t["rows"] if r[0].endswith(tr) and "skipped" not in r[1]]
            if not rows:
                continue
            nv = [first_number(r[0]) for r in rows]
            axs[0].loglog(nv, [first_number(r[2]) for r in rows], "o" + ls, label=f"nnz(K), {tr}, {cell}")
            axs[1].loglog(nv, [first_number(r[6].split("(")[0]) if "skipped" not in r[6] else np.nan for r in rows], "o" + ls, label=f"nnz(LU), {tr}, {cell}")
    for ax, yl in zip(axs, ("non-zeros of K", "non-zeros of the LU factors")):
        ax.set_xlabel("number of vias")
        ax.set_ylabel(yl)
        ax.legend(fontsize=5.5)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_sor(path):
    """!
    @brief Sweeps of the block SOR (c') against those of the same board without vias, and the block structure (S2).
    @param path Output file.
    @return None.
    """
    p = need("sor_real.txt")
    if not p:
        return
    rows = list(tables(p[0])[0]["rows"])
    if (OUT / "sor_real_05.txt").exists():
        rows += tables(OUT / "sor_real_05.txt")[0]["rows"]
    rows = [r for r in rows if "skipped" not in r[5] and r[0] != "alleg"]            # no figure from the Allegro board (licence not stated)
    lab = [f"{r[0]} {r[1]} mm" for r in rows]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(rows))
    ax.bar(x - 0.2, [first_number(r[5]) for r in rows], 0.4, label="block SOR (c') with vias", color=COLOURS["mw"])
    ax.bar(x + 0.2, [first_number(r[7]) for r in rows], 0.4, label="program's SOR, same board without vias", color="#888888")
    ax.set_xticks(x)
    ax.set_xticklabels(lab, rotation=25, fontsize=7)
    ax.set_ylabel("sweeps to a residual of 1e-9")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def fig_maps(path):
    """!
    @brief Top-layer temperature maps of the Stormduino and the own via field: no vias, the program, the recommended treatment, and the difference (S2).
    @param path Output file.
    @return None.
    """
    names = [n for n in ("storm", "own_100") if (OUT / f"maps_{n}.npz").exists()]
    if not names:
        print("skipped (missing): maps_*.npz")
        return
    fig, axs = plt.subplots(len(names), 4, figsize=(14, 3.4 * len(names)), squeeze=False)
    for r, n in enumerate(names):
        d = np.load(OUT / f"maps_{n}.npz")
        w, h, cell = float(d["width"]), float(d["height"]), float(d["cell"])
        ext = (0, w, 0, h)
        lo, hi = float(d["none"].min()), float(d["none"].max())
        for c, key in enumerate(("none", "program", "recommended")):
            im = axs[r, c].imshow(d[key], origin="lower", extent=ext, vmin=lo, vmax=hi, cmap="inferno")
            axs[r, c].set_title({"none": "no vias", "program": "program (point via)", "recommended": "recommended (mean-potential)"}[key], fontsize=8)
            hl = d["holes"]
            axs[r, c].plot(hl[:, 0], hl[:, 1], ".", color="c", markersize=1.5)
        diff = d["recommended"] - d["program"]
        im2 = axs[r, 3].imshow(diff, origin="lower", extent=ext, cmap="coolwarm", vmin=-abs(diff).max(), vmax=abs(diff).max())
        axs[r, 3].set_title(f"recommended - program (K), max {np.abs(diff).max():.2f}", fontsize=8)
        fig.colorbar(im, ax=axs[r, 2], fraction=0.046)
        fig.colorbar(im2, ax=axs[r, 3], fraction=0.046)
        axs[r, 0].set_ylabel(f"{n.replace('_', ' ')} ({cell:g} mm cells)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fig_convergence(path):
    """!
    @brief The via effect against the cell on each board, program against recommended (S2).
    @param path Output file.
    @return None.
    """
    p = need("real_effect.txt")
    if not p:
        return
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for t in tables(p[0]):
        if t["title"].startswith("alleg"):                                   # no stated licence: numbers only, nothing drawn from this board
            continue
        for r in t["rows"]:
            if "via effect" in r[2]:
                cells = [float(re.sub(r"[^\d.]", "", h)) for h in t["header"][3:-1]]
                vals = [first_number(c) for c in r[3:-1]]
                ax.plot(cells, vals, "o-" if r[1] == "mw" else "s--", color=COLOURS.get("mw" if r[1] == "mw" else "program"), alpha=0.8, label=f"{t['title'].split(':')[0]} {r[0]} {r[1]}")
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xticks([2, 1, 0.5, 0.25])
    ax.set_xticklabels(["2", "1", "0.5", "0.25"])
    ax.minorticks_off()
    ax.set_xlabel("cell (mm)")
    ax.set_ylabel("via effect E (K)")
    ax.legend(fontsize=5.5, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main():
    """!
    @brief Draw all the data figures that have their inputs.
    @return None.
    """
    FIG.mkdir(parents=True, exist_ok=True)
    fig_edge_cell(FIG / "fig_06_edge_error_against_cell.png")
    fig_edge_distance(FIG / "fig_07_edge_error_against_distance.png")
    fig_outline(FIG / "fig_08_outline_footprint_variants.png")
    fig_spy(FIG / "fig_09_sparsity_against_vias.png")
    fig_scaling(FIG / "fig_10_unknowns_nnz_against_vias.png")
    fig_sor(FIG / "fig_11_sor_sweeps_real_boards.png")
    fig_maps(FIG / "fig_12_temperature_maps_before_after.png")
    fig_convergence(FIG / "fig_13_via_effect_against_cell.png")


if __name__ == "__main__":
    main()
