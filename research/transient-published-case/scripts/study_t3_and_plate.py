#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_t3_and_plate.py
@brief The published 1D transient benchmark (NAFEMS T3: 36.60 degC at x = 0.08 m, t = 32 s) reproduced with an independent exact series and with the program's finite-element time
       stepper, and the uniformly heated square plate with held edges (exact double series) run in the program's FVM, FDM and Analytic transients.
@details Part A (T3): the exact series of lib/exact1d.py (imports nothing from the program), then femcore with the held ends as films of very large h and a time factor on the
         load (the form of tests/test_fem_transient_closed_forms.py), swept over the elements (20 to 400), the steps (Crank-Nicolson and implicit Euler) and the
         end-film h. Part B: a 0.1 m square 1 mm plate of the bar's material (k 35, rho c = 7200 x 440.5) with a uniform heater, edges held near ambient by the largest h_side the program accepts (1e5 W/m2K; the exact series is the Robin one with that h), faces
         insulated; the centre temperature in time of the three board models against the exact double series. The FVM, FDM and Analytic models hold an end only at the (constant) ambient
         and cannot follow a prescribed time-varying temperature: Part B is the representable neighbour of T3, not T3.
         Usage: .venv/bin/python research/transient-published-case/scripts/study_t3_and_plate.py [--quick] (about 1 min, light).
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", ".."))          # the tree that holds this folder, so the program is the one of the branch
import exact1d as E  # noqa: E402
from pcbthermal import femcore as fc  # noqa: E402

H_EDGE = 1e5                                                       # the largest edge film the program accepts, W/m2K
PUBLISHED = 36.60                                                  # degC, x = 0.08 m, t = 32 s (MOOSE docs table/Altair, quoting NAFEMS)


def fem_t3(n=100, steps=3200, theta=0.5, big=1e10):
    """!
    @brief The program's FEM stepper on the T3 bar.
    @param n Elements along the bar.
    @param steps Equal steps over 32 s.
    @param theta 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @param big Film coefficient standing for a held temperature, W/m2K.
    @return float Temperature at x = 0.08 m and t = 32 s, degC.
    """
    L = 0.1
    m = fc.structured_model(np.linspace(0, L, n + 1), [0, 0.01], [0, 0.01], k=35.0, films={"xmin": big})
    m.rho_c[:] = 7200.0 * 440.5
    fn, _ = fc.structured_face(m.elems, (n, 1, 1), "xmax")
    m.add_faces(fn, h=big, t_amb=1.0)
    a = m.assemble(capacity=True)
    st = fc.Stepper(a["A"], a["M"])
    dt = 32.0 / steps
    T = np.zeros(a["rhs"].size)
    g = lambda t: 100.0 * np.sin(np.pi * t / 40.0)                 # noqa: E731
    for i in range(steps):
        T = st.step(T, dt, theta, g(i * dt) * a["rhs"], g((i + 1) * dt) * a["rhs"])
    x = m.nodes[a["used"], 0]
    # x = 0.08 is a node for n a multiple of 5; otherwise interpolate linearly between the two nodes
    xs = np.unique(np.round(x, 12))
    vals = np.array([T[np.abs(x - xx) < 1e-9].mean() for xx in xs])
    return float(np.interp(0.08, xs, vals))


def part_a(quick):
    """!
    @brief Run part A and print the tables.
    @param quick True to skip the finest runs.
    @return dict of the printed numbers.
    """
    out = {}
    ex = E.bar_sinusoidal_end(0.08, 32.0)
    ex2 = E.bar_sinusoidal_end(0.08, 32.0, n_terms=20000)
    print(f"A1 exact series (4000 / 20000 terms): {ex:.6f} / {ex2:.6f} degC; published {PUBLISHED}; difference {ex - PUBLISHED:+.4f}")
    out["exact"] = ex
    print("A2 FEM, Crank-Nicolson, 3200 steps, elements -> T(0.08, 32), error vs exact")
    for n in ((20, 50, 100) if quick else (20, 50, 100, 200, 400)):
        v = fem_t3(n=n)
        print(f"   n={n:4d}  {v:9.4f}  {v - ex:+8.4f}")
        out[f"cn_n{n}"] = v
    print("A3 FEM, n = 100, steps -> CN and implicit Euler")
    for s in (100, 400, 1600, 3200):
        c, e = fem_t3(100, s, 0.5), fem_t3(100, s, 1.0)
        print(f"   steps={s:5d}  CN {c:9.4f} ({c - ex:+8.4f})   Euler {e:9.4f} ({e - ex:+8.4f})")
        out[f"steps{s}"] = (c, e)
    print("A4 FEM, n = 100, 3200 steps, held end as film h")
    for big in (1e4, 1e6, 1e10):
        v = fem_t3(100, 3200, 0.5, big)
        print(f"   h={big:8.0e}  {v:9.4f}  {v - ex:+8.4f}")
    return out


def plate_problem(cell_note=None):
    """!
    @brief The 0.1 m square plate of the bar's material with a uniform heater and held edges.
    @param cell_note Unused label.
    @return tuple (Problem, rho_c, k, thickness m, power W).
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    t_mm, k, rc, power = 1.0, 35.0, 7200.0 * 440.5, 10.0
    mat = Materials(k_copper=k, rho_copper=7200.0, cp_copper=440.5)
    p = Problem.new(100.0, 100.0, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=0.0, h_top=1e-6, h_bottom=1e-6, h_side=H_EDGE, materials=mat)
    p.add_full_copper(layers=None)
    p.add_heater(1, power, rect=(0.0, 0.0, 100.0, 100.0), name="U")
    return p, rc, k, t_mm * 1e-3, power


def part_b(quick):
    """!
    @brief Run part B: the centre temperature in time of the three board models against the exact Robin double series, for the program's default stepping and for finer stepping.
    @param quick True for fewer runs.
    @return dict of (model, setting, cell) -> largest relative centre error for t > 10 s.
    """
    from pcbthermal import fvm, fdm, analytic
    p, rc, k, th, power = plate_problem()
    qvol = power / (0.1 * 0.1 * th)
    tau = rc * 0.1 ** 2 / (k * np.pi ** 2 * 2)                      # time constant of the slowest mode (Dirichlet limit)
    t_end = 2.0 * tau
    print(f"B0 plate 0.1 m, 1 mm, k 35, rho c {rc:.4g}, P {power} W, edge film {H_EDGE:.0e}; slowest-mode tau {tau:.1f} s; run to {t_end:.0f} s")
    settings = {"default (log, Euler, 20 frames)": dict(n_out=20), "log, Crank-Nicolson, 20 frames": dict(n_out=20, theta_scheme=0.5),
                "linear 40 frames x 16 substeps, Euler": dict(n_out=40, substeps=16, log_times=False),
                "linear 40 frames x 16 substeps, CN": dict(n_out=40, substeps=16, log_times=False, theta_scheme=0.5)}
    res = {}
    for name, mod in (("FVM", fvm), ("FDM", fdm), ("Analytic", analytic)):
        for label, kw in settings.items():
            if name == "Analytic" and not label.startswith("default"):
                continue                                              # the Analytic model has no time-stepping options
            for cell in ((2.5,) if quick else (5.0, 2.5, 1.25)):
                try:
                    r = mod.solve_transient(p, t_end, cell_mm=cell, **kw) if name != "Analytic" else mod.solve_transient(p, t_end, n_out=20, cell_mm=cell)
                except Exception as exc:                            # report, never hide
                    print(f"   {name} {label} cell {cell}: FAILED {type(exc).__name__}: {exc}")
                    continue
                fr = np.asarray(r.frames)[:, 0]
                ny, nx = fr.shape[1:]
                xs = np.linspace(0.0, 0.1, nx) if r.grid == "nodes" else (np.arange(nx) + 0.5) * 0.1 / nx
                i = ny // 2                                         # centre cell / node; the exact value is taken at the same coordinate
                errs = [float(fr[m, i, i] / E.square_plate_robin_heating(xs[i], xs[i], t, 0.1, k, rc, qvol, H_EDGE, n_roots=40) - 1.0)
                        for m, t in enumerate(r.times) if t > 10.0]
                worst = max(abs(e) for e in errs)
                print(f"   {name:8s} {label:40s} cell {cell:5.2f} mm: largest centre error (t > 10 s) {100 * worst:6.2f} %")
                res[(name, label, cell)] = worst
    return res


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    part_a(quick)
    part_b(quick)
