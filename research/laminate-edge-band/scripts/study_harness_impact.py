#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_impact.py
@brief What the edge rules would move on the 17 boards of the frozen-numbers harness (tests/regression): hottest temperature of the FVM and FDM, in K and in percent of the rise, and the unknowns.
@details Boards from tests/regression/regress_boards.py (read only). Rules of lib/edge_rules.py: the band of one gap thickness with the half-cell film ("b1+hc"), the program's margin with it ("margin+hc"), and eta. A board without an edge
         coefficient, or with a metal block, or a one-layer board, is not touched by any rule; the run is skipped for it and it is listed as unchanged by construction.
         Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_harness_impact.py [--cells 2,1] [--model fvm,fdm]
"""

import json
import sys

import _bootband

import edge_rules as ER
from pcbthermal import SolverOptions, fdm, fvm, simulate

sys.path.insert(0, str(_bootband.REPO / "tests" / "regression"))
import regress_boards as RB                                     # noqa: E402

RULES = {"b1+hc": dict(band_width=1.0, halfcell=True), "margin+hc": dict(band_width="margin", halfcell=True), "eta": dict(eta_mode="exact")}


def main(argv=None):
    """!
    @brief Print the table and store out/harness_impact.json.
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    cells = [float(x) for x in (argv[argv.index("--cells") + 1] if "--cells" in argv else "2,1").split(",")]
    models = (argv[argv.index("--model") + 1] if "--model" in argv else "fvm,fdm").split(",")
    rows = []
    print("board | model | cell | h_side | T default | " + " | ".join(f"{r}: dT K (% rise), unknowns x" for r in RULES))
    for name in RB.board_names():
        p = RB.build(name, str(_bootband.REPO / "examples"))
        hs = p.board.h_side
        if p.board.layers < 2 or any(s.is_block() for s in p.heatsinks) or not hs:
            print(f"{name:20s} untouched by construction (layers {p.board.layers}, block {any(s.is_block() for s in p.heatsinks)}, h_side {hs})")
            continue
        for model in models:
            mod = fvm if model == "fvm" else fdm
            for cell in cells:
                try:
                    opts = SolverOptions(models=(model,), cell_mm=cell)
                    t0 = simulate(p, opts).results[model].t_max
                    u0 = mod.unknowns(p, cell)[0]
                    rise = t0 - p.board.ambient
                    row = dict(board=name, model=model, cell=cell, h_side=hs, t0=t0, u0=int(u0))
                    txt = []
                    for rn, kw in RULES.items():
                        with ER.rule(**kw):
                            t = simulate(p, opts).results[model].t_max
                            u = mod.unknowns(p, cell)[0]
                        row[rn] = dict(dT=t - t0, pct=100 * (t - t0) / rise, u=int(u))
                        txt.append(f"{t - t0:+7.3f} ({100 * (t - t0) / rise:+5.2f}%) {u / u0:4.2f}")
                    rows.append(row)
                    print(f"{name:20s} {model} {cell:4g} | {hs:6g} | {t0:8.3f} | " + " | ".join(txt), flush=True)
                except Exception as e:                       # a memory refusal or an unsupported feature: say so and go on
                    print(f"{name:20s} {model} {cell:g} mm: {type(e).__name__}: {str(e)[:80]}")
    (_bootband.OUT / "harness_impact.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
