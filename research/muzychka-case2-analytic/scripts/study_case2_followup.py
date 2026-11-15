#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_followup.py
@brief Follow-up of the reporter of case 2: what his project defines and what the 3D solid reads from it, and what the 3D solid reads when the plate is a resolved dielectric gap.
@details (1) With a project path (his file is not stored in the repository: pass a copy), prints the board, stack-up, coefficients, sources and solver of the project and the
         3D solid's part rows (the peak of the Results table) and layer-1 centroids and means at the project's cell. (2) Always: the case 2 plate mapped as a dielectric gap of
         k 150 between two 1 um copper layers with full copper zones, so that the 3D solid cuts its thickness into slabs (solid3d.slab_rule); 1 mm and 0.5 mm with the rule and
         1 mm with 32 slabs, against the independent reference. Peak about 3 GB (the 0.5 mm run).
         Run from the repository root: .venv/bin/python -u research/muzychka-case2-analytic/scripts/study_case2_followup.py [project.pcbtz]
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402
from pcbthermal import Problem, SolverOptions, package, simulate, solid3d  # noqa: E402
from pcbthermal.model import Dielectric, Materials  # noqa: E402


def resolved_plate():
    """!
    @brief The case 2 plate as a dielectric gap of the plate's conductivity between two 1 um copper layers (advanced stack-up, full copper, adiabatic top and sides).
    @return Problem.
    """
    p = Problem.new(C.W_MM, C.W_MM, layers=2, thickness_mm=C.T_MM + 0.002, copper_um=1.0, ambient=C.AMB, h_top=0.0, h_bottom=C.H_PAPER, h_side=None,
                    materials=Materials(k_copper=C.K_PLATE))
    p.board.dielectrics = [Dielectric(thickness=C.T_MM * 1e-3, name="plate", k_through=C.K_PLATE, k_inplane=C.K_PLATE)]
    p.board.validate()
    p.add_full_copper(layers=None)
    for i, (c, pw) in enumerate(zip(C.CENTRES, C.POWERS)):
        p.add_heater(1, pw, rect=C.rect(c), name=f"S{i}")
    return p


def show_project(path):
    """!
    @brief Print what the project defines and what the 3D solid reads from it.
    @param path Path of a .pcbt.json or .pcbtz project.
    @return None.
    """
    proj = package.load_any(path)
    p, b = proj.problem, proj.problem.board
    print(f" board {b.width * 1e3:.2f} x {b.height * 1e3:.2f} mm, {b.layers} layers, advanced {b.is_advanced()}, copper {[round(c * 1e3, 4) for c in b.copper_thickness]} mm, "
          f"gaps {[round(g * 1e3, 4) for g in b.gap_thicknesses()]} mm, gap k (through, in-plane) {b.gap_properties()[0].tolist()}, {b.gap_properties()[1].tolist()}, copper k {b.materials.k_copper}")
    print(f" h_mode {b.h_mode}, h_top {b.h_top}, h_bottom {b.h_bottom}, h_side {b.h_side}, ambient {b.ambient}; zones {len(p.zones)}, vias {len(p.vias)}, heatsinks {len(p.heatsinks)}")
    for h in p.heaters:
        print(f"  {h.name}: layer {h.layer + 1}, {h.power} W, polygon {np.round(np.asarray(h.polygon) * 1e3, 2).tolist()}")
    o = proj.options
    print(f" solver: models {o.models}, cell {o.cell_mm} mm; 3D solid slabs per gap {solid3d.slabs_per_gap(p)}")
    sim = simulate(p, SolverOptions(models=("solid3d",), cell_mm=o.cell_mm))
    r = C.readout(sim.results["solid3d"])
    print("  rows t_max", [round(x["t_max"], 2) for x in sim.heater_rows()], " layer-1 centroid", np.round(r["cen"], 2).tolist(), " mean", np.round(r["mean"], 2).tolist())
    print("  paper centroid", C.PAPER_CENTROID)
    for w in sim.warnings:
        print("  WARNING:", w[:160])


def main():
    """!
    @brief Run the follow-up.
    @return None.
    """
    if len(sys.argv) > 1:
        print("1. the reporter's project")
        show_project(sys.argv[1])
    print("\n2. the 3D solid with the plate as a resolved dielectric gap (paper centroid %s, mean %s)" % (C.PAPER_CENTROID, C.PAPER_MEAN))
    p = resolved_plate()
    for cell, nd in ((1.0, None), (1.0, 32), (0.5, None)):
        r = C.readout(solid3d.solve_steady(p, cell_mm=cell, n_diel=nd))
        print(f" cell {cell} mm, slabs {solid3d.slabs_per_gap(p, nd)}: centroid {np.round(r['cen'], 2).tolist()} mean {np.round(r['mean'], 2).tolist()}", flush=True)


if __name__ == "__main__":
    main()
