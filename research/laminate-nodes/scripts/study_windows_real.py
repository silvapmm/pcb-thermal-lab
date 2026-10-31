#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_windows_real.py
@brief The rule on real Gerber copper: windows of 36 mm cut from seven real one-layer boards (research/gerber-import), the program with two nodes against the rule, against the resolved 3D solver at 0.2 mm.
@details Question answered: gerber-models R2 found the program's two laminate nodes 5.5 to 13.6 % cool (mean -9.8 %) on seven real windows and 1.9 and 5.3 % with eight nodes. What does
         the rule (nodes only where the copper is partly absent, plus a margin, n by the law) give on the same windows, how many cells are flagged (a real layout has fine features everywhere, so the
         mask may be nearly every cell), and what does a cost cap (`budget`) do? Windows: the first of each of the seven boards of the 42 (`--all`: the 42), copper mask of 0.1 mm pixels from
         research/gerber-import/out/windows_native.npz (git-ignored; found by _bootstrap.gerber_out), brought to 0.2 mm pixels (a pixel is copper when half of it is), heater block 12 to 18 mm,
         1 W, 1.6 mm laminate with 35 um copper, 10 W/m2K on both faces, sides insulated; the program's fill is the mean of the 0.2 mm pixels of each cell (cells of 0.8 and 1.2 mm). The reference
         is ref3d.solve_fills (the layout of study_laminate_reference.py of gerber-models, written again: 291 000 unknowns, 8 sub-slabs; about 8 GB for a few minutes per window). Printed: the mean
         rise of the heater (the metric of gerber-models) and the peak, errors against the reference, flagged fraction, unknown ratio. Saves the field of the first window (reference face, rule,
         program) to out/windows_real_fields.npz for the error map of make_figures.py.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_windows_real.py [--all] [--cell 0.8]
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

import numpy as np

import boards as BD
import gapnet as GN
import ref3d as R3
import report as RP
import rule as RU
from pcbthermal import Problem

PIX = 0.2                     # mm of the reference pixel
RECT = (12.0, 12.0, 18.0, 18.0)


def problem():
    """!
    @brief The one-layer board of the windows.
    @return Problem.
    """
    p = Problem.new(36.0, 36.0, 1, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None)
    p.add_zone(1, rect=(0, 0, 36, 36))                  # placeholder: the fill is replaced by the mask
    p.add_heater(1, 1.0, rect=RECT)
    return p


def load_windows(all_windows):
    """!
    @brief The windows, 0.2 mm pixels.
    @param all_windows True: the 42 windows; False: the first of each board.
    @return list of (name, mask02 float (180, 180)).
    """
    out_dir = _bootstrap.gerber_out()
    if out_dir is None:
        raise SystemExit("windows_native.npz not found: set LAMNODES_GERBER_OUT to research/gerber-import/out of the main checkout")
    d = np.load(out_dir / "windows_native.npz", allow_pickle=True)
    masks, meta = d["masks"], [tuple(m) for m in d["meta"]]
    seen, out = set(), []
    for m, mt in zip(masks, meta):
        if not all_windows and mt[0] in seen:
            continue
        seen.add(mt[0])
        m02 = m.reshape(180, 2, 180, 2).mean(axis=(1, 3)) >= 0.5
        out.append((f"{mt[0]} ({mt[1]}, {mt[2]})", m02.astype(float)))
    return out


def main():
    """!
    @brief Run the windows.
    @return None.
    """
    cell = float(sys.argv[sys.argv.index("--cell") + 1]) if "--cell" in sys.argv else 0.8
    k = int(round(cell / PIX))
    p = problem()
    nb = BD.board_numbers(p)
    rules = {"program (2 nodes)": RU.PRESETS["program"], "n=8 all": RU.Rule(n_fixed=8, mask="all", vert=False, face=-1.0), "proposed": RU.Rule(), "proposed edge": RU.Rule(mask="edge"),
             "proposed budget 2": RU.Rule(budget=2.0)}
    rows, fields = [], {}
    for name, m02 in load_windows("--all" in sys.argv):
        ref = R3.solve_fills(nb, [m02], PIX, 8, RECT, 1.0)
        n = m02.shape[0] // k
        fill = m02.reshape(n, k, n, k).mean(axis=(1, 3))[None]
        row = {"window": name, "copper %": (".0f", 100 * m02.mean()), "ref mean K": (".2f", ref["mean"]), "ref peak K": (".2f", ref["max"])}
        for rn, rl in rules.items():
            net = GN.build(p, cell, rl, fill=fill)
            th, _ = net.solve_steady()
            vals = GN.footprint_values(net, th, p, rl)[0]
            row[rn + " mean %"] = 100 * (vals[1].mean() / ref["mean"] - 1)
            row[rn + " peak %"] = 100 * (vals[1].max() / ref["max"] - 1)
            if rn.startswith("proposed"):
                row[rn + " flagged %"] = (".0f", 100 * float(net.ladder.gaps[0].flagged.mean())) if net.ladder.gaps else ""
                row[rn + " unk x"] = (".2f", net.ladder.counts(True)["ratio_ragged"])
            if rn == "proposed" and not fields:
                fields = {"ref_surf": ref["surf"], "fill": fill[0], "rule_top": th[0], "name": name}
        rows.append(row)
        print({k_: v for k_, v in row.items() if "mean %" in k_ or k_ == "window"}, flush=True)
    cols = ["window"] + [c for c in rows[0] if c.endswith("mean %") or c.endswith("flagged %") or c.endswith("unk x")]
    RP.table(rows, cols, title=f"Real windows, one layer, cell {cell} mm: error of the mean heater rise against the resolved 3D face value (percent)")
    RP.save(f"windows_real_{cell}", rows)
    if fields:
        np.savez_compressed(RP.OUT / "windows_real_fields.npz", **{k_: v for k_, v in fields.items() if k_ != "name"})


if __name__ == "__main__":
    main()
