"""!
@file make_figures.py
@brief Pictures of the model comparison, written to figures/ (committed, linked from the README files).

@details The numbers come from running the studies of this folder and reading the tables they print.
         fig_01: error of the four other models against the FVM on 19 scenarios; fig_02: the example board against the grid spacing for the FVM, both FDM samplings and the 3D solid;
         fig_03: the solvers (direct, CG, SOR with a residual rule and with the original step rule) on several boards.
Usage: python research/models-comparison/scripts/make_figures.py   (from the repository root; about 2 minutes)
"""

import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                       # the studies of this folder
sys.path.insert(0, str(HERE.parents[2]))            # the program
OUT = HERE.parent / "figures"          # kept in the repository on purpose: the README files link to them


def run(script):
    """!
    @brief Run one study of this folder and return what it prints.
    @param script File name of the study.
    @return str Standard output.
    """
    return subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True, check=True).stdout


def table(text, start):
    """!
    @brief The header and the rows of the Markdown table whose header line starts with `start`.
    @param text Output of a study.
    @param start Beginning of the header line.
    @return tuple (list of str, list of list of str).
    """
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(start))
    head = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    j = i + 2
    while j < len(lines) and lines[j].startswith("|"):
        rows.append([c.strip() for c in lines[j].strip("|").split("|")])
        j += 1
    return head, rows


def pct(cell):
    """!
    @brief The percentage in parentheses of a cell such as "90.27 (+0.2 %)".
    @param cell Table cell.
    @return float The number.
    """
    return float(re.search(r"\(([+-]?\d+\.\d) %\)", cell).group(1))


def fig_scenarios(text):
    """!
    @brief Error of FDM, 3D solid, Lumped and Analytic against the FVM on every scenario.
    @param text Output of validation_study.py.
    @return None.
    """
    head, rows = table(text, "| Scenario")
    names = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(13, 6))
    y = np.arange(len(rows))
    for k, (name, col, mk) in enumerate((("FDM", "#6b7280", "o"), ("3D solid", "#059669", "s"), ("Lumped", "#d97706", "^"), ("Analytic", "#1d4ed8", "D"))):
        ax.plot([pct(r[2 + k]) for r in rows], y, mk, color=col, label=name, ms=6)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8); ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Error of the temperature rise against the FVM (%)")
    ax.set_title("19 scenarios, 1 mm cells: the models stay within a few percent except where the copper edge crosses the heater (warned)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_models_against_the_fvm.png", dpi=110)
    plt.close(fig)


def fig_grid(text):
    """!
    @brief Maximum temperature of the example board against the grid spacing.
    @param text Output of validation_study.py.
    @return None.
    """
    head, rows = table(text, "| Spacing")
    sp = [float(r[0]) for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for k, (name, col) in enumerate((("FVM", "#1f2937"), ("FDM (area sampling)", "#6b7280"), ("FDM (point sampling, classic)", "#d97706"), ("3D solid", "#059669"))):
        v = [(float(r[1 + k]) if r[1 + k] != "-" else np.nan) for r in rows]
        ax.plot(sp, v, "o-", color=col, label=name)
    ax.set_xscale("log", base=2); ax.invert_xaxis()
    ax.set_xticks(sp); ax.set_xticklabels([f"{s:g}" for s in sp])
    ax.set_xlabel("Grid spacing (mm)"); ax.set_ylabel("Tmax of the example board (°C)")
    ax.set_title("The FVM converges monotonically; the FDM jumps by about ±0.5 °C with the grid", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_grid_convergence_of_the_models.png", dpi=110)
    plt.close(fig)


def fig_solvers():
    """!
    @brief Difference to the direct solver for CG and the two SOR stopping rules, on every board.
    @return None.
    """
    head, rows = table(run("solver_equivalence.py"), "| Board")
    boards = list(dict.fromkeys(r[0] for r in rows))
    solvers = [("cg (Jacobi)", "CG", "#6b7280"), ("SOR, residual", "SOR, residual 1e-9", "#059669"), ("SOR, step", "SOR, step 0.01 K (original rule)", "#b91c1c")]
    x = np.arange(len(boards))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for k, (key, lab, col) in enumerate(solvers):
        v = []
        for b in boards:
            r = next(rr for rr in rows if rr[0] == b and rr[1].startswith(key))
            v.append(max(float(r[3]), 1e-13))
        ax.bar(x + (k - 1) * 0.27, v, 0.27, color=col, label=lab)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels([b.replace(", ", ",\n", 1) for b in boards], fontsize=7)
    ax.set_ylabel("Max abs difference to the direct solver (K)")
    ax.set_title("Same answer with a residual stopping rule (1e-9 K or better); wrong by 2.7 to 16 K with the original step rule", fontsize=9)
    ax.legend(fontsize=8, loc="center left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_solver_equivalence.png", dpi=110)
    plt.close(fig)


DATA = HERE.parent / "out"              # JSON written by the studies (git-ignored)


def study_json(script, name, extra=()):
    """!
    @brief The JSON output of a study of this folder, running it when the file is missing.
    @param script File name of the study.
    @param name File name of the JSON in out/.
    @param extra Further command-line arguments of the study.
    @return The loaded JSON.
    """
    import json
    path = DATA / name
    if not path.exists():
        DATA.mkdir(exist_ok=True)
        subprocess.run([sys.executable, str(HERE / script), *extra, "--json" if script != "study_complex_boards.py" else "--out", str(path)], check=True)
    return json.loads(path.read_text())


def fig_complex_boards():
    """!
    @brief The nine boards of study_complex_boards.py: error of every model against the 3D solid, before and after the corrections of the review.
    @details Needs out/complex_boards_before.json, written by the study run on the program before the corrections (see the study's header), and
             out/complex_boards_after.json (written here when missing).
    @return None.
    """
    import json
    import study_complex_boards as cb
    before = json.loads((DATA / "complex_boards_before.json").read_text())
    after = study_json("study_complex_boards.py", "complex_boards_after.json")
    eb, ea = cb.errors(before), cb.errors(after)
    names = list(after)
    models = ("fvm", "fdm", "lumped", "analytic")
    cols = {"fvm": "#1d4ed8", "fdm": "#9ca3af", "lumped": "#d97706", "analytic": "#7c3aed"}
    fig, ax = plt.subplots(figsize=(14, 5.2))
    y = np.arange(len(names))
    for k, m in enumerate(models):
        off = (k - 1.5) * 0.2
        ax.barh(y + off, [eb[n][m][0] for n in names], 0.18, color="none", ec=cols[m], ls="--", lw=1.0)
        ax.barh(y + off, [ea[n][m][0] for n in names], 0.18, color=cols[m], alpha=0.85, label=f"{m} (now; dashed outline: before)")
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("maximum rise against the 3D solid (%)")
    mb = {m: np.mean([abs(eb[n][m][0]) for n in names]) for m in models}
    ma = {m: np.mean([abs(ea[n][m][0]) for n in names]) for m in models}
    ax.set_title("Nine boards against the 3D solid; mean absolute error before -> now: " + ", ".join(f"{m} {mb[m]:.1f} -> {ma[m]:.1f} %" for m in models), fontsize=9)
    ax.legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_complex_boards_before_after.png", dpi=110)
    plt.close(fig)


def fig_board_layouts():
    """!
    @brief Drawings of the nine boards of study_complex_boards.py: outline, copper of the top layer (and of the other layers, lighter), parts, vias, heatsinks.
    @return None.
    """
    from matplotlib.patches import Polygon as Poly
    import study_complex_boards as cb
    from pcbthermal import Problem
    from pcbthermal.examples import example_block_board, example_board
    items = cb.boards({"Problem": Problem, "example_board": example_board, "example_block_board": example_block_board})
    fig, axs = plt.subplots(3, 3, figsize=(14, 10.5))
    for ax, (name, p) in zip(axs.ravel(), items):
        b = p.board
        W, H = b.width * 1e3, b.height * 1e3
        outline = np.asarray(b.outline) * 1e3 if b.outline is not None else np.array([[0, 0], [W, 0], [W, H], [0, H]])
        ax.add_patch(Poly(outline, closed=True, fc="#dcfce7", ec="#15803d", lw=1.2))
        for z in p.zones:
            ax.add_patch(Poly(np.asarray(z.polygon) * 1e3, closed=True, fc="#d97706", ec="none", alpha=0.75 if z.layer == 0 else 0.15))
        for s in p.heatsinks:
            ax.add_patch(Poly(np.asarray(s.polygon) * 1e3, closed=True, fc="none", ec="#1d4ed8", lw=1.2, ls="--"))
        for v in p.vias:
            ax.plot(v.x * 1e3, v.y * 1e3, "k.", ms=2)
        for h in p.heaters:
            poly = np.asarray(h.polygon) * 1e3
            ax.add_patch(Poly(poly, closed=True, fc="#dc2626", ec="k", lw=0.6, alpha=1.0 if h.layer == 0 else 0.45))
            c = poly.mean(axis=0)
            ax.text(c[0], c[1] + 4, f"{h.name} {h.power:g} W", ha="center", fontsize=6)
        ax.set_xlim(-2, W + 2)
        ax.set_ylim(-2, H + 2)
        ax.set_aspect("equal")
        ax.set_title(f"{name}\n{b.layers} layer(s), {b.thickness * 1e3:g} mm", fontsize=8)
        ax.tick_params(labelsize=6)
    fig.suptitle("The boards of the comparison: orange = copper of the top layer (pale: other layers), red = parts (pale: on the bottom), dashed blue = heatsink or block, dots = vias", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_complex_boards_layouts.png", dpi=105)
    plt.close(fig)


def fig_lumped_rings():
    """!
    @brief The rings of the Lumped model on the raster before and after the minimum width, and the error against the FVM for 10, 20 and 40 rings.
    @return None.
    """
    from pcbthermal import lumped
    data = study_json("study_lumped_rings.py", "lumped_rings.json")
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
    # Ring maps: a 30 mm source on the 50 mm coupon, 0.5 mm cells, 40 rings, around one corner of the source
    n, d = 100, 0.5e-3
    xs = (np.arange(n) + 0.5) * d
    foot = (np.abs(xs[None, :] - 0.025) < 0.015) & (np.abs(xs[:, None] - 0.025) < 0.015)
    from scipy import ndimage
    dist = ndimage.distance_transform_edt(~foot, sampling=(d, d))
    for ax, w, title in ((axs[0], 0.0, "before: 40 rings, the inner ones thinner than a cell"), (axs[1], 1.0, "now: rings narrower than a cell merged")):
        e = lumped.ring_edges(float(dist.max()), d, d, 40, min_width=w)
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(e[1:], dist, side="left"), len(e) - 2))
        sub = idx[60:100, 60:100]
        ax.imshow(np.where(sub % 2 == 0, 0.25, 0.75) * (sub > 0), origin="lower", cmap="Greys", vmin=0, vmax=1, extent=(30, 50, 30, 50))
        ax.imshow(np.where(sub == 0, 1.0, np.nan), origin="lower", cmap="Reds", vmin=0, vmax=1.2, extent=(30, 50, 30, 50))
        ax.set_title(f"{title}\n{len(e) - 1} rings used", fontsize=8.5)
        ax.set_xlabel("x (mm), one corner of the source (red)")
    sides = data["sides"]
    cols = {"10": "#1d4ed8", "20": "#059669", "40": "#d97706"}
    for r, row in data["coupon"].items():
        axs[2].plot(sides, row["before"], "--", color=cols[r], label=f"{r} rings, before")
        axs[2].plot(sides, row["after"], "-", color=cols[r], lw=2, label=f"{r} rings, now")
    axs[2].axhline(0, color="k", lw=0.8)
    axs[2].set_xlabel("side of the source on the 50 mm coupon (mm)")
    axs[2].set_ylabel("Lumped maximum against the FVM (%)")
    axs[2].set_title("The error no longer depends on the ring count or jumps with the source", fontsize=9)
    axs[2].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_lumped_rings.png", dpi=110)
    plt.close(fig)


def fig_laminate_nodes():
    """!
    @brief Diagram of a one-layer board in the layered models: before, one node with both films; now, the copper node and two laminate nodes.
    @return None.
    """
    from matplotlib.patches import Rectangle, Circle
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, now in ((axs[0], False), (axs[1], True)):
        ax.set_xlim(0, 10)
        ax.set_ylim(-0.4, 5.2)
        ax.axis("off")
        ax.add_patch(Rectangle((3.8, 4.15), 2.4, 0.3, fc="#dc2626", ec="k"))
        ax.text(5, 4.65, "part", ha="center", fontsize=8)
        ax.add_patch(Rectangle((1, 3.95), 8, 0.2, fc="#d97706", ec="k"))
        ax.add_patch(Rectangle((1, 1.0), 8, 2.95, fc="#dcfce7", ec="#15803d"))
        ax.text(9.15, 4.05, "copper", fontsize=7, va="center")
        ax.text(9.15, 2.4, "laminate\nt_lam", fontsize=7, va="center")
        ax.annotate("", xy=(5, 4.9), xytext=(5, 4.45), arrowprops=dict(arrowstyle="->", color="#1d4ed8"))
        ax.text(5.15, 4.95, "h_top", fontsize=7, color="#1d4ed8")
        if not now:
            ax.add_patch(Circle((5, 2.5), 0.17, fc="#1d4ed8", ec="k"))
            ax.plot([5, 5], [2.67, 3.95], "k-", lw=0.8)
            ax.annotate("", xy=(5, 0.25), xytext=(5, 2.33), arrowprops=dict(arrowstyle="->", color="#1d4ed8"))
            ax.text(5.15, 0.25, "h_bottom on the same node: the laminate is not crossed", fontsize=7, color="#1d4ed8")
            ax.text(5.25, 2.55, "one node: copper + the whole laminate", fontsize=7)
            ax.set_title("before: one node per copper layer", fontsize=9)
        else:
            g = 2.95 / 2
            ys = [3.95 - 0.0, 3.95 - g, 1.0]
            labels = ["copper node: copper + g/2", "laminate node: g", "laminate node: g/2, bottom face"]
            for y, lab in zip(ys, labels):
                ax.add_patch(Circle((5, y if y < 3.9 else 3.75), 0.17, fc="#1d4ed8", ec="k"))
                ax.text(5.3, (y if y < 3.9 else 3.75) + 0.05, lab, fontsize=7)
            for y0, y1 in ((3.58, 3.95 - g + 0.17), (3.95 - g - 0.17, 1.17)):
                ax.add_patch(Rectangle((4.85, y1), 0.3, y0 - y1, fc="white", ec="k", lw=0.8))
                ax.text(3.6, 0.5 * (y0 + y1), "k_th A / g", fontsize=7)
            ax.plot([1, 9], [3.95 - g] * 2, color="#15803d", lw=0.6, ls=":")
            ax.annotate("", xy=(5, 0.25), xytext=(5, 0.83), arrowprops=dict(arrowstyle="->", color="#1d4ed8"))
            ax.text(5.15, 0.25, "h_bottom on the last laminate node", fontsize=7, color="#1d4ed8")
            ax.text(1.1, 1.3, "each node also conducts sideways and\nstores heat (k_ip x its slab)", fontsize=7)
            ax.set_title("now: the laminate cut into two gaps g = t_lam / 2 (FVM, FDM, Lumped)", fontsize=9)
    fig.suptitle("A one-layer board in the layered models (the Analytic model keeps one node with h_bottom in series with t_lam / k_th)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_one_layer_laminate_nodes.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the figures (fig_04 needs out/complex_boards_before.json from the program before the corrections; see study_complex_boards.py).
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    text = run("validation_study.py")
    fig_scenarios(text)
    fig_grid(text)
    fig_solvers()
    fig_complex_boards()
    fig_board_layouts()
    fig_lumped_rings()
    fig_laminate_nodes()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
