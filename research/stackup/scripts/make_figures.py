"""!
@file make_figures.py
@brief Pictures of the stack-up study, written to figures/ (committed, linked from the README files).

@details The numbers come from running the two studies of this folder and reading the tables they print, so the pictures cannot disagree with them.
         fig_01: maximum temperature of the example board with the program's typical stack-up and the published ones of fabricators;
         fig_02: rise of the hottest point for several stack-ups, in the five models; fig_03: sensitivity of the rise to the stack-up numbers;
         fig_06: inner copper 15.2 um against 35 um; fig_07: real 1 oz builds of fabricators against the 1 oz rules of the program.
Usage: python research/stackup/scripts/make_figures.py [inner]   (from the repository root; about 2 minutes; `inner` draws only figures 6 and 7)
"""

import re
import subprocess
import textwrap
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures"          # kept in the repository on purpose: the README files link to them


def run(script, *args):
    """!
    @brief Run one study of this folder and return what it prints.
    @param script File name of the study.
    @param args Extra command-line arguments of the study.
    @return str Standard output.
    """
    return subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True, check=True).stdout


def table(text, header):
    """!
    @brief Rows of the Markdown table that follows a header line.
    @param text Output of a study.
    @param header Start of the line before the table.
    @return list of lists of str (cells).
    """
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(header)) + 3
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append([c.strip() for c in lines[i].strip("|").split("|")])
        i += 1
    return rows


def fig_vendors():
    """!
    @brief Maximum temperature of the example board for every stack-up (program templates against fabricators), grouped by layer count.
    @return None.
    """
    rows = []
    for ln in run("stackup_vendor_check.py").splitlines():
        m = re.match(r"(\d)L (.+?)\s+total ([\d.]+) mm\s+Tmax ([\d.]+)", ln)
        if m:
            rows.append((int(m.group(1)), m.group(2).strip(), float(m.group(4))))
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), sharex=False)
    for ax, layers in zip(axs, (4, 6, 8)):
        r = [x for x in rows if x[0] == layers]
        names = [x[1].split("(")[0].strip()[:34] for x in r]
        cols = ["#1d4ed8" if "program" in n else "#d97706" if "OSH" in n else "#9ca3af" for n in names]
        ax.barh(range(len(r)), [x[2] for x in r], color=cols)
        ax.set_yticks(range(len(r))); ax.set_yticklabels(names, fontsize=7); ax.invert_yaxis()
        lo = min(x[2] for x in r)
        ax.set_xlim(lo - 3, max(x[2] for x in r) + 1.5)
        for k, x in enumerate(r):
            ax.text(x[2] + 0.1, k, f"{x[2]:.1f}", va="center", fontsize=7)
        ax.set_title(f"{layers} layers", fontsize=10)
        ax.set_xlabel("Tmax of the example board (°C)")
    fig.suptitle("Program templates (blue) against published fabricator stack-ups: the dielectric split moves Tmax by 0.1 to 1.5 °C; OSH Park (orange) has thicker outer copper", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_vendor_stackups.png", dpi=110)
    plt.close(fig)


def fig_stacks(text):
    """!
    @brief Rise of the hottest point of several stack-ups in the five models.
    @param text Output of stackup_outline_study.py.
    @return None.
    """
    rows = table(text, "A. Advanced")
    names = [r[0] for r in rows]
    fvm = np.array([float(r[1]) for r in rows])
    others = {n: [float(r[k].split()[0]) for r in rows] for k, n in ((2, "FDM"), (3, "3D solid"), (4, "Lumped"), (5, "Analytic"))}
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(14, 5.4))
    ax.bar(x - 0.3, fvm, 0.15, label="FVM", color="#1f2937")
    for k, (n, col) in enumerate((("FDM", "#6b7280"), ("3D solid", "#059669"), ("Lumped", "#d97706"), ("Analytic", "#1d4ed8"))):
        ax.bar(x - 0.15 + 0.15 * k, fvm * (1 + np.array(others[n]) / 100.0), 0.15, label=n, color=col)
    ax.set_xticks(x); ax.set_xticklabels([textwrap.fill(n, 20) for n in names], fontsize=7)
    ax.set_ylabel("Rise of the hottest point (K)")
    ax.set_title("The stack-up matters (70 to 102 K on the same board) and the models follow it in the same direction", fontsize=10)
    ax.legend(fontsize=8, ncol=5)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_stackups_in_five_models.png", dpi=110)
    plt.close(fig)


def fig_sensitivity(text):
    """!
    @brief Change of the rise for a change of each stack-up number.
    @param text Output of stackup_outline_study.py.
    @return None.
    """
    rows = table(text, "C. Sensitivity")
    names = [r[0] for r in rows]
    ch = [float(r[2].replace("%", "").replace("+", "").strip()) for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh(range(len(rows)), ch, color=["#b45309" if abs(c) > 3 else "#6b7280" for c in ch])
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(names, fontsize=8); ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    for k, c in enumerate(ch):
        ax.text(c + (0.1 if c >= 0 else -0.1), k, f"{c:+.1f} %", va="center", ha="left" if c >= 0 else "right", fontsize=8)
    ax.set_xlim(-6, 8)
    ax.set_xlabel("Change in the rise (%)")
    ax.set_title("Only the finished copper matters (orange)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_sensitivity_to_stackup_numbers.png", dpi=110)
    plt.close(fig)


def fig_inner_copper():
    """!
    @brief Maximum temperature with 15.2 um and 35 um inner copper for every template, with the published tables (planes on every inner layer) as markers.
    @return None.
    """
    fvm = run("study_inner_copper_1oz.py", "--no-3d").split("Model solid3d")[0]
    data = {}
    for ln in fvm.splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        if ln.startswith("|") and c[0].isdigit():
            data[(int(c[0]), c[1])] = float(c[3])
    # Published tables with a full plane on every inner layer, from the vendor check (section 4.3)
    pub = {}
    for ln in run("stackup_vendor_check.py").splitlines():
        m = re.match(r"(\d)L (.+?)\s+total ([\d.]+) mm\s+Tmax ([\d.]+)\s+planes ([\d.]+)", ln)
        if m and "program" not in m.group(2):
            pub.setdefault(int(m.group(1)), []).append(float(m.group(5)))
    layers = [2, 4, 6, 8, 10, 12]
    x = np.arange(len(layers))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for k, (name, col, lab) in enumerate((("shipped 15.2", "#1d4ed8", "shipped, 15.2 um inner (default, 0.5 oz)"),
                                          ("35, same thickness", "#d97706", "35 um inner, same total thickness"),
                                          ("35, dielectrics unchanged", "#9ca3af", "35 um inner, dielectrics unchanged (adopted: template_inner_oz = 1)"))):
        ax.bar(x - 0.27 + 0.27 * k, [data.get((n, name), data.get((n, "shipped 15.2"))) for n in layers], 0.27, color=col, label=lab)
    for i, n in enumerate(layers):
        if n in pub:
            ax.scatter([i] * len(pub[n]), pub[n], marker="D", color="black", zorder=3, s=14, label="published tables (planes)" if i == 1 else None)
    ax.set_xticks(x); ax.set_xticklabels([f"{n} layers" for n in layers])
    ax.set_ylim(60, 105); ax.set_ylabel("Tmax of the example board (degC)")
    ax.set_title("A plane on every inner layer: 1 oz inner copper is 6.8 to 7.5 K cooler than the shipped 15.2 um with the dielectrics unchanged\n(7.1 to 7.9 K at the same total thickness; 2 layers: no inner copper)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_inner_copper_1oz.png", dpi=110)
    plt.close(fig)


def fig_real_1oz():
    """!
    @brief Maximum temperature of the program's 1 oz variants against the real 1 oz builds of fabricators (tables C and D of study_real_1oz_stackups.py).
    @return None.
    """
    text = run("study_real_1oz_stackups.py")
    sec_c = text.split("\nC. ")[1].split("\nD. ")[0]
    sec_d = text.split("\nD. ")[1].split("\nE. ")[0]
    var = {}                                            # (layers, row name) -> Tmax
    for ln in sec_c.splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        if ln.startswith("|") and c[0].isdigit():
            var[(int(c[0]), c[1].split(" (inner")[0])] = float(c[4])
    others = {}                                         # layers -> Tmax of the other fabricators (35 um inner)
    for ln in sec_d.splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        m = re.search(r"(\d+)L", c[0]) if ln.startswith("|") else None
        if m:
            others.setdefault(int(m.group(1)), []).append(float(c[2]))
    layers = [4, 6, 8, 10, 12]
    x = np.arange(len(layers))
    rows = (("shipped template 15.2 um", "#1d4ed8", "shipped, 15.2 um"),
            ("35 um, dielectrics unchanged", "#9ca3af", "35 um, dielectrics unchanged (adopted)"),
            ("35 um, scaled to the same thickness", "#d97706", "35 um, scaled to the same thickness"),
            ("30 um, dielectrics unchanged", "#059669", "30 um, dielectrics unchanged"))
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    w = 0.2
    for k, (name, col, lab) in enumerate(rows):
        ax.bar(x - 1.5 * w + k * w, [var[(n, name)] for n in layers], w, color=col, label=lab)
    jlc = [next(v for (n2, name), v in var.items() if n2 == n and name.startswith("JLCPCB 1 oz")) for n in layers]
    ax.scatter(x, jlc, marker="o", color="#dc2626", zorder=4, s=36, label="JLCPCB real 1 oz build (30 um inner)")
    for i, n in enumerate(layers):
        if n in others:
            ax.scatter([i] * len(others[n]), others[n], marker="D", color="black", zorder=3, s=14, label="other fabricators, 1 oz (35 um inner)" if i == 0 else None)
    ax.set_xticks(x); ax.set_xticklabels([f"{n} layers" for n in layers])
    ax.set_ylim(60, 95); ax.set_ylabel("Tmax of the example board (degC)")
    ax.set_title("Real 1 oz builds against the 1 oz rules of the program (full plane on every inner layer)", fontsize=9)
    ax.legend(fontsize=7.5, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_real_1oz_stackups.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "inner":              # only figures 6 and 7 (the two that show the 1 oz option)
        fig_inner_copper()
        fig_real_1oz()
        print("figures 6 and 7 in", OUT)
        return
    fig_vendors()
    text = run("stackup_outline_study.py")
    fig_stacks(text)
    fig_sensitivity(text)
    fig_inner_copper()
    fig_real_1oz()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
