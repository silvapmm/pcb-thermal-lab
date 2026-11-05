#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_impact.py
@brief Which boards of the frozen-numbers harness (17 boards, tests/regression) would the proposals A (local laminate rule) and B (nodes at the edge) move, and by how much, at the 2 mm cell of
       the frozen test and at 1 mm?
@details The boards are built by tests/regression/regress_boards.py (read only). For every board that the prototype supports (two or more layers, no metal block) the FVM runs with the
         program's rule, with the local rule of lib/local_laminate.py (A: trigger 0.05, target 0.05, cap 16) and with the edge nodes (B: margin 1); reported: hottest temperature of the board
         and of each part, the shift in K and in percent of the rise, the unknowns. A board whose number does not move is bit-identical (the plan fires nowhere).
         Run (repository root, light): .venv/bin/python research/laminate-2-6/scripts/study_harness_impact.py [--cells 2,1]
"""

import json
import sys

import _boot26

import local_laminate as LL

sys.path.insert(0, str(_boot26.REPO / "tests" / "regression"))
import regress_boards as RB                                     # noqa: E402


def run(problem, cell, local=None):
    """!
    @brief FVM run with the program's rule or a local one.
    @param problem A Problem.
    @param cell Cell in mm.
    @param local None or the options of local_laminate.make_plan_gaps.
    @return Tuple (t_max, unknowns).
    """
    from pcbthermal import SolverOptions, fvm, simulate
    opts = SolverOptions(models=("fvm",), cell_mm=cell)
    if local is None:
        u = fvm.unknowns(problem, cell)[0]
        return simulate(problem, opts).results["fvm"].t_max, u
    with LL.local_rule(problem, **local):
        u = fvm.unknowns(problem, cell)[0]
        return simulate(problem, opts).results["fvm"].t_max, u


def main(argv=None):
    """!
    @brief Print the table.
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    cells = [float(x) for x in (argv[argv.index("--cells") + 1] if "--cells" in argv else "2,1").split(",")]
    rows = []
    print("board | cell | T default | A local (dT K, unknowns x) | B edge (dT K, unknowns x)")
    for name in RB.board_names():
        try:
            p = RB.build(name, str(_boot26.REPO / "examples"))
        except Exception as e:
            print(name, "build:", e)
            continue
        if p.board.layers < 2 or any(s.is_block() for s in p.heatsinks):
            print(f"{name:22s} not supported by the prototype (layers {p.board.layers}, block {any(s.is_block() for s in p.heatsinks)})")
            continue
        for cell in cells:
            try:
                t0, u0 = run(p, cell)
                ta, ua = run(p, cell, dict(trigger=0.05, target=0.05, n_cap=16))
                tb, ub = run(p, cell, dict(trigger=1e9, edge=True, edge_margin=1))
            except Exception as e:                              # a memory refusal or an unsupported feature: say so, go on
                print(f"{name:22s} {cell:g} mm: {type(e).__name__}: {str(e)[:80]}")
                continue
            rows.append(dict(board=name, cell=cell, t0=t0, ta=ta, tb=tb, u0=u0, ua=ua, ub=ub, h_side=p.board.h_side))
            print(f"{name:22s} {cell:4g} | {t0:8.3f} | {ta - t0:+7.3f} ({ua / u0:4.2f}) | {tb - t0:+7.3f} ({ub / u0:4.2f})  h_side {p.board.h_side}", flush=True)
    (_boot26.OUT / "study_harness_impact.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
