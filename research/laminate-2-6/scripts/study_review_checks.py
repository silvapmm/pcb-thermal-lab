#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief The independent checks of the review of research/laminate-2-6 (README 9): do the proposals hold at the cells a user runs, on a board with many small parts, and is the edge result
       a converged number or a transition effect?
@details Four parts, each printed as a table and saved to out/study_review_checks.json:
         * `cells`: the local rule L6, its margin x2 and x4, the global (0.1, 16) and the default at 0.5 and 1 mm on the thick-laminate cases (README 3.3 is at 0.25 mm only);
         * `many`: a 60 x 40 mm two-layer board, 1.6 mm, with 40 small parts (1 to 3 mm) on pads and a plane under 60 % of it: unknowns, time and hottest temperature of the default,
           L6 and the global (0.1, 16) at 1 and 0.5 mm (README 3.3 has one part per board);
         * `edge`: the edge nodes with the margin 0 (the ring alone, after the review's correction of the prototype), 1, 2 and 4 cells, nodes everywhere (fill 0.9999) with the default
           and the (0.1, 16) laminate, at 0.5 and 1 mm, on the 3.2 mm board with h_side 200 (corner and centre), against the independent 3D solver at 1 mm (8 sub-slabs);
           with --heavy also at 0.5 mm (3.3 GB);
         * `stack`: the 4-layer residual of README 4.2: the simple stack-up against an advanced one with the same gaps (the slab allocation of the outer nodes).
         Run (repository root; light, at most about 1.5 GB without --heavy): .venv/bin/python research/laminate-2-6/scripts/study_review_checks.py [cells|many|edge|stack ...] [--heavy]
"""

import copy
import json
import sys
import time

import _boot26

import numpy as np
import cases
import local_laminate as LL
import s2board as B
from pcbthermal import Problem, SolverOptions, fvm, laminate, simulate
from pcbthermal.model import Dielectric

L6 = dict(trigger=0.05, target=0.05, n_cap=16)


def part_cells():
    """!
    @brief The local rule at 0.5 and 1 mm.
    @return list of row dicts.
    """
    rows = []
    print("cells: S, t, board, cell | error of R' in % against the reference (unknowns)")
    for S, t, pad in ((2.0, 3.2, False), (2.0, 3.2, True), (2.0, 1.6, False), (5.0, 3.2, False)):
        c = B.case(S, t)
        ref, src = B.reference(c, pad)
        for cell in (0.5, 1.0):
            out = {}
            for name, kw in (("default", {}), ("G(0.1,16)", dict(s_max=0.1, n_max=16)), ("L6", dict(local=L6)), ("L6 x2", dict(local=dict(L6, margin_scale=2.0))),
                             ("L6 x4", dict(local=dict(L6, margin_scale=4.0)))):
                r, n, _ = B.run(c, pad, cell, **kw)
                out[name] = (100.0 * (r / ref - 1.0), n)
            rows.append(dict(S=S, t=t, pad=pad, cell=cell, ref=ref, src=src, out=out))
            print(f"  S{S:g} t{t:g} {'pad ' if pad else 'bare'} {cell:g} mm: " + " | ".join(f"{k} {e:+6.2f} ({n})" for k, (e, n) in out.items()), flush=True)
    return rows


def part_many():
    """!
    @brief Cost of the local rule on a board with many small parts.
    @return list of row dicts.
    """
    rng = np.random.default_rng(1)
    p = Problem.new(60, 40, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
    p.add_zone(2, rect=(0, 0, 36, 40))
    for k in range(40):
        s = rng.uniform(1.0, 3.0)
        x, y = rng.uniform(2, 55), rng.uniform(2, 35)
        p.add_zone(1, rect=(x - 0.3, y - 0.3, x + s + 0.3, y + s + 0.3))
        p.add_heater(1, 0.05, rect=(x, y, x + s, y + s), name=f"U{k}")
    rows = []
    print("many: 40 parts of 1 to 3 mm on pads, 60 x 40 mm, 1.6 mm, two layers")
    for cell in (1.0, 0.5):
        for name in ("default", "L6", "G(0.1,16)"):
            t0 = time.time()
            if name == "default":
                n = fvm.unknowns(p, cell)[0]
                tm = simulate(p, SolverOptions(cell_mm=cell, models=("fvm",))).results["fvm"].t_max
            elif name == "L6":
                with LL.local_rule(p, **L6):
                    n = fvm.unknowns(p, cell)[0]
                    tm = simulate(p, SolverOptions(cell_mm=cell, models=("fvm",))).results["fvm"].t_max
            else:
                with laminate.using(0.1e-3, 16):
                    n = fvm.unknowns(p, cell)[0]
                tm = simulate(p, SolverOptions(cell_mm=cell, models=("fvm",), laminate_s_max_mm=0.1, laminate_n_max=16)).results["fvm"].t_max
            dt = time.time() - t0
            rows.append(dict(cell=cell, rule=name, unknowns=int(n), t_max=tm, sec=dt))
            print(f"  {cell:g} mm {name:10s} unknowns {n:7d}  T_max {tm:8.3f} degC  {dt:5.1f} s (wall time under load)", flush=True)
    return rows


def _rise(p, cell, s=None, n=None):
    """!
    @brief FVM hottest rise.
    @param p Problem.
    @param cell Cell in mm.
    @param s laminate_s_max_mm (None: default).
    @param n laminate_n_max.
    @return float in K.
    """
    kw = {} if s is None else dict(laminate_s_max_mm=s, laminate_n_max=n)
    return simulate(p, SolverOptions(cell_mm=cell, models=("fvm",), **kw)).results["fvm"].t_max - cases.T0


def part_edge(heavy):
    """!
    @brief The edge nodes against their margin, nodes everywhere and the 3D solver.
    @param heavy True to add the 3D solver at 0.5 mm.
    @return list of row dicts.
    """
    rows = []
    print("edge: 60 x 40 mm, two layers, 3.2 mm, h_side 200, faces 10; error of the hottest rise in % against the 3D solver at 1 mm, 8 sub-slabs")
    for pos in ("corner", "centre"):
        p, xy = cases.board(60, 40, 2, 3.2, 200.0, pos)
        r1 = cases.ref3d(p, xy, 1.0, sub=8)
        r05 = cases.ref3d(p, xy, 0.5, sub=8) if heavy else None
        out, unk = {}, {}
        for cell in (0.5, 1.0):
            out[f"default {cell}"] = _rise(p, cell)
            m_gap = laminate.margin_cells(float(p.board.gap_thicknesses()[0]), cell * 1e-3)      # the band one gap thickness plus a cell wide (the rule's own margin)
            for m in (0, 1, 2, 4, m_gap):
                with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=m):
                    key = f"edge m{m} {cell}" if m != m_gap else f"edge band d+dx ({m} cells) {cell}"
                    out[key] = _rise(p, cell)
                    unk[key] = int(fvm.unknowns(p, cell)[0])
            unk[f"default {cell}"] = int(fvm.unknowns(p, cell)[0])
            for z in p.zones:
                z.fill = 0.9999
            out[f"everywhere {cell}"] = _rise(p, cell)
            unk[f"everywhere {cell}"] = int(fvm.unknowns(p, cell)[0])
            out[f"everywhere (0.1,16) {cell}"] = _rise(p, cell, 0.1, 16)
            for z in p.zones:
                z.fill = 1.0
        rows.append(dict(pos=pos, ref_1mm=r1, ref_05mm=r05, out=out, unknowns=unk))
        print(f"  {pos}: 3D at 1 mm {r1:.3f} K" + (f", at 0.5 mm {r05:.3f} K" if r05 else ""), flush=True)
        for k, v in out.items():
            print(f"    {k:32s} {v:8.3f}  {100 * (v / r1 - 1):+6.2f} %" + (f"  ({unk[k]} unknowns)" if k in unk else "")
                  + (f"  (vs 3D 0.5 mm {100 * (v / r05 - 1):+6.2f} %)" if r05 else ""), flush=True)
    return rows


def part_stack():
    """!
    @brief The 4-layer residual: simple stack-up against an advanced stack-up with the same gaps.
    @return list of row dicts.
    """
    rows = []
    print("stack: 60 x 40 mm, four layers, 1.6 mm, h_side 200, corner; nodes everywhere (fill 0.9999), FVM 0.5 mm, against the 3D solver at 1 mm, 8 sub-slabs")
    p, xy = cases.board(60, 40, 4, 1.6, 200.0, "corner")
    r1 = cases.ref3d(p, xy, 1.0, sub=8)
    q = copy.deepcopy(p)
    d = q.board.dielectric_thickness()
    q.board.dielectrics = [Dielectric(thickness=d, k_through=q.board.materials.k_fr4_through, k_inplane=q.board.materials.k_fr4_inplane) for _ in range(3)]
    for name, pp in (("simple", p), ("advanced, same gaps", q)):
        for z in pp.zones:
            z.fill = 0.9999
        v = _rise(pp, 0.5)
        for z in pp.zones:
            z.fill = 1.0
        rows.append(dict(stack=name, slabs_um=[float(x * 1e6) for x in pp.board.slab_thicknesses()], rise=v, ref=r1))
        print(f"  {name:20s} slabs {[round(x * 1e6) for x in pp.board.slab_thicknesses()]} um: {v:.3f} K, {100 * (v / r1 - 1):+6.2f} %", flush=True)
    return rows


def main(argv=None):
    """!
    @brief Run the parts asked for (all by default).
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    parts = [a for a in argv if not a.startswith("--")] or ["cells", "many", "edge", "stack"]
    out = {}
    for part in parts:
        out[part] = {"cells": part_cells, "many": part_many, "stack": part_stack}[part]() if part != "edge" else part_edge("--heavy" in argv)
    (_boot26.OUT / "study_review_checks.json").write_text(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
