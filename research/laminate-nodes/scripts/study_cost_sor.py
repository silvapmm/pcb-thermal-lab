#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cost_sor.py
@brief The cost of the nodes in unknowns, memory and time (dense layers with pinned cells against the ragged matrix), and what the SOR needs (coloured sweeps over irregular extra nodes).
@details Questions answered: (1) the unknown count that the memory guard must use (`fvm.unknowns` counts layers * cells; with the construction it is the ragged count, or the dense one if the
         extra layers are kept full-size), on a 100 x 80 mm two-layer board with a 60 x 40 mm pour and windows, the typical 4- and 6-layer boards, one-layer boards, the example board, at cells of 1,
         0.5 mm; (2) what the pinned passive cells cost the direct solver (time of net.solve_steady against gapnet.solve_ragged, resident memory by `resource`); (3) the SOR: the point SOR of the
         program on its own network (iterations, seconds) against the general red-black SOR of gapnet on the program's K and on the ladder's K at the same omega and tolerance 1e-8, the bipartite
         check with the barrels in the sub-links, and the same with `via_mode="parallel"` (an odd cycle for even n: the colouring fails). The sweeps are counted on 30 x 30 mm boards at 1 mm (a
         full-size board needs hundreds of thousands of sweeps by point SOR; the program's own SOR study, sor-with-via-couplings, has the Young factor). Output: out/cost_sor.json.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_cost_sor.py
"""

import _bootstrap  # noqa: F401  (import paths)

import resource
import time

import boards as BD
import gapnet as GN
import report as RP
import rule as RU


def rss_mb():
    """!
    @brief Peak resident memory of the process in MB (macOS reports bytes, Linux kilobytes).
    @return float.
    """
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if r > 1e8 else r / 1e3


def main():
    """!
    @brief Run the three parts.
    @return None.
    """
    big = [BD.Spec("2L 100x80 pour 60x40 window 6", layers=2, size=100.0, part=6.0, shapes=[("rects", [(20, 20, 80, 60)]), ("full",)]),
           BD.Spec("4L typical 100 window 6", layers=4, stack="template", size=100.0, shapes=[("window", 6)] + [("full",)] * 3),
           BD.Spec("1L 100 pad 40", layers=1, size=100.0, shapes=[("pad", 40)])]
    rows = []
    for s in big:
        p = BD.problem(s)
        for cell in (1.0, 0.5):
            row = {"board": s.name, "cell": cell}
            net = GN.build(p, cell, RU.Rule(), assemble=True)
            c = net.ladder.counts(p.board.layers == 1)
            row.update({"program unk": c["program"], "ragged x": (".2f", c["ratio_ragged"]), "dense x": (".2f", c["ratio_dense"])})
            t0 = time.perf_counter()
            net.solve_steady()
            row["direct dense s"] = (".1f", time.perf_counter() - t0)
            t0 = time.perf_counter()
            GN.solve_ragged(net)
            row["ragged s"] = (".1f", time.perf_counter() - t0)
            prog = GN.build(p, cell, RU.PRESETS["program"])
            t0 = time.perf_counter()
            prog.solve_steady()
            row["program s"] = (".1f", time.perf_counter() - t0)
            row["peak RSS MB"] = (".0f", rss_mb())
            rows.append(row)
    RP.table(rows, list(rows[0]), title="Unknowns and direct-solve time: program, dense extra layers, ragged matrix")
    sor = []
    # The review added the 2L window (flagged and unflagged cells side by side: the case that breaks the point colouring for an even n) and the column (block) red-black SOR
    for s in (BD.Spec("2L 1.6 pad 10 bare bottom 30", layers=2, shapes=[("pad", 10), ("none",)], vias=((15.0, 15.0),)), BD.Spec("2L 1.6 window 6 30", layers=2, shapes=[("window", 6), ("full",)]),
              BD.Spec("1L pad 10 30", layers=1, shapes=[("pad", 10)])):
        p = BD.problem(s)
        base = GN.build(p, 1.0, RU.PRESETS["program"])
        t0 = time.perf_counter()
        _, _, info = base.solve_sor(tol=1e-8)
        sor.append({"board": s.name, "case": "program point SOR (own network)", "iterations": info["iterations"], "seconds": (".1f", time.perf_counter() - t0)})
        for name, net in (("program K, general red-black", base), ("ladder K, general red-black", GN.build(p, 1.0, RU.Rule(n_fixed=4))),
                          ("ladder K, barrels parallel, n=2", GN.build(p, 1.0, RU.Rule(n_fixed=2, via_mode="parallel")))):
            t0 = time.perf_counter()
            _, res, info = GN.solve_sor_general(net, tol=1e-8, max_iter=60000)
            sor.append({"board": s.name, "case": name, "iterations": info["iterations"], "converged": info["converged"], "colours_ok": info["colours_ok"], "seconds": (".1f", time.perf_counter() - t0)})
        for name, net in (("ladder K, column red-black, n=4", GN.build(p, 1.0, RU.Rule(n_fixed=4))), ("ladder K, column red-black, barrels parallel, n=2", GN.build(p, 1.0, RU.Rule(n_fixed=2, via_mode="parallel")))):
            t0 = time.perf_counter()
            th, res, info = GN.solve_sor_columns(net, tol=1e-8, max_iter=60000)
            dev = float(abs(th - net.solve_steady()[0]).max()) if th is not None else float("nan")
            sor.append({"board": s.name, "case": name, "iterations": info["iterations"], "converged": info["converged"], "colours_ok": info["colours_ok"], "max |SOR - direct| K": (".1e", dev),
                        "seconds": (".1f", time.perf_counter() - t0)})
    RP.table(sor, ["board", "case", "iterations", "converged", "colours_ok", "max |SOR - direct| K", "seconds"], title="SOR sweeps to a residual of 1e-8 (30 mm boards, 1 mm cells)")
    RP.save("cost_sor", {"cost": rows, "sor": sor})


if __name__ == "__main__":
    main()
