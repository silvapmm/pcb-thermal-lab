#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_t0.py
@brief Row 57.0 of the FEM campaign (validation 57, first line): the published transient case NAFEMS T3 reproduced on this tree (exact series, method of lines, the program's FEM at
       several meshes and steps, the published mesh results of MOOSE and Abaqus) and the plate with held edges against the exact double series in the FVM, FDM and Analytic.
@details It re-runs, unchanged, parts A and B of `research/transient-published-case/scripts/study_t3_and_plate.py` (the exact series and the helper `lib/exact1d.py` import nothing
         from the program), so the numbers of the first line of validation 57 are printed by the tree that ships and not quoted. Sources by key of
         `research/theory/BIBLIOGRAPHY.md`: [NAFEMS-T3] (the primary publication was not obtained), [MOOSE-T3], [Abaqus-T3], [Altair-T3], [Wolfram-T3].
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_t0.py` (about 1 min, light; output also in out/t0.txt); `--stepping` prints only the review's separation of the stepping on the plate (about 8 min).
"""

import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STUDY = ROOT / "research" / "transient-published-case" / "scripts" / "study_t3_and_plate.py"


def part_b_fem(mod):
    """!
    @brief The plate with held edges and a power step in the FVM, FDM, FEM and Analytic at the program's default stepping, the centre temperature against the exact Robin double series.
    @details The part B of the research study labels its runs 'implicit Euler' and 'Crank-Nicolson' by the keyword `theta_scheme`; since 2.9.0 the default is Crank-Nicolson with the
             Rannacher start and the first stage in quarter steps, so its 'implicit Euler' line IS that default (the two lines print the same digits); this part runs the default only
             and adds the FEM, which holds the edge as a film of 1e5 W/m2K like the others.
    @param mod The imported study module (the plate, the exact series and the edge film).
    @return None.
    """
    import numpy as np
    from pcbthermal import analytic, fdm, fem, fvm
    p, rc, k, th, power = mod.plate_problem()
    qvol = power / (0.1 * 0.1 * th)
    tau = rc * 0.1 ** 2 / (k * np.pi ** 2 * 2)
    t_end = 2.0 * tau
    print(f"B0 plate 0.1 m square, 1 mm, k 35, rho c {rc:.4g}, P {power} W, edge film {mod.H_EDGE:.0e} W/m2K, slowest-mode tau {tau:.1f} s, run to {t_end:.0f} s, 20 frames, default stepping")
    print("   largest relative error of the centre column temperature over the frames after 10 s, against the exact Robin double series")
    print("| model | 5 mm | 2.5 mm | 1.25 mm |\n| :-- | --: | --: | --: |")
    for name, m in (("FVM", fvm), ("FDM", fdm), ("FEM", fem), ("Analytic", analytic)):
        row = []
        for cell in (5.0, 2.5, 1.25):
            r = m.solve_transient(p, t_end, n_out=20, cell_mm=cell)
            fr = np.asarray(r.frames)[:, 0]
            ny, nx = fr.shape[1:]
            xs = np.linspace(0.0, 0.1, nx) if r.grid == "nodes" else (np.arange(nx) + 0.5) * 0.1 / nx
            i = ny // 2
            errs = [float(fr[j, i, i] / mod.E.square_plate_robin_heating(xs[i], xs[i], t, 0.1, k, rc, qvol, mod.H_EDGE, n_roots=40) - 1.0) for j, t in enumerate(r.times) if t > 10.0]
            row.append(f"{100 * max(abs(e) for e in errs):.2f} %")
        print(f"| {name} | " + " | ".join(row) + " |")


def part_b_stepping(mod):
    """!
    @brief Review: separate the stepping from the model on the held-edge plate at the 2.9.0 default: the default (20 logarithmic frames) against 40 linear frames of 16 steps.
    @details `substeps` does not act on a logarithmic grid (one step per frame there), so the finer run is linear. The FEM is run at 2.5 mm only (the 1.25 mm linear run takes
             more than ten minutes).
    @param mod The imported study module (the plate, the exact series and the edge film).
    @return None.
    """
    import numpy as np
    from pcbthermal import fdm, fem, fvm
    p, rc, k, th, power = mod.plate_problem()
    qvol = power / (0.1 * 0.1 * th)
    t_end = 2.0 * rc * 0.1 ** 2 / (k * np.pi ** 2 * 2)

    def worst(r):
        """!
        @brief Largest relative error of the centre column temperature after 10 s against the exact series, and its time.
        @param r TransientResult.
        @return tuple (error, time in s).
        """
        fr = np.asarray(r.frames)[:, 0]
        ny, nx = fr.shape[1:]
        xs = np.linspace(0.0, 0.1, nx) if r.grid == "nodes" else (np.arange(nx) + 0.5) * 0.1 / nx
        i = ny // 2
        e = [(float(fr[j, i, i] / mod.E.square_plate_robin_heating(xs[i], xs[i], t, 0.1, k, rc, qvol, mod.H_EDGE, n_roots=40) - 1.0), float(t))
             for j, t in enumerate(r.times) if t > 10.0]
        return max(e, key=lambda a: abs(a[0]))

    print("B1 (review) the same plate: default stepping against 40 linear frames of 16 steps, largest error after 10 s [%] (time of it)")
    print("| model | cell mm | default | linear 40 x 16 |\n| :-- | --: | --: | --: |")
    for name, m, cells in (("FVM", fvm, (2.5, 1.25)), ("FDM", fdm, (2.5, 1.25)), ("FEM", fem, (2.5,))):
        for cell in cells:
            a = worst(m.solve_transient(p, t_end, n_out=20, cell_mm=cell))
            b = worst(m.solve_transient(p, t_end, n_out=40, substeps=16, log_times=False, cell_mm=cell))
            print(f"| {name} | {cell:g} | {100 * a[0]:+.3f} ({a[1]:.1f} s) | {100 * b[0]:+.3f} ({b[1]:.1f} s) |", flush=True)


def main():
    """!
    @brief Run parts A and B of the published-case study and print them with the tree.
    @return None.
    """
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("study_t3_and_plate", STUDY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    if "--stepping" in sys.argv[1:]:
        # the review's separation of the stepping on the plate (validation 57.0), printed alone
        print(f"tree {tree}")
        part_b_stepping(mod)
        return
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(f"tree {tree}")
        print("== Part A: NAFEMS T3 (36.60 degC at x = 0.08 m, t = 32 s)")
        mod.part_a(False)
        print("== Part B: plate with held edges and a power step, centre temperature against the exact double series (default stepping of 2.9.0, the FEM added)")
        part_b_fem(mod)
    text = buf.getvalue()
    out = HERE.parent / "out"
    out.mkdir(exist_ok=True)
    (out / "t0.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
