#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_branch4.py
@brief The independent checks of the review of FEM branch 4 (`releases/2.8.0/fem-model/REVIEW_BRANCH4.md`): is the face flux of a part on thick outer copper right and continuous,
       how close is case 2 of Muzychka, Culham and Yovanovich at the converged node, what the 0.4 to 0.9 % between the FEM and the FVM is, and does a hollow via match the research FEM.
@details Parts (one per argument): `flux` (a 40 x 30 mm two-layer board at 35, 100, 110 and 400 um: the FEM with the face flux, the FEM with the volumetric source of a copy of
         `femmesh.build`, the FVM and the independent finite volumes of `research/solid3d-verification/lib/layered3d.py`, a flux on the top face); `case2` (the node at each source
         centroid on the top face, FR-4 film and conductive film, cells 2 to 0.5 mm, refinement 1 to 4); `converge` (the heater surface mean of the 35 um board, the FEM converging
         from below, the finite volumes from above); `plain` (two four-layer boards against the FVM, FDM and 3D solid, CG against direct); `hollow` (the program FEM on the strong-edge
         board with and without an open via; the research tool is run by `hollow_research` in a separate process because its module names `fem` and `board` are bare).
         Needs pyamg for the meshes above 30 000 unknowns. Heavy: `case2` peaks at about 3 GB (828 000 unknowns), the others under 1 GB. Run from the repository root:

         .venv/bin/python releases/2.8.0/fem-model/scripts/study_review_branch4.py flux case2 converge plain hollow hollow_research
"""

import os
import subprocess
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "solid3d-verification", "lib"))

import numpy as np                                                       # noqa: E402

from pcbthermal import fem, femmesh                                     # noqa: E402
from pcbthermal.api import SolverOptions, simulate                      # noqa: E402
from pcbthermal.model import Materials, Problem                         # noqa: E402

CENTROIDS = [(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)]   # case 2: source centroids in mm
PAPER = [97.40, 103.82, 101.28, 99.94]                                  # case 2: Table 4 of the paper, degC


def volumetric_build():
    """!
    @brief A copy of `femmesh.build` with the face-flux branch of a part on thick outer copper switched off (every part a volumetric source), for the comparison only.
    @return Callable with the signature of femmesh.build.
    """
    src = open(femmesh.__file__).read()
    key = "if len(slabs_l) > 1 and (h.layer == 0 or h.layer == L - 1):"
    assert src.count(key) == 1, "the face-flux branch of femmesh.build changed: update this study"
    mod = types.ModuleType("pcbthermal.femmesh_volumetric")
    mod.__package__ = "pcbthermal"                                      # the relative imports of the copy resolve in the program package
    exec(compile(src.replace(key, "if False:"), "femmesh_volumetric", "exec"), mod.__dict__)
    return mod.build


def solve(problem, cell, variant="face", **kw):
    """!
    @brief Solve with the program FEM, with the face flux (the program) or the volumetric copy.
    @param problem A Problem.
    @param cell Cell in mm.
    @param variant "face" or "volumetric".
    @param kw Passed to fem.solve_steady.
    @return SteadyResult.
    """
    if variant == "face":
        return fem.solve_steady(problem, cell_mm=cell, **kw)
    old = fem.femmesh.build
    fem.femmesh.build = volumetric_build()
    try:
        return fem.solve_steady(problem, cell_mm=cell, **kw)
    finally:
        fem.femmesh.build = old


def two_layer(t_um):
    """!
    @brief The 40 x 30 mm two-layer board of the flux and convergence parts: full copper, isotropic laminate 0.3 W/mK, h 10 on both faces, insulated edge, 6 mm part of 1 W.
    @param t_um Copper thickness in um.
    @return Problem.
    """
    p = Problem.new(40, 30, layers=2, thickness_mm=1.6, copper_um=t_um, h_top=10.0, h_bottom=10.0, h_side=None,
                    materials=Materials(k_fr4_inplane=0.3, k_fr4_through=0.3))
    p.add_full_copper([1, 2])
    p.add_heater(1, 1.0, rect=(17, 12, 23, 18), name="U1")
    return p


def reference_3d(p, dx_mm, n_cu, n_gap):
    """!
    @brief The independent finite volumes on the two-layer board (a flux on the top face, the film also under the source as in the program).
    @param p Problem of two_layer.
    @param dx_mm Cell in mm.
    @param n_cu Sub-slabs per copper layer.
    @param n_gap Sub-slabs in the laminate.
    @return Tuple (heater surface mean rise, heater column mean rise) in K.
    """
    import layered3d
    b = p.board
    t, d = b.copper_thickness[0], b.gap_thicknesses()[0]
    r = layered3d.solve(dx_mm * 1e-3, int(round(40 / dx_mm)), int(round(30 / dx_mm)), [(t, b.materials.k_copper, n_cu), (d, 0.3, n_gap), (t, b.materials.k_copper, n_cu)],
                        (17e-3, 12e-3, 23e-3, 18e-3), 1.0, 10.0, 10.0, film_under_source=True)
    m = r["mask_source"]
    return float(r["mean_source"]), float(np.mean([r["T"][k][m].mean() for k in range(n_cu)]))


def heater_means(r, cell):
    """!
    @brief Surface and column means of the FEM over the 6 x 6 mm part of two_layer.
    @param r SteadyResult.
    @param cell Cell in mm.
    @return Tuple (surface rise, column rise) in K.
    """
    n = int(round(1 / cell))
    hm = np.zeros(r.T.shape[1:], bool)
    hm[12 * n:18 * n, 17 * n:23 * n] = True
    return float(r.arrays["T_surface"][0][hm].mean() - r.ambient), float(r.T[0][hm].mean() - r.ambient)


def part_flux():
    """!
    @brief Face flux against volumetric source at 35, 100, 110 and 400 um, with the FVM and the independent 3D.
    @return None.
    """
    for t_um in (35.0, 100.0, 110.0, 400.0):
        p = two_layer(t_um)
        s3, c3 = reference_3d(p, 1.0, max(2, int(np.ceil(p.board.copper_thickness[0] / 25e-6))), 16)
        row = [f"t {t_um:5.0f} um: 3D surface {s3:.4f} column {c3:.4f}"]
        for variant in ("face", "volumetric"):
            s, c = heater_means(solve(p, 1.0, variant), 1.0)
            row.append(f"FEM {variant} surface {s:.4f} column {c:.4f}")
        v = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
        row.append(f"FVM column {v.T[0][12:18, 17:23].mean() - v.ambient:.4f}")
        print(" | ".join(row), flush=True)


def case2(conductive_film):
    """!
    @brief Case 2 of Muzychka, Culham and Yovanovich (2003) as a one-layer Problem (the 10 mm plate is the copper; the Problem needs a laminate of 1 um).
    @param conductive_film True: the 1 um film has the plate's conductivity; False: FR-4.
    @return Problem.
    """
    mat = Materials(k_copper=150.0, k_fr4_through=150.0, k_fr4_inplane=150.0) if conductive_film else Materials(k_copper=150.0)
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=mat)
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip(CENTROIDS, [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    return p


def part_case2():
    """!
    @brief The node at each centroid (FR-4 and conductive film, cells and refinements), the 2 x 2 mm mean the test reads, and the volumetric source.
    @return None.
    """
    for film in (False, True):
        p = case2(film)
        for cell, ref in ((2.0, 2.0), (1.0, 1.0), (1.0, 2.0), (1.0, 4.0), (0.5, 2.0), (0.5, 4.0)):
            mesh = femmesh.build(p, cell, 6, ref)
            th = mesh.model.solve()["T"]
            s0 = [s for s, sl in enumerate(mesh.slabs) if sl["region"] == "board"][0]
            nodes = np.unique(mesh.model.elems[mesh.elem_slab == s0][:, :4])
            X = mesh.model.nodes[nodes]
            vals = [25.0 + th[nodes[int(np.argmin(np.hypot(X[:, 0] - cx * 1e-3, X[:, 1] - cy * 1e-3)))]] for cx, cy in CENTROIDS]
            print(f"case 2 node, {'conductive' if film else 'FR-4'} film, cell {cell} refinement {ref}: " + " / ".join(f"{v:.3f}" for v in vals)
                  + "  (paper " + " / ".join(f"{v:.2f}" for v in PAPER) + ")", flush=True)
    for variant in ("face", "volumetric"):
        r = solve(case2(False), 1.0, variant)
        S, T = r.arrays["T_surface"][0], r.T[0]
        centred = [(S[int(cy), int(cx)], T[int(cy), int(cx)]) for cx, cy in CENTROIDS]             # the 1 mm cell whose centre is the centroid
        offset = [(S[round(cy) - 1:round(cy) + 1, round(cx) - 1:round(cx) + 1].mean(), 0.0) for cx, cy in CENTROIDS]   # the first test's window: round() to even, 0.5 mm off
        for name, vals in (("centred 1 mm cell", centred), ("2 x 2 mm window of the first test", offset)):
            print(f"case 2 {name}, {variant} source, FR-4 film: surface " + " / ".join(f"{s:.3f}" for s, _ in vals)
                  + ("; column " + " / ".join(f"{c:.3f}" for _, c in vals) if name.startswith("centred") else ""), flush=True)


def part_converge():
    """!
    @brief The heater surface mean of the 35 um board: the FEM from below, the independent finite volumes from above.
    @return None.
    """
    p = two_layer(35.0)
    for dx, n_gap in ((1.0, 16), (0.5, 16), (0.25, 12)):
        print(f"finite volumes dx {dx} mm: heater surface mean {reference_3d(p, dx, 2, n_gap)[0]:.4f} K", flush=True)
    for cell, ref, gap in ((1.0, 1.0, 6), (1.0, 2.0, 6), (1.0, 4.0, 6), (0.5, 2.0, 6), (1.0, 2.0, 12)):
        print(f"FEM cell {cell} refinement {ref} gap elements {gap}: heater surface mean {heater_means(fem.solve_steady(p, cell_mm=cell, refine=ref, gap_elements=gap), cell)[0]:.4f} K",
              flush=True)


def part_plain():
    """!
    @brief Two plain four-layer boards against the FVM, FDM and 3D solid at 2 mm; CG against direct.
    @return None.
    """
    for w, h in ((60.0, 40.0), (40.0, 30.0)):
        p = Problem.new(width_mm=w, height_mm=h, layers=4, h_top=10.0, h_bottom=10.0, h_side=None)
        p.add_full_copper([1, 2, 3, 4])
        p.add_heater(1, 1.0, rect=(w / 2 - 3, h / 2 - 3, w / 2 + 3, h / 2 + 3), name="U1")
        rows = {m: simulate(p, SolverOptions(models=(m,), cell_mm=2.0)).results[m].delta_t for m in ("fvm", "solid3d", "fdm")}
        for cell in (2.0, 1.0):
            rd = fem.solve_steady(p, cell_mm=cell, force_solver="direct")
            rc = fem.solve_steady(p, cell_mm=cell, force_solver="cg")
            print(f"plain {w:.0f} x {h:.0f} mm, cell {cell}: FEM column {rd.delta_t:.3f} node {rd.extras['t_max_point'] - rd.ambient:.3f} K; at 2 mm FVM {rows['fvm']:.3f} "
                  f"3D {rows['solid3d']:.3f} FDM {rows['fdm']:.3f}; CG - direct {float(np.abs(rd.T - rc.T).max()):.1e} K; balance {rd.balance_error:.1e}; "
                  f"{int(rd.extras['unknowns'])} unknowns", flush=True)


def part_hollow():
    """!
    @brief The program FEM on the strong-edge board of the research (10 x 10 mm, 4 layers, h 10 / 200 / 200) with and without an open via at (7, 5) mm.
    @return None.
    """
    for cell in (1.0, 0.5, 0.25):
        res = []
        for via in (False, True):
            p = Problem.new(10, 10, layers=4, thickness_mm=1.6, h_top=10.0, h_bottom=200.0, h_side=200.0, materials=Materials(k_fr4_inplane=0.3, k_fr4_through=0.3))
            p.add_full_copper([1, 2, 3, 4])
            p.add_heater(1, 0.5, rect=(1, 4, 4, 6), name="U1")
            if via:
                p.add_via(7.0, 5.0, diameter=0.3)
            r = fem.solve_steady(p, cell_mm=cell)
            n = int(round(1 / cell))
            hm = np.zeros(r.T.shape[1:], bool)
            hm[4 * n:6 * n, 1 * n:4 * n] = True
            res.append((r.extras["t_max_point"] - r.ambient, float(r.arrays["T_surface"][0][hm].mean() - r.ambient), r.extras["patches"], r.extras["rods"]))
        a, b = res
        print(f"program FEM cell {cell}: hottest node {a[0]:.4f} / {b[0]:.4f}, heater mean {a[1]:.4f} / {b[1]:.4f} K (without / with the via; {b[2]:.0f} patch, {b[3]:.0f} rod); "
              f"via effect {a[0] - b[0]:.4f} and {a[1] - b[1]:.4f} K", flush=True)


HOLLOW_RESEARCH = r'''
import sys
sys.path[:0] = sys.argv[1:3]
import cases, hollow
for hf in (0.2, 0.1):
    a = cases.strong_edge(200, hf=hf, hmax=0.5).solve()
    b = hollow.strong_board(200, [(7.0, 5.0)], hf=hf, hmax=0.5, core="open").solve()
    print(f"research FEM hf {hf}: hottest node {a['tmax']:.4f} / {b['tmax']:.4f}, heater mean {a['heater_mean']:.4f} / {b['heater_mean']:.4f} K; "
          f"via effect {a['tmax'] - b['tmax']:.4f} and {a['heater_mean'] - b['heater_mean']:.4f} K", flush=True)
'''


def part_hollow_research():
    """!
    @brief The research finite-element tool on the same board, in a separate process (its module names are bare).
    @return None.
    """
    lib = [os.path.join(ROOT, "research", "independent-fem-extensions", "lib"), os.path.join(ROOT, "research", "independent-fem-edge", "lib")]
    subprocess.run([sys.executable, "-c", HOLLOW_RESEARCH] + lib, check=True)


def main(argv):
    """!
    @brief Run the parts named on the command line (all when none).
    @param argv Part names.
    @return None.
    """
    parts = {"flux": part_flux, "case2": part_case2, "converge": part_converge, "plain": part_plain, "hollow": part_hollow, "hollow_research": part_hollow_research}
    for name in (argv or list(parts)):
        parts[name]()


if __name__ == "__main__":
    main(sys.argv[1:])
