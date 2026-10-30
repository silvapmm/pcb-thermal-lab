#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The review checks of this folder: do the claims hold against references written by the reviewer, and are the assumed constants of the proposals safe?
@details Part 1 (`unit`): the unit cell against the reviewer's axisymmetric 3D solver with the real barrel (`lib/review_refs.axisym_3d`) and the layered disc (`axisym_layered`),
         read on the maximum and on the mean of the top copper; the program's Lumped and Analytic, the proposals and the one-cell closed form with the Krogh well at
         r_t = exp(-1/4) r_v and at r_v.
         Part 2 (`kinds`): a lone via, a row, 3 x 3 arrays and a pad against the reviewer's Cartesian layered solver (`cartesian_layered`, two cell sizes).
         Part 3 (`macro`): the factor of the cluster (macro) term of the Lumped proposal on the simple boards and on the example board with denser and larger arrays
         (reference: the corrected FVM at 0.25 mm, as in `study_real_boards.py`).
         Part 4 (`analytic`): the constants of the Analytic proposal (tile cap, isolation, guard), the Green function with 64 modes against 128 and 300 on the example board,
         a 0.5 mm pitch array (not in the study) and the coarsening above 1200 active tiles.
Usage: python research/lumped-analytic-vias/scripts/study_review.py [unit kinds macro analytic]   (from the repository root; about 15 minutes for all)
"""

import inspect
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import analytic_patch as ap                                                  # noqa: E402
import cases                                                                 # noqa: E402
import constriction as cr                                                    # noqa: E402
import harness as hz                                                         # noqa: E402
import lumped_patch as lp                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402
import review_refs as rr                                                     # noqa: E402
import study_real_boards as srb                                              # noqa: E402


def one_cell(par, R, a, constriction=True):
    """!
    @brief Rise of the top node of the one-cell network of a disc cell (one node per sheet, dielectric, Kron-reduced barrel with Krogh wells).
    @param par layer_parameters of the board.
    @param R Cell radius in m.
    @param a Sink radius in m.
    @param constriction False: the barrel joins the sheet means directly (the program's Lumped model on this cell).
    @return float Rise in K for 1 W.
    """
    S, L = par["S"], len(par["S"])
    A = math.pi * R * R
    K = np.zeros((L, L))
    for l in range(L - 1):
        g = par["gz_area"][l] * A
        K[l, l] += g
        K[l + 1, l + 1] += g
        K[l, l + 1] -= g
        K[l + 1, l] -= g
    wells = np.array([1.0 / rr.krogh_disc(S[l], R, a) if constriction else np.inf for l in range(L)])
    G = cr.kron_barrel(par["gv"][0], wells)
    for i in range(L):
        for j in range(i + 1, L):
            K[i, i] += G[i, j]
            K[j, j] += G[i, j]
            K[i, j] -= G[i, j]
            K[j, i] -= G[i, j]
    K[L - 1, L - 1] += par["h_bottom"] * A
    q = np.zeros(L)
    q[0] = 1.0
    return float(np.linalg.solve(K, q)[0])


def part_unit():
    """!
    @brief Part 1: the unit cell against the reviewer's axisymmetric references.
    @return None.
    """
    print("## 1. Unit cell against the reviewer's axisymmetric 3D solver (error of E in percent of E_3D read on the maximum)\n")
    print("| layers | drill | pitch | fill | E_3D max K | E_3D mean K | layered disc, max | layered disc, mean | L_prog | L_ring | A_prog | A_fin | Krogh r_t | Krogh r_v |")
    print("| --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for L, dia, p, f in [(2, 0.3, 4, 0.0), (2, 0.3, 4, 385.0), (2, 0.3, 8, 385.0), (2, 0.6, 8, 385.0), (4, 0.3, 8, 385.0), (4, 0.6, 4, 385.0), (2, 0.3, 2, 385.0), (4, 1.0, 8, 0.0)]:
        prob = pc.unit_cell_board(p, dia, f, layers=L)
        par = pc.layer_parameters(prob)
        b = prob.board
        R = p * 1e-3 / math.sqrt(math.pi)
        rv = dia / 2 * 1e-3
        t1 = rr.axisym_3d(L, float(b.copper_thickness[0]), float(par["d"][0]), R, rv, b.via_plating, f)
        t0 = rr.axisym_3d(L, float(b.copper_thickness[0]), float(par["d"][0]), R, rv, b.via_plating, f, via=False)
        e3 = t0[0] - t1[0]
        l1 = rr.axisym_layered(par["S"], par["gz_area"], par["h_bottom"], R, rv, par["gv"][0])
        # The board without the via is uniform: its rise is that of the one-cell network without barrel
        par0 = dict(par)
        par0["gv"] = [np.zeros_like(par["gv"][0])]
        t_nv = one_cell(par0, R, rv, False)
        q0 = hz.no_vias(prob)
        ev = {n: hz.effect(prob, hz.VARIANTS[n][0], hz.VARIANTS[n][1], 0.5, q0) for n in ("L_prog", "L_ring", "A_prog", "A_fin")}
        pct = lambda e: f"{100 * (e / e3 - 1):+.1f}"
        print(f"| {L} | {dia} | {p} | {'Cu' if f else 'open'} | {e3:.2f} | {t0[1] - t1[1]:.2f} | {pct(t_nv - l1[0])} | {pct(t_nv - l1[1])} | {pct(ev['L_prog'])} | "
              f"{pct(ev['L_ring'])} | {pct(ev['A_prog'])} | {pct(ev['A_fin'])} | {pct(t_nv - one_cell(par, R, cr.ETA * rv))} | {pct(t_nv - one_cell(par, R, rv))} |", flush=True)


def part_kinds():
    """!
    @brief Part 2: board kinds against the reviewer's Cartesian layered solver.
    @return None.
    """
    names = ["FVM", "L_prog", "L_grp0", "A_prog", "A_fin"]
    print("\n## 2. Board kinds against the reviewer's Cartesian layered solver (error of E, percent)\n")
    print("| board | E_ref K (cell) | E at twice the cell | study's E_ref K | " + " | ".join(names) + " |")
    print("| :-- | --: | --: | --: |" + " --: |" * len(names))
    boards = [("lone via, 2 layers, 0.3 Cu, 4 mm", pc.lone_via_board(30.0, 0.3, 385.0, 2, 3.0, 4.0), 0.1),
              ("lone via, 4 layers, 0.6 open, 2 mm", pc.lone_via_board(30.0, 0.6, 0.0, 4, 3.0, 2.0), 0.1),
              ("row of 5 at 1 mm, 2 layers, 0.3 Cu", pc.row_board(5, 1.0, 0.3, 385.0), 1 / 16),
              ("3 x 3 at 3.5 mm, 4 layers, 0.3 Cu", cases.array(4, 3, 3.5, 0.3, 385.0), 1 / 12),
              ("3 x 3 at 1 mm, 4 layers, 0.3 Cu", cases.array(4, 3, 1.0, 0.3, 385.0), 1 / 12),
              ("3 x 3 at 1 mm, 4 layers, 0.3 open", cases.array(4, 3, 1.0, 0.3, 0.0), 1 / 12),
              ("pad 5 x 5 at 0.8 mm, 20 mm board, Cu", cases.pad(4, 5, 0.8, 0.3, 385.0, 20.0, 6.0), 1 / 12)]
    for label, prob, dx in boards:
        par = pc.layer_parameters(prob)
        h = prob.heaters[0]
        xs = [q[0] for q in h.polygon]
        ys = [q[1] for q in h.polygon]
        rect = (min(xs), min(ys), max(xs), max(ys))
        vias = [(x, y, r, g) for (x, y), r, g in zip(par["xy"], par["r_via"], par["gv"])]

        def e_at(cell):
            # Via effect of the reviewer's solver at one cell size
            args = (par["width"], par["S"], par["gz_area"], par["h_top"], par["h_bottom"], rect, h.power)
            return rr.cartesian_layered(*args, [], cell * 1e-3) - rr.cartesian_layered(*args, vias, cell * 1e-3)
        e = e_at(dx)
        e2 = e_at(2 * dx)
        e_study = hz.reference_uniform(prob)[0]
        er = hz.errors(prob, e, 0.5, names)
        print(f"| {label} | {e:.3f} ({dx:.3f} mm) | {e2:.3f} | {e_study:.3f} | " + " | ".join(f"{er[n]:+.1f}" for n in names) + " |", flush=True)


def part_macro():
    """!
    @brief Part 3: the factor of the Lumped cluster (macro) term, simple boards and the example board with larger arrays.
    @return None.
    """
    factors = (0.0, 0.25, 0.5, 0.75, 1.0)
    print("\n## 3. Lumped proposal: factor of the cluster term (error of E, percent; 1.0 is the proposal, 0.0 the micro well alone)\n")
    print("| board | E_ref K | L_prog | L_ring | " + " | ".join(f"macro {f}" for f in factors) + " |")
    print("| :-- | --: | --: | --: |" + " --: |" * len(factors))
    rows = [("row of 5, 2 layers, Cu", pc.row_board(5, 1.0, 0.3, 385.0), False), ("3 x 3 at 1 mm, 4 layers, Cu", cases.array(4, 3, 1.0, 0.3, 385.0), False),
            ("3 x 3 at 1 mm, 4 layers, open", cases.array(4, 3, 1.0, 0.3, 0.0), False), ("3 x 3 at 2 mm, 4 layers, Cu", cases.array(4, 3, 2.0, 0.3, 385.0), False),
            ("pad 5 x 5 at 0.8 mm, Cu", cases.pad(4, 5, 0.8, 0.3, 385.0, 20.0, 6.0), False)]
    for n, pitch in ((0, 3.5), (5, 1.2), (7, 1.0), (20, 1.0)):
        for fill in (0.0, 385.0):
            rows.append((f"example board, {n} x {n} at {pitch} mm, {'Cu' if fill else 'open'}" if n else f"example board, 9 vias at 3.5 mm, {'Cu' if fill else 'open'}",
                         srb.example(fill, n, pitch), True))
    for label, prob, real in rows:
        q0 = hz.no_vias(prob)
        e = hz.effect(prob, "fvm", hz.VARIANTS["FVM_fix"][1], 0.25, q0) if real else hz.reference_uniform(prob)[0]
        r = [hz.effect(prob, "lumped", hz.VARIANTS[k][1], 0.5, q0) for k in ("L_prog", "L_ring")]
        r += [hz.effect(prob, "lumped", (lambda f=f: lp.patched("krogh", cell="nn", cluster=True, macro_scale=f)), 0.5, q0) for f in factors]
        print(f"| {label} | {e:.3f} | " + " | ".join(f"{100 * (x / e - 1):+.1f}" for x in r) + " |", flush=True)


def _with_modes(mg, **kw):
    """!
    @brief Patched Analytic context whose tile Green function uses mg modes instead of the program's 64 (the source line is changed in the compiled copy only).
    @param mg Number of modes per direction of the tile Green function.
    @param kw Options of analytic_patch.patched.
    @return Context manager.
    """
    import contextlib
    line = "Mg, Ng = min(M, 64), min(N, 64)"

    @contextlib.contextmanager
    def ctx():
        orig = inspect.getsource

        def getsource(obj):
            # Only the source of solve_steady is altered, and only the number of modes of G
            s = orig(obj)
            return s.replace(line, f"Mg, Ng = min(M, {mg}), min(N, {mg})") if getattr(obj, "__name__", "") == "solve_steady" else s
        inspect.getsource = getsource
        try:
            with ap.patched(**kw):
                yield
        finally:
            inspect.getsource = orig
    return ctx


def part_analytic():
    """!
    @brief Part 4: the constants of the Analytic proposal, the modes of its tile Green function and the coarsening.
    @return None.
    """
    fin = dict(mode="on", spread="bilinear", tile_cap=1.0)
    variants = [("A_fin", {}), ("tile 1.5 mm", dict(tile_cap=1.5)), ("tile 2.0 mm", dict(tile_cap=2.0)), ("iso 0.5", dict(iso=0.5)), ("iso 1.0", dict(iso=1.0)),
                ("guard 0", dict(guard=0.0)), ("guard 1.0", dict(guard=1.0))]
    print("\n## 4. Analytic proposal\n\n### 4.1 Its constants (error of E against the study's fine-grid reference, percent)\n")
    print("| board | E_ref K | " + " | ".join(v for v, _ in variants) + " |")
    print("| :-- | --: |" + " --: |" * len(variants))
    boards = [("3 x 3 at 2 mm, 4 layers, Cu", cases.array(4, 3, 2.0, 0.3, 385.0)), ("3 x 3 at 1 mm, 4 layers, Cu", cases.array(4, 3, 1.0, 0.3, 385.0)),
              ("3 x 3 at 1 mm, 4 layers, open", cases.array(4, 3, 1.0, 0.3, 0.0)), ("pad 5 x 5 at 0.8 mm, Cu", cases.pad(4, 5, 0.8, 0.3, 385.0, 20.0, 6.0)),
              ("row of 5, 2 layers, Cu", pc.row_board(5, 1.0, 0.3, 385.0)), ("lone via at 2 mm, 2 layers, Cu", pc.lone_via_board(30.0, 0.3, 385.0, 2, 3.0, 2.0)),
              ("lone via at 4 mm, 2 layers, Cu", pc.lone_via_board(30.0, 0.3, 385.0, 2, 3.0, 4.0)), ("5 x 5 at 0.5 mm, 0.2 mm drill, 2 layers, Cu", cases.array(2, 5, 0.5, 0.2, 385.0))]
    for label, prob in boards:
        e = hz.reference_uniform(prob)[0]
        out = []
        for _, kw in variants:
            k = dict(fin)
            k.update(kw)
            out.append(100 * (hz.effect(prob, "analytic", (lambda k=k: ap.patched(**k)), 0.5) / e - 1))
        print(f"| {label} | {e:.3f} | " + " | ".join(f"{x:+.1f}" for x in out) + " |", flush=True)
    print("\n### 4.2 Modes of the tile Green function (example board; the program builds G from min(M, 64) modes, the study varied M only)\n")
    print("| modes of G | A_fin T_max open degC | copper-fill gain K | program gain K |")
    print("| --: | --: | --: | --: |")
    ex_o, ex_c = srb.example(0.0, 0, 3.5), srb.example(385.0, 0, 3.5)
    amb = ex_o.board.ambient
    for mg in (64, 128, 300):
        with _with_modes(mg, **fin)():
            to = pc.max_rise(ex_o, "analytic", 0.5)
            tc = pc.max_rise(ex_c, "analytic", 0.5)
        with _with_modes(mg, mode="off")():
            go = pc.max_rise(ex_o, "analytic", 0.5) - pc.max_rise(ex_c, "analytic", 0.5)
        print(f"| {mg} | {to + amb:.2f} | {to - tc:.3f} | {go:.3f} |", flush=True)
    print("\n### 4.3 Many vias on the example board (coarsening above 1200 active tiles; copper fill; error of E against the corrected FVM at 0.25 mm, percent)\n")
    print("| array | vias | E_ref K | A_prog | A_fin | A_fin, limit 2400 tiles |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for n, pitch in ((11, 1.0), (20, 1.0), (24, 0.8)):
        prob = srb.example(385.0, n, pitch)
        q0 = hz.no_vias(prob)
        e = hz.effect(prob, "fvm", hz.VARIANTS["FVM_fix"][1], 0.25, q0)
        r = [hz.effect(prob, "analytic", hz.VARIANTS[k][1], 0.5, q0) for k in ("A_prog", "A_fin")]
        ap.MAX_ACTIVE = 2400
        try:
            r.append(hz.effect(prob, "analytic", hz.VARIANTS["A_fin"][1], 0.5, q0))
        finally:
            ap.MAX_ACTIVE = 1200
        print(f"| {n} x {n} at {pitch} mm | {n * n} | {e:.3f} | " + " | ".join(f"{100 * (x / e - 1):+.1f}" for x in r) + " |", flush=True)


def main():
    """!
    @brief Run the parts named on the command line (all by default).
    @return None.
    """
    pc.load_libraries()
    parts = sys.argv[1:] or ["unit", "kinds", "macro", "analytic"]
    for p in parts:
        {"unit": part_unit, "kinds": part_kinds, "macro": part_macro, "analytic": part_analytic}[p]()


if __name__ == "__main__":
    main()
