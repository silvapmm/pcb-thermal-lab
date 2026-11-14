#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plan_costs.py
@brief Which planned finite-element case fits under 2 GB: the unknown count of every case of README 2, counted on plan meshes built by the tool's
       own mesh functions (no assembly, no solve), and the memory estimate from the peaks the tool measured in `independent-fem-edge`.
@details Run from the repository root: `.venv/bin/python research/independent-fem-extensions/scripts/study_plan_costs.py` (NumPy and SciPy only;
         a few seconds). The plan meshes of study 1 are built exactly (`cases.strong_edge` with the via, the O-grid included); the other cases are
         counted from their graded axes (`cases.axis`, the same grading rule) plus the O-grid patches measured on study 1, times the z levels of the
         stack named in the table. Memory law (review of the plan, README 7.2): the tool's measured peaks are 0.93 GB at 138 000 unknowns (CG with the
         scaled AMG, fresh process) and 2.78 GB at 327 000 (the same, the peak of a whole study process), so 8.5 kB per unknown is taken as the upper
         value for CG + AMG; the direct solve measured 2.73 GB at 59 000 unknowns (46 kB per unknown) and 5.2 GB at 138 000, so under a 2 GB budget the
         direct solve is used only up to DIRECT_MAX unknowns. The plan's first constant (3000 bytes per unknown) was 2.8 times too low and its unknown
         counts about three times too high: the two errors partly cancelled.
"""
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "..", "independent-fem-edge", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import cases                                                             # noqa: E402

LOG = logging.getLogger("plan_costs")
B_CG = 8500.0                   # bytes per unknown, CG + AMG, the upper measured value of independent-fem-edge (327 000 unknowns, 2.78 GB)
B_DIRECT = 46000.0              # bytes per unknown, SuperLU symmetric mode (59 000 unknowns, 2.73 GB)
DIRECT_MAX = 30000              # largest direct solve under the 2 GB budget (the tool's default direct_max is 60 000: 2.7 GB)
LIMIT_GB = 2.0                  # the budget of a run while the machine is shared


def gb(n):
    """!
    @brief Estimated peak memory of one solve.
    @param n Unknowns.
    @return float GB.
    """
    return n * (B_DIRECT if n <= DIRECT_MAX else B_CG) / 1e9


def plan_nodes(xn, yn):
    """!
    @brief Nodes of a tensor plan mesh.
    @param xn Axis nodes in x.
    @param yn Axis nodes in y.
    @return int.
    """
    return xn.size * yn.size


def main():
    """!
    @brief Print the cost table.
    @return None.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rows = []
    # Study 1: the board of independent-fem-edge 3(b) with the via, built exactly; slabs 4 copper + 3 x 6 gap = 22, plus 4 O-grid rings for a
    # 25 um wall (4 n_side nodes per ring, n_side 8) per level
    patch = {}
    for hf in (0.2, 0.1, 0.05):
        for d in (0.16, 3.0):
            b = cases.strong_edge(200.0, hf=hf, via_dist=d)
            nb = cases.strong_edge(200.0, hf=hf).plan.xy.shape[0]
            npl = b.plan.xy.shape[0] + 4 * 4 * 8
            patch[hf] = max(patch.get(hf, 0), b.plan.xy.shape[0] - nb + 4 * 4 * 8)
            rows.append((f"1a hollow barrel d {d} mm, half, hf {hf}", npl * (b.dz.size + 1)))
    for hf in (0.2, 0.1, 0.05):
        b = cases.strong_edge(200.0, hf=hf, via_dist=3.0)
        rows.append((f"1b 3 x 3 array, half (+5 patches), hf {hf}", (b.plan.xy.shape[0] + 4 * 4 * 8 + 5 * patch[hf]) * (b.dz.size + 1)))
    # Study 2: quarter 10 x 10 mm, tab 6 x 6 (0..3 mm in the quarter), 4 x 4 cluster at 0.8 mm (2 x 2 in the quarter); board 22 slabs, interface 2,
    # plate 4 (whole plan); tab 2 + solder 2 slabs only over the tab region
    for hf in (0.2, 0.1, 0.05, 0.025):
        xn = cases.axis(10.0, [3.0], [(0, 3.3)], hf, 1.3, 0.5)
        npl = plan_nodes(xn, xn) + 4 * patch.get(hf, patch[0.05] * 4)
        tab = int((3.0 / hf + 1) ** 2)
        rows.append((f"2 tab over cluster, plate, quarter, hf {hf}", npl * (22 + 2 + 4 + 1) + tab * 4))
    # Study 3: aligned stripes on a 20 mm square, quarter, stripes resolved by 2 elements of 0.125 mm across the striped 10 mm, 2 layers (14 slabs)
    xn = cases.axis(10.0, [], [(0, 10.0)], 0.125, 1.3, 0.5)
    yn = cases.axis(10.0, [], [(0, 0.6)], 0.2, 1.3, 0.8)
    rows.append(("3 stripes aligned, 20 mm square, quarter", plan_nodes(xn, yn) * 15))
    # Study 4: L outline with 20 mm arms, two layers (14 slabs), whole domain, fine zones at the walls, the reflex corner and the heater
    for hf in (0.2, 0.1):
        xn = cases.axis(20.0, [6.4, 8.8, 11.2], [(0, 0.6), (5.8, 7.0), (8.2, 11.8), (19.4, 20)], hf, 1.3, 0.8)
        rows.append((f"4 L outline, whole, hf {hf}", int(0.75 * plan_nodes(xn, xn)) * 15))
    # Study 5: the 60 x 40 mm board of research/fast-wave-oscillation, quarter (30 x 20 mm), 10 mm part (5 mm in the quarter), 2 layers with
    # 20 graded elements per gap for a 20 Hz wave (22 slabs)
    for hf in (0.4, 0.2, 0.1):
        xn = cases.axis(30.0, [5.0], [(0, 5.3)], hf, 1.3, 1.0)
        yn = cases.axis(20.0, [5.0], [(0, 5.3)], hf, 1.3, 1.0)
        rows.append((f"5 fast-wave board, quarter, hf {hf}", plan_nodes(xn, yn) * 23))
    LOG.info("%-48s %10s %8s  %-6s  %s", "case", "unknowns", "GB est.", "solver", "under %.0f GB" % LIMIT_GB)
    for name, n in rows:
        g = gb(n)
        LOG.info("%-48s %10d %8.2f  %-6s  %s", name, n, g, "direct" if n <= DIRECT_MAX else "cg+amg", "yes" if g < LIMIT_GB else "WAIT")


if __name__ == "__main__":
    main()
