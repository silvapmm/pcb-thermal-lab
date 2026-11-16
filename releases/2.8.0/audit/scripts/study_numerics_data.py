#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_numerics_data.py
@brief The checks of the numerics and the default data made by the audit of 2.8.0 (REVIEW_L12.md): SOR omega on both sides of the Rayleigh value, the theta method
       against the exact exponential, the step responses, the observed order with the cell, the memory law on fresh processes, the default material constants.
@details Parts (run one or several):
         * `omega`: sweeps of the program's SOR on the example board at 2 and 1 mm for omega = Rayleigh value + delta (theory 2.3);
         * `theta`: implicit Euler and Crank-Nicolson against the exact exponential of a uniform one-layer board at four step sizes, and the energy check
           (the set-up of `tests/test_fvm.py`; validation 7);
         * `steps`: the step responses of the example board (Crank-Nicolson, 4 steps per stage) against 16 steps per stage (Crank-Nicolson and implicit Euler);
         * `lu`: the symmetric and the default SuperLU modes on the example board (fill, permutations, solutions; theory 2.3);
         * `order`: observed order of the FVM with the cell, a smooth case and a case with a copper edge and a heater off the grid lines (theory 2.5);
         * `memory`: the estimate of the memory guard against the peak of `api.simulate` in a fresh process (one subprocess per point, example board; theory 2.7);
         * `copper`: the hottest rise of the example board with the program's copper (385, 8960, 385) and with Table A.1 of Lienhard (398, 8954, 384);
         * `sens`: the hottest rise against the FR-4 conductivities and the emissivity (example board and a bare 60 x 40 mm board);
         * `gmd`: the geometric mean distance of a square to itself (the 0.447 of `lumped.py`) by quadrature and in closed form.
         Run from the repository root: `.venv/bin/python releases/2.8.0/audit/scripts/study_numerics_data.py omega theta steps lu order memory copper sens gmd`
         (`memory` peaks at about 3.1 GB at 0.25 mm; the other parts stay under 1 GB and take seconds).
"""

import copy
import math
import resource
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from pcbthermal import api, fdm, fvm, laminate  # noqa: E402
from pcbthermal.model import Problem, reference_problem  # noqa: E402
from pcbthermal.project import load_project  # noqa: E402

EXAMPLE = ROOT / "examples" / "example_board.pcbt.json"


def example():
    """!
    @brief The example board.
    @return Problem.
    """
    return load_project(str(EXAMPLE)).problem


def network(problem, cell_mm):
    """!
    @brief The FVM network of a problem at a cell size, with the grid rule of the program.
    @param problem A Problem.
    @param cell_mm Cell size in mm.
    @return fvm.Network.
    """
    b = problem.board
    return fvm.Network(problem, max(int(round(b.width * 1000.0 / cell_mm)), 2), max(int(round(b.height * 1000.0 / cell_mm)), 2))


def part_omega():
    """!
    @brief Sweeps of the SOR against omega around the Rayleigh value on the example board.
    @return None (prints).
    """
    p = example()
    for cell in (2.0, 1.0):
        net = network(p, cell)
        w0 = net.sor_omega()
        row = []
        for dw in (-0.06, -0.03, -0.015, -0.005, 0.0, 0.005, 0.015, 0.03, 0.06):
            if w0 + dw >= 2.0:
                continue
            _, _, info = net.solve_sor(omega=w0 + dw)
            row.append(f"{dw:+.3f}: {info['iterations']}")
        print(f"omega cell {cell} mm, Rayleigh omega {w0:.5f}; delta: sweeps  " + ", ".join(row))


def part_theta():
    """!
    @brief Implicit Euler and Crank-Nicolson against the exact exponential (uniform one-layer board, laminate nodes off as in tests/test_fvm.py).
    @return None (prints).
    """
    saved = (laminate.LAMINATE_NODES, laminate.uses_rule)
    laminate.LAMINATE_NODES, laminate.uses_rule = 0, (lambda problem: False)
    try:
        p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
        p.board.h_side = None
        net = fvm.Network(p, 8, 8, assemble=False)
        C, G, P = net.C.sum(), net.g_amb.sum(), net.Q.sum()
        tau = C / G
        exact = lambda t: p.board.ambient + P / G * (1.0 - np.exp(-t / tau))       # noqa: E731
        print(f"theta: time constant {tau:.2f} s, steady rise {P / G:.3f} K")
        for scheme, name in ((1.0, "implicit Euler"), (0.5, "Crank-Nicolson")):
            errs = []
            for sub in (1, 2, 4, 8):
                tr = fvm.solve_transient(p, t_end=3 * tau, n_out=6, cell_mm=12.5, substeps=sub, theta_scheme=scheme, log_times=False)
                errs.append(float(np.abs(tr.t_max - exact(tr.times)).max()))
            orders = [math.log2(errs[i] / errs[i + 1]) for i in range(3)]
            print(f"  {name}: max error {' / '.join(f'{e:.4f}' for e in errs)} K, observed orders {' / '.join(f'{o:.2f}' for o in orders)}")
        tr = fvm.solve_transient(p, t_end=3 * tau, n_out=40, cell_mm=12.5, substeps=4, theta_scheme=0.5, log_times=False)
        stored = C * (tr.t_mean[-1] - p.board.ambient)
        lost = np.trapezoid(G * (tr.t_mean - p.board.ambient), tr.times)
        print(f"  energy: (stored + lost) / injected - 1 = {(stored + lost) / (P * tr.times[-1]) - 1:+.2e}")
    finally:
        laminate.LAMINATE_NODES, laminate.uses_rule = saved


def part_steps():
    """!
    @brief Step responses of the example board: monotone, and close to the same run with four times the steps.
    @return None (prints).
    """
    p = example()
    t, z, rth = fvm.step_responses(p, cell_mm=1.0)
    t16, z16, _ = fvm.step_responses(p, cell_mm=1.0, per_stage=16)
    te, ze, _ = fvm.step_responses(p, cell_mm=1.0, per_stage=16, theta_scheme=1.0)
    for i in range(z.shape[0]):
        print(f"steps heater {i}: R {rth[i]:.4f} K/W, Z(end)/R {z[i, -1] / rth[i]:.6f}, smallest increment {np.diff(z[i]).min():.2e}, "
              f"max |CN4 - CN16| / R {np.abs(z[i] - np.interp(t, t16, z16[i])).max() / rth[i]:.2e}, "
              f"max |CN4 - IE16| / R {np.abs(z[i] - np.interp(t, te, ze[i])).max() / rth[i]:.2e}")


def part_lu():
    """!
    @brief The symmetric and the default SuperLU modes on the matrices of the example board.
    @return None (prints).
    """
    import scipy.sparse.linalg as spla
    p = example()
    rng = np.random.default_rng(1)
    for name, net in (("fvm", network(p, 1.0)), ("fdm", fdm.Network(p, 1.0))):
        A = net.K.tocsc()
        s = spla.splu(A, permc_spec=fvm.ORDERING, diag_pivot_thresh=0.0, options={"SymmetricMode": True})
        d = spla.splu(A, permc_spec=fvm.ORDERING)
        x = rng.random(A.shape[0])
        rel = np.abs(s.solve(x) - d.solve(x)).max() / np.abs(d.solve(x)).max()
        print(f"lu {name}: {A.shape[0]} unknowns, nnz(L+U) symmetric {s.L.nnz + s.U.nnz} default {d.L.nnz + d.U.nnz}, "
              f"default perm_r == perm_c {np.array_equal(d.perm_r, d.perm_c)}, pivots positive {bool(s.U.diagonal().min() > 0)}, solutions differ {rel:.1e}")


def part_order():
    """!
    @brief Observed order of the FVM with the cell on a smooth case and on a case with a feature.
    @return None (prints).
    """
    def smooth():
        p = Problem.new(48, 48, 2)
        for layer in (1, 2):
            p.add_zone(layer, rect=(0, 0, 48, 48))
        p.add_heater(1, 2.0, rect=(20, 20, 28, 28), name="U")
        p.board.h_side = None
        return p

    def feature():
        p = Problem.new(48, 48, 2)
        p.add_zone(1, rect=(0, 0, 24.3, 48))
        p.add_zone(2, rect=(0, 0, 48, 48))
        p.add_heater(1, 2.0, rect=(20.1, 20.1, 26.1, 26.1), name="U")
        p.board.h_side = None
        return p

    for name, make in (("smooth", smooth), ("feature", feature)):
        peak, mean = [], []
        for cell in (2.0, 1.0, 0.5, 0.25):
            n = int(round(48 / cell))
            net = fvm.Network(make(), n, n)
            theta, _ = net.solve_steady()
            top = theta[0]
            w = net.Qw_matrix.toarray()[:, 0][: n * n]
            peak.append(float(top.max()))
            mean.append(float((top.ravel() * w).sum() / w.sum()))

        def orders(v):
            return " / ".join(f"{math.log2(abs(v[i] - v[i + 1]) / abs(v[i + 1] - v[i + 2])):.2f}" for i in range(len(v) - 2))
        print(f"order {name} (cells 2 / 1 / 0.5 / 0.25 mm): peak rise {' / '.join(f'{x:.4f}' for x in peak)} K, orders {orders(peak)}; "
              f"heater mean {' / '.join(f'{x:.4f}' for x in mean)} K, orders {orders(mean)}")


def memory_point(model, cell):
    """!
    @brief One point of the memory law: run in this (fresh) process and print the estimate and the measured peak.
    @param model "fvm" or "fdm".
    @param cell Cell size in mm.
    @return None (prints).
    """
    from pcbthermal import memory
    p = example()
    base = memory.baseline_bytes()
    v = memory.check(p, [model], cell, quiet=True)[0]
    o = api.default_options()
    o.models, o.cell_mm = (model,), cell
    api.simulate(p, o)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak = peak if sys.platform == "darwin" else peak * 1024            # ru_maxrss is in bytes on macOS, in kB on Linux
    safety = memory.CONTINUOUS[model][3]
    law = base + (v.estimate - base) / safety
    print(f"memory {model} {cell} mm: {v.unknowns} unknowns, base {base / 1e9:.3f} GB, peak {peak / 1e9:.3f} GB, estimate {v.estimate / 1e9:.3f} GB, "
          f"peak / estimate {peak / v.estimate:.2f}, peak / law without safety {peak / law:.2f}")


def part_memory():
    """!
    @brief Five points of the memory law, each in its own process.
    @return None (prints through the subprocesses).
    """
    for model, cell in (("fvm", 0.5), ("fdm", 0.5), ("fvm", 0.35), ("fdm", 0.35), ("fvm", 0.25)):
        out = subprocess.run([sys.executable, __file__, "_memory_point", model, str(cell)], capture_output=True, text=True, check=True)
        print(out.stdout.strip().splitlines()[-1])


def rise(problem, models=("fvm",), cell=1.0):
    """!
    @brief Hottest rise of a problem in each model.
    @param problem A Problem.
    @param models Model keys.
    @param cell Cell size in mm.
    @return dict model -> rise in K.
    """
    o = api.default_options()
    o.models, o.cell_mm = tuple(models), cell
    r = api.simulate(problem, o)
    return {m: r.results[m].t_max - problem.board.ambient for m in models}


def part_copper():
    """!
    @brief The example board with the program's copper and with Lienhard's Table A.1 (pure copper at 20 C).
    @return None (prints).
    """
    out = []
    for k, rho, cp in ((385.0, 8960.0, 385.0), (398.0, 8954.0, 384.0)):
        p = example()
        m = p.board.materials
        m.k_copper, m.rho_copper, m.cp_copper = k, rho, cp
        out.append(rise(p, ("fvm", "lumped", "analytic")))
    for m in out[0]:
        print(f"copper {m}: rise {out[0][m]:.3f} K (385) / {out[1][m]:.3f} K (398), change {(out[1][m] / out[0][m] - 1) * 100:+.2f} %")


def set_dielectric(problem, k_inplane=None, k_through=None):
    """!
    @brief Change the FR-4 conductivities of a problem (simple and advanced stack-up).
    @param problem A Problem (changed in place).
    @param k_inplane In-plane conductivity in W/mK, or None.
    @param k_through Through-thickness conductivity in W/mK, or None.
    @return The problem.
    """
    m = problem.board.materials
    if k_inplane:
        m.k_fr4_inplane = k_inplane
    if k_through:
        m.k_fr4_through = k_through
    for d in problem.board.dielectrics or []:
        if k_inplane:
            d.k_inplane = k_inplane
        if k_through:
            d.k_through = k_through
    return problem


def part_sens():
    """!
    @brief Sensitivity of the hottest rise (FVM, 1 mm) to the FR-4 conductivities and to the emissivity of computed coefficients.
    @return None (prints).
    """
    def bare():
        p = Problem.new(60, 40, 2)
        p.add_heater(1, 1.0, rect=(27, 17, 33, 23), name="U")
        return p

    def computed(p, eps):
        p.board.h_mode = "computed"
        p.board.emissivity_top = p.board.emissivity_bottom = eps
        return p

    for name, make in (("example board", example), ("bare 60 x 40 mm, 2 layers, 6 mm 1 W part", bare)):
        base = rise(make())["fvm"]
        row = [f"k_ip {k}: {(rise(set_dielectric(make(), k_inplane=k))['fvm'] / base - 1) * 100:+.1f} %" for k in (0.3, 0.6, 1.2)]
        row += [f"k_th {k}: {(rise(set_dielectric(make(), k_through=k))['fvm'] / base - 1) * 100:+.1f} %" for k in (0.25, 0.35)]
        e9 = rise(computed(make(), 0.9))["fvm"]
        row += [f"emissivity {e} (computed h): {(rise(computed(make(), e))['fvm'] / e9 - 1) * 100:+.1f} %" for e in (0.6, 0.3)]
        print(f"sens {name}, rise {base:.3f} K: " + ", ".join(row))


def part_gmd():
    """!
    @brief Geometric mean distance of a square to itself, in units of its side.
    @return None (prints).
    """
    from scipy import integrate
    f = lambda v, u: (1 - u) * (1 - v) * 0.5 * math.log(u * u + v * v) if u * u + v * v > 0 else 0.0      # noqa: E731
    val, _ = integrate.dblquad(f, 0, 1, 0, 1, epsabs=1e-12)
    print(f"gmd: quadrature {math.exp(4 * val):.10f}, closed form exp(ln2/3 + pi/3 - 25/12) {math.exp(math.log(2) / 3 + math.pi / 3 - 25 / 12):.10f}")


PARTS = {"omega": part_omega, "theta": part_theta, "steps": part_steps, "lu": part_lu, "order": part_order, "memory": part_memory,
         "copper": part_copper, "sens": part_sens, "gmd": part_gmd}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_memory_point":
        memory_point(sys.argv[2], float(sys.argv[3]))
    else:
        for key in sys.argv[1:] or list(PARTS):
            PARTS[key]()
