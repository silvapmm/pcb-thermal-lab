#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_example.py
@brief S4 on the example board of the program: the rows of `docs/validation.md` section 18 (what fills a via barrel) for the Lumped and Analytic models of the program and with the
       proposals (Lumped cluster well, Analytic self-term with the tile rule), and the same board with denser arrays; the numbers that would move in the project documents.
@details Rows: open, epoxy resin (0.3 W/mK), conductive paste (8), copper (385) and no vias; change of the maximum temperature against the open via, in K, and the maximum temperature of the
         open board. Columns: FVM at 1 mm, the FVM with the mean-potential treatment at 0.25 mm (`FVM_fix`, the best the program has but not independent), the Lumped model of the program and
         the cluster well, the Analytic model of the program, the fixed 1 mm tile and the rule of this study. The copper-fill gain is the "copper" row (the documents quote 6.3 to 7.0 K for
         the program's Lumped and Analytic against 3.9 to 4.5 K for the FVM, FDM and 3D solid). Part 2: the example board with 5 x 5 (1.2 mm) and 7 x 7 (1.0 mm) arrays replacing the 3 x 3.
Usage: python research/young-omega-tiles/scripts/study_s4_example.py   (from the repository root; a few minutes). Results go to out/s4_example.json.
"""

import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
import harness as hz                                                        # noqa: E402
import program_cases as pc                                                  # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402

RULE_KIND = sys.argv[sys.argv.index("--rule") + 1] if "--rule" in sys.argv else "cap_nn"

COLUMNS = [
    ("FVM 1 mm", "fvm", 1.0, hz.VARIANTS["FVM"][1]),
    ("FVM_fix 0.25 mm", "fvm", 0.25, hz.VARIANTS["FVM_fix"][1]),
    ("Lumped program", "lumped", 0.5, hz.VARIANTS["L_prog"][1]),
    ("Lumped cluster well", "lumped", 0.5, hz.VARIANTS["L_grp0"][1]),
    ("Analytic program", "analytic", 0.5, lambda: contextlib.nullcontext()),
    ("Analytic fixed 1 mm", "analytic", 0.5, lambda: tr.patched("fixed", t_mm=1.0, floor_mm=0.25)),
    ("Analytic rule", "analytic", 0.5, lambda: tr.patched(RULE_KIND, cap_mm=1.0, k_nn=0.75, m_rad=8.0, floor_mm=0.25)),
]


def board(fill=None, none=False, array=None):
    """!
    @brief The example board with its vias changed.
    @param fill Fill conductivity of every via in W/mK (None: open).
    @param none True removes the vias.
    @param array (n, pitch_mm) replaces the vias by an n x n array centred under the first part (None: the board's own nine).
    @return Problem.
    """
    prob = example_board()
    if none:
        prob.vias = []
        return prob
    if array is not None:
        n, pitch = array
        cx = sum(v.x for v in prob.vias) / len(prob.vias)
        cy = sum(v.y for v in prob.vias) / len(prob.vias)
        d = prob.vias[0].diameter
        prob.vias = []
        h = (n - 1) / 2
        for i in range(n):
            for j in range(n):
                prob.add_via(cx * 1e3 + (i - h) * pitch, cy * 1e3 + (j - h) * pitch, d * 1e3)
    for v in prob.vias:
        if fill is not None:
            v.fill_k = fill
    return prob


def t_max(prob, model, cell, ctx):
    """!
    @brief Maximum temperature of a variant.
    @param prob Problem.
    @param model Model key.
    @param cell Cell in mm.
    @param ctx Context factory.
    @return float degC.
    """
    with ctx():
        return pc.max_rise(prob, model, cell) + prob.board.ambient


def part1():
    """!
    @brief The rows of the fill table.
    @return list of dict.
    """
    print("## 1. Example board (nine 0.3 mm vias under U1): change of the maximum temperature against the open via (K)\n")
    rows = [("epoxy resin", board(0.3)), ("conductive paste", board(8.0)), ("copper", board(385.0)), ("no vias", board(none=True))]
    base_prob = board()
    base = {c[0]: t_max(base_prob, c[1], c[2], c[3]) for c in COLUMNS}
    outio.table(["open board, T_max degC"] + [c[0] for c in COLUMNS], [["T_max"] + [f"{base[c[0]]:.2f}" for c in COLUMNS]])
    out = [{"row": "open", "values": base}]
    table = []
    for name, prob in rows:
        vals = {c[0]: t_max(prob, c[1], c[2], c[3]) - base[c[0]] for c in COLUMNS}
        table.append([name] + [f"{vals[c[0]]:+.2f}" for c in COLUMNS])
        out.append({"row": name, "values": vals})
    outio.table(["row"] + [c[0] for c in COLUMNS], table)
    return out


def part2():
    """!
    @brief Denser arrays on the same board: gain of the copper fill and via effect.
    @return list of dict.
    """
    print("## 2. Denser arrays on the example board: gain of the copper fill (K) and via effect of the open board (K)\n")
    out, table = [], []
    for label, arr in (("3 x 3, 3.5 mm (own)", None), ("5 x 5, 1.2 mm", (5, 1.2)), ("7 x 7, 1.0 mm", (7, 1.0))):
        po, pc_ = board(array=arr), board(385.0, array=arr)
        pn = board(none=True)
        rec = {"board": label}
        cells = []
        for name, model, cell, ctx in COLUMNS:
            t_open = t_max(po, model, cell, ctx)
            gain = t_open - t_max(pc_, model, cell, ctx)
            effect = t_max(pn, model, cell, ctx) - t_open
            rec[name] = {"gain": gain, "effect_open": effect}
            cells.append(f"{gain:.2f} / {effect:.2f}")
        table.append([label] + cells)
        out.append(rec)
    outio.table(["board (gain / effect)"] + [c[0] for c in COLUMNS], table)
    return out


def main():
    """!
    @brief Run and save.
    @return None.
    """
    sc.load_libraries()
    res = {"fill": part1(), "arrays": part2()}
    print("saved", outio.save("s4_example", res))


if __name__ == "__main__":
    main()
