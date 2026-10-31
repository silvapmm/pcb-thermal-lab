#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_combinations.py
@brief The rule with the other features: vias (barrel in the sub-links or across the gap), the simple stack-up of three or more layers, an edge coefficient, a board outline, a metal block, a part on an inner layer.
@details Question answered: does the construction keep its promises when it meets the rest of the program? Part A, vias: a via under the part of a two-layer board with a bare bottom, a barrel as
         copper area in the through conductivity of the resolved reference (ref3d `via_cols`); the rule with `via_mode` series (barrel in every sub-link) and parallel (across the gap), n = 1, 2, 4,
         8, error against the reference, at cells 0.5 and 1 mm (the point via of the program is a known limit below 0.5 mm, research/via-fill). Part B, the simple stack-up of 4 and 6 layers (equal
         slabs, laminate allocated 0.75 d to an outer node): the rule with and without `rebuild_slabs`, against the reference (simple 4- and 6-layer boards with a window). Part C, an edge
         coefficient (h_side = 10 W/m2K, the rectangle's four edges): the energy balance of the rule's network (heat out through every path equals the power) and the change of the peak. Part D, an
         outline (a round board of 40 mm): the energy balance, no heat to the pinned cells, the change of the peak. Part E, a metal block: refused by gapnet (NotImplementedError) and recorded as a
         documented limit, together with what the program does today. Part F, a part on an inner layer of a four-layer board (no face term; the node is at the middle of the layer).
         Output: out/combinations.json. Run: .venv/bin/python research/laminate-nodes/scripts/study_combinations.py
"""

import _bootstrap  # noqa: F401  (import paths)

import boards as BD
import gapnet as GN
import report as RP
import rule as RU
import runner as RN


def balance(net):
    """!
    @brief Heat out through the real paths over the power (the pins are not paths).
    @param net Solved network (K assembled).
    @return float.
    """
    th, _ = net.solve_steady()
    return float(((net.g_amb - net.g_pin) * th).sum() / net.Q.sum())


def main():
    """!
    @brief Run the parts.
    @return None.
    """
    out = {}
    # A: vias
    rows = []
    for cell in (1.0, 0.5):
        s = BD.Spec("2L 1.6 pad 10 bare bottom + via", layers=2, part=3.0, shapes=[("pad", 10), ("none",)], vias=((15.0, 15.0),))
        p = BD.problem(s)
        ref = RN.reference(s, 0.25, 8, quadrant=False)["max"]
        row = {"cell": cell, "program": RN.err(RN.fvm_peak(s, RU.PRESETS["program"], cell, p)["peak"], ref)}
        for mode in ("series", "parallel"):
            for n in (1, 2, 4, 8):
                row[f"{mode} n={n}"] = RN.err(RN.fvm_peak(s, RU.Rule(n_fixed=n, via_mode=mode), cell, p)["peak"], ref)
        rows.append(row)
    RP.table(rows, list(rows[0]), title="A. Via under the part: error against the reference with the barrel as copper area, percent")
    out["A vias"] = rows
    # B: simple stack-up
    rows = []
    for n in (4, 6):
        s = BD.Spec(f"{n}L simple 1.6 mm window 6", layers=n, shapes=[("window", 6)] + [("full",)] * (n - 1))
        ref = RN.reference(s)["max"]
        rows.append({"board": s.name, "program": RN.err(RN.fvm_peak(s, RU.PRESETS["program"], 0.5)["peak"], ref), "rule": RN.err(RN.fvm_peak(s, RU.Rule(), 0.5)["peak"], ref),
                     "rule + rebuild_slabs": RN.err(RN.fvm_peak(s, RU.Rule(rebuild_slabs=True), 0.5)["peak"], ref)})
    RP.table(rows, list(rows[0]), title="B. Simple stack-up of 4 and 6 layers: error against the reference, percent")
    out["B simple stack-up"] = rows
    # C, D: edge coefficient and outline
    rows = []
    s = BD.Spec("2L 1.6 pad 10 bare bottom", layers=2, shapes=[("pad", 10), ("none",)])
    for tag, mod in (("h_side 10", lambda p: setattr(p.board, "h_side", 10.0)), ("round outline 28 mm", lambda p: setattr(p.board, "outline", _circle(15.0, 15.0, 14.0)))):
        p = BD.problem(s)
        mod(p)
        a, b = GN.build(p, 0.5, RU.PRESETS["program"]), GN.build(p, 0.5, RU.Rule())
        rows.append({"case": tag, "balance program": (".9f", balance(a)), "balance rule": (".9f", balance(b)), "peak change %": 100 * (RN.fvm_peak(s, RU.Rule(), 0.5, p)["peak"] / RN.fvm_peak(s, RU.PRESETS["program"], 0.5, p)["peak"] - 1)})
    RP.table(rows, list(rows[0]), title="C, D. Edge coefficient and outline: energy balance and change")
    out["C D edge outline"] = rows
    # E: metal block
    from pcbthermal import examples as EX
    note = "no example with a block available"
    try:
        GN.build(EX.example_block_board(), 1.0, RU.Rule())
    except NotImplementedError as e:
        note = f"refused: {e}"
    out["E block"] = note
    print("E.", note)
    # F: part on an inner layer
    s = BD.Spec("4L typical window 6, part on layer 2", layers=4, stack="template", shapes=[("window", 6)] + [("full",)] * 3)
    p = BD.problem(s)
    p.heaters[0].layer = 1
    a, b = GN.build(p, 0.5, RU.PRESETS["program"]), GN.build(p, 0.5, RU.Rule())
    ta, _ = a.solve_steady()
    tb, _ = b.solve_steady()
    out["F inner part"] = {"peak change %": 100 * (GN.peak_under_parts(b, tb, p, RU.Rule())[0] / ta[1].max() - 1)}
    print("F.", out["F inner part"])
    RP.save("combinations", out)


def _circle(cx, cy, r, n=96):
    """!
    @brief A regular polygon approximating a circle, in the Board outline format (an array (n, 2) in metres inside the width x height box).
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param r Radius in mm.
    @param n Vertices.
    @return numpy.ndarray (n, 2) in m.
    """
    import numpy as np
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return 1e-3 * np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)


if __name__ == "__main__":
    main()
