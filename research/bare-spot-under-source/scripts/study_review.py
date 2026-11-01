#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The reviewer's checks of the folder (README section 9): how far the reference is from a converged value, what the 3D solid reports over a bare cell, how much heat leaves a window sideways, and which part of the vertical correction moves the validation rows.
@details Questions answered, each with code independent of `resolved3d.py`: (1) the converged peak of five cases by a refinement study on the graded grid of `lib/graded3d.py`
         (scales 1.41, 1.0, 0.75, fitted v0 + C s^p), against the reference of the sweeps (0.25 mm, 8 sub-slabs) and the program's FVM, vertical correction and n = 4 nodes;
         (2) the 3D solid of the program at the centre of its top copper slab and at the face (centre plus the half-slab drop of the heat of the part) on the window boards and on
         the validation rows with bare cells; (3) the heat that crosses the window edge sideways in the resolved field (top slab, upper half of the gap) against the heat that the
         program's top node carries out of the window; (4) the vertical correction split into its link and its face term on the three validation rows with bare cells; (5) the vertical correction on a 1D column against the series circuit.
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_review.py [all|column|converge|solid|lateral|rows]; out/review.txt (about 15 minutes).
"""

import _bootstrap  # noqa: F401  (import paths)

import sys

import numpy as np

from _bootstrap import HERE, OUT

import cases as C                                                           # noqa: E402
import graded3d as G                                                        # noqa: E402
import layered as LY                                                        # noqa: E402
import sweep as SW                                                          # noqa: E402
import treatments as TR                                                     # noqa: E402

lines = []
CASES = (("2L 1.6 mm", 6), ("2L 1.6 mm", 2), ("2L 0.8 mm", 6), ("4L typical", 6), ("6L typical", 6))


def say(s):
    """!
    @brief Print and keep a line.
    @param s Text.
    @return None.
    """
    print(s, flush=True)
    lines.append(s)


def converge():
    """!
    @brief (1) The converged peak of five cases and the errors of the program and the treatments against it.
    @return None.
    """
    for stack, w in CASES:
        scales = (1.41, 1.0, 0.75)
        vals = [G.solve(stack, w * 1e-3, s)["peak"] for s in scales]
        v0, p = G.extrapolate(scales, vals)
        case = SW.make_case(stack, w)
        ref = SW.cached_reference(case)["max"]
        pb = C.problem(case)
        net = LY.network(pb, 0.5)
        gaps, kz, kxy = LY.gap_data(pb)
        prog = TR.run(pb, net, {"kind": "none"}, gaps, kz, kxy)["peak"]
        vert = TR.run(pb, net, {"kind": "vert"}, gaps, kz, kxy)["peak"]
        n4 = TR.run(pb, net, {"kind": "nodes", "n": 4, "vert": True}, gaps, kz, kxy)["peak"]
        say(f"(1) {stack}, window {w} mm: graded peaks {' / '.join(f'{v:.3f}' for v in vals)} K at scales {scales}; converged {v0:.2f} K (order {p:.2f}); "
            f"reference of the sweeps {ref:.2f} K ({100 * (ref / v0 - 1):+.2f} %); FVM 0.5 mm {100 * (prog / v0 - 1):+.1f} % (sweeps {100 * (prog / ref - 1):+.1f} %), "
            f"vert {100 * (vert / v0 - 1):+.1f} % ({100 * (vert / ref - 1):+.1f} %), n=4+v {100 * (n4 / v0 - 1):+.1f} % ({100 * (n4 / ref - 1):+.1f} %)")


def solid_face(problem, cell, n_diel=4):
    """!
    @brief The 3D solid of the program: the hottest top-slab centre and the hottest face (centre plus the drop of the heat of the part across half the top slab).
    @param problem A Problem.
    @param cell Cell in mm.
    @param n_diel Sub-slabs per gap.
    @return Tuple (centre rise, face rise) in K.
    """
    from pcbthermal import solid3d
    net = solid3d.Solid(problem, cell, n_diel)
    th, _ = net.solve()
    s0 = net.board_slab[0]
    sl = net.slabs[s0]
    q = net.Q.reshape(th.shape)[s0]
    face = th[s0] + q * sl["dz"] / 2 / (sl["kz"] * net.dx * net.dy)
    return float(th[s0].max()), float(face.max())


def solid():
    """!
    @brief (2) The 3D solid at the slab centre and at the face against the reference.
    @return None.
    """
    for stack, w in (("2L 0.8 mm", 6), ("4L typical", 6), ("6L typical", 6)):
        case = SW.make_case(stack, w)
        ref = SW.cached_reference(case)["max"]
        for cell in (0.5, 0.25):
            try:
                c, f = solid_face(C.problem(case), cell)
            except ValueError:
                continue                                                     # above the size limit of the 3D solid
            say(f"(2) {stack}, window {w} mm, 3D solid at {cell} mm: slab centre {c:.2f} K ({100 * (c / ref - 1):+.2f} %), face {f:.2f} K ({100 * (f / ref - 1):+.2f} %) of the reference {ref:.2f} K")


def lateral():
    """!
    @brief (3) Heat leaving a 6 mm window sideways: the resolved field against the program's top node.
    @return None.
    """
    for stack in ("2L 1.6 mm", "2L 0.8 mm", "4L typical"):
        t_cu, gaps = G.STACKS[stack]
        r = G.solve(stack, 6e-3, 1.0)
        z, q = r["z_top"], r["lateral"]
        top = q[z < t_cu[0] - 1e-12].sum()
        upper = q[(z >= t_cu[0] - 1e-12) & (z < t_cu[0] + gaps[0] / 2 - 1e-12)].sum()
        gap = q[(z >= t_cu[0] - 1e-12) & (z < t_cu[0] + gaps[0] - 1e-12)].sum()
        case = SW.make_case(stack, 6)
        net = LY.network(C.problem(case), 0.5)
        net.K = net._assemble()
        th, _ = net.solve_steady()
        T = th.reshape(net.nl, net.ny, net.nx)[0] if th.ndim == 1 else th[0]
        S = net.S[0]
        gx = 2 * S[:, :-1] * S[:, 1:] / (S[:, :-1] + S[:, 1:]) * net.dy / net.dx
        inside = np.minimum(net.fill[0], 1.0) < 1.0
        rows = np.where(inside.any(axis=1))[0]
        cols = np.where(inside.any(axis=0))[0]
        i = cols[-1]
        out = 4 * (gx[rows, i] * (T[rows, i] - T[rows, i + 1])).sum()   # four equal sides by symmetry
        say(f"(3) {stack}, 6 mm window: resolved field, heat across the window edge: top slab {top:.3f} W, upper half of the gap {upper:.3f} W (sum {top + upper:.3f}), "
            f"whole gap {gap:.3f} W; program FVM 0.5 mm, top node out of the window {out:.3f} W (of 1 W)")


def rows():
    """!
    @brief (4) The validation rows with bare cells: the vertical correction split into link and face term, and the 3D solid at the slab centre and at the face.
    @return None.
    """
    sys.path.append(str(HERE.parent / "models-comparison" / "scripts"))
    import stress_study
    for name, p in stress_study.cases():
        if not any(s in name for s in ("straddling", "no copper on", "hatched")):
            continue
        amb = p.board.ambient
        net = LY.network(p, 1.0)
        gaps, kz, kxy = LY.gap_data(p)
        tcu = [float(x) for x in p.board.copper_thickness]
        a = LY.solve(net, gaps, kz, kxy, [None] * len(gaps), [None] * len(gaps))
        b = LY.solve(net, gaps, kz, kxy, [None] * len(gaps), [None] * len(gaps), tcu=tcu)
        c, f = solid_face(p, 1.0)
        say(f"(4) {name}: program {a['peak'] + amb:.2f}, link only {b['peak_node'] + amb:.2f}, link + face {b['peak'] + amb:.2f} degC; "
            f"3D solid slab centre {c + amb:.2f}, face {f + amb:.2f} degC")


def column():
    """!
    @brief (5) The vertical correction on a 1D column: a part over the whole board, no copper in the top layer, against the series circuit.
    @return None.
    """
    import closed_forms as cf
    for layers, stack in ((2, "simple"), (4, "template")):
        case = C.Case("column", layers=layers, stack=stack, window=(0.0, 0.0, 30.0, 30.0), part=30.0)
        p = C.problem(case)
        nb = C.board_numbers(p)
        net = LY.network(p, 1.0)
        gaps, kz, kxy = LY.gap_data(p)
        slabs = [(nb["t_cu"][0], nb["k_gap_z"][0])]
        for i, d in enumerate(nb["gaps"]):
            slabs += [(d, nb["k_gap_z"][i]), (nb["t_cu"][i + 1], nb["k_cu"])]
        exact = cf.column_rise(1.0, (30e-3) ** 2, slabs, nb["h_top"], nb["h_bottom"])
        a = TR.run(p, net, {"kind": "none"}, gaps, kz, kxy)["peak"]
        b = TR.run(p, net, {"kind": "vert"}, gaps, kz, kxy)["peak"]
        say(f"(5) {layers} layers, 1D column with a bare top layer: series circuit {exact:.4f} K, program {a:.4f} K ({100 * (a / exact - 1):+.3f} %), vert {b:.4f} K ({100 * (b / exact - 1):+.3f} %)")


def main():
    """!
    @brief Run the chosen checks.
    @return None.
    """
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    for key, fn in (("column", column), ("converge", converge), ("solid", solid), ("lateral", lateral), ("rows", rows)):
        if what in ("all", key):
            fn()
    (OUT / f"review{'' if what == 'all' else '_' + what}.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
