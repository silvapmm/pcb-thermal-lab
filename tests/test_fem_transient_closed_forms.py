#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_transient_closed_forms.py
@brief Closed forms of the finite-element time stepper (`femcore.Stepper`, `femcore.Model.assemble(capacity=True)`): a lumped RC, the order in time of implicit Euler and
       Crank-Nicolson on a decaying mode, the slab with convection (eigenseries), the semi-infinite solid (the first-seconds table of DESIGN.md 3 and the two exact one-step
       values of 14.1), the Rannacher factor reuse, the energy balance, the steady limit and a 1D transient benchmark.
@details The slab formula is a textbook result (status M of [CarslawJaeger]): the test derives it here and says so. The benchmark is the NAFEMS T3 case, read in four open
         verification documents ([NAFEMS-T3] for the case, [MOOSE-T3], [Abaqus-T3], [Altair-T3], [Wolfram-T3], keys of research/theory/BIBLIOGRAPHY.md; the NAFEMS publication
         itself was not obtained) and reproduced by an exact series (36.6031 degC). Light: a few seconds.
"""

import numpy as np
import pytest
from scipy.optimize import brentq

from pcbthermal import femcore as fc


def _bar(n, length=1.0, area_side=0.01, k=1.0, rho_c=1.0, film_h=1e-9):
    """!
    @brief A bar of n elements along x with an (almost) insulated surface: one tiny film on the x = 0 end so that the problem is regular.
    @param n Elements along the bar, count.
    @param length Length in m.
    @param area_side Side of the square cross-section in m.
    @param k Conductivity in W/mK.
    @param rho_c Volumetric heat capacity in J/m3K.
    @param film_h Film coefficient of the end face in W/m2K.
    @return femcore.Model with rho_c set.
    """
    m = fc.structured_model(np.linspace(0, length, n + 1), [0, area_side], [0, area_side], k=k, films={"xmin": film_h})
    m.rho_c[:] = rho_c
    return m


def _run(model, hs, theta, loadfn=None, T0=None, start=False, emit_all=True):
    """!
    @brief March a model through the steps `hs` with the Stepper and return the field after each step.
    @param model femcore.Model with rho_c.
    @param hs Step sizes in s.
    @param theta 0.5 or 1.
    @param loadfn Callable t -> load vector factor (None: the model's own load at 1).
    @param T0 Start field on the unknowns (None: rest).
    @param start True: the Rannacher start on the first step.
    @param emit_all Unused flag kept for readability.
    @return Tuple (list of fields, the assembled dict).
    """
    a = model.assemble(capacity=True)
    st = fc.Stepper(a["A"], a["M"])
    load = a["rhs"]
    T = np.zeros(load.size) if T0 is None else T0.copy()
    out, t = [], 0.0
    for i, h in enumerate(hs):
        p0 = 1.0 if loadfn is None else loadfn(t)
        p1 = 1.0 if loadfn is None else loadfn(t + h)
        if i == 0 and start and theta < 1.0:
            st.prepare(h, theta)
            for _ in range(2):
                T = st.euler_half_step(T, h, p0 * load)
        else:
            T = st.step(T, h, theta, p0 * load, p1 * load)
        t += h
        out.append(T.copy())
    return out, a


def test_lumped_rc_matches_the_exponential_and_the_energy_balance_closes():
    """!
    @brief A conductive plate (Bi = 1e-5) with a film on its top and a source: T(t) = P / (h A) (1 - exp(-t / tau)), tau = rho c t / h, to 0.2 % from one tau on (2 % in the first
           steps, which the Euler half steps of the start cost) with Crank-Nicolson, and the field reaches the steady solve after 20 tau.
    @return None.
    """
    side, th, h, rc, P = 0.02, 1e-3, 10.0, 1e6, 0.5
    m = fc.structured_model([0, side], [0, side], [0, th], k=1000.0, q=P / (side * side * th), films={"top": h})
    m.rho_c[:] = rc
    tau = rc * th / h
    hs = [tau / 20.0] * 400
    fields, a = _run(m, hs, 0.5, start=True)
    mean = np.array([float(a["m_lump"] @ f) / a["capacity_total"] for f in fields])
    t = np.cumsum(hs)
    exact = P / (h * side * side) * (1.0 - np.exp(-t / tau))
    late = t >= tau                                                  # the Euler half steps of the start cost a percent in the first steps, then it is second order
    assert np.abs(mean[late] / exact[late] - 1.0).max() < 2e-3
    assert np.abs(mean / exact - 1.0).max() < 2e-2
    steady = fc.Stepper(a["A"], None)
    steady.prepare(0.0, 1.0)
    assert np.abs(fields[-1] / steady.solve(a["rhs"]) - 1.0).max() < 1e-6


def test_energy_balance_of_march_is_exact_to_round_off():
    """!
    @brief The energy bookkeeping of `fem.march` (the steps' own theta weights) closes stored + lost = input to 1e-9 for Euler and for Crank-Nicolson with the start.
    @return None.
    """
    from pcbthermal import fem
    side, th, h, rc, P = 0.02, 1e-3, 10.0, 1e6, 0.5
    m = fc.structured_model([0, side, 2 * side], [0, side], [0, th, 2 * th], k=5.0, q=P / (2 * side * side * 2 * th), films={"top": h})
    m.rho_c[:] = rc
    a = m.assemble(capacity=True)
    for theta in (1.0, 0.5):
        st = fc.Stepper(a["A"], a["M"])
        hs = np.array([1.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0])
        T, energy = fem.march(st, a["M"], a["A"], a["rhs"], hs, np.ones(hs.size, bool), theta, lambda k, T: None, gam=a["gam"][a["used"]])
        e_in = (a["q_gen"] + a["q_flux"]) * hs.sum()
        assert abs((float(a["m_lump"] @ T) + energy["lost"]) / e_in - 1.0) < 1e-9


def test_time_order_euler_one_and_crank_nicolson_two_on_a_decaying_mode():
    """!
    @brief The error of the field at a fixed time against a very fine step falls by 2 when the step is halved for implicit Euler and by 4 for Crank-Nicolson (no start: the
           load is zero and the start is smooth).
    @return None.
    """
    n, L = 40, 1.0
    m = _bar(n, L, k=1.0, rho_c=1.0)
    x = m.nodes[:, 0]
    T0 = np.cos(np.pi * x / L)
    t_end = 0.1
    fine, _ = _run(m, [t_end / 1024.0] * 1024, 0.5, loadfn=lambda t: 0.0, T0=T0)
    ref = fine[-1]
    for theta, lo, hi in ((1.0, 1.8, 2.2), (0.5, 3.6, 4.4)):
        err = []
        for steps in (8, 16, 32):
            f, _ = _run(m, [t_end / steps] * steps, theta, loadfn=lambda t: 0.0, T0=T0)
            err.append(np.linalg.norm(f[-1] - ref))
        assert lo < err[0] / err[1] < hi and lo < err[1] / err[2] < hi, (theta, err)


def test_slab_with_convection_matches_the_eigenseries():
    """!
    @brief A slab insulated at one face and with a film at the other, initial rise 1: theta(0, t) = sum 4 sin(l_n) / (2 l_n + sin 2 l_n) exp(-alpha l_n^2 t / L^2) with
           l tan l = Bi (the classical solution, status M in the design note: derived here), to 5e-4 with Crank-Nicolson at 100 elements.
    @return None.
    """
    L, k, rc, h = 0.01, 2.0, 2.0e6, 400.0
    Bi, alpha = h * L / k, k / rc
    lam = np.array([brentq(lambda z: z * np.tan(z) - Bi, n * np.pi + 1e-9, n * np.pi + np.pi / 2 - 1e-9) for n in range(60)])
    c = 4.0 * np.sin(lam) / (2.0 * lam + np.sin(2.0 * lam))
    m = fc.structured_model(np.linspace(0, L, 101), [0, L], [0, L], k=k, films={"xmax": h})
    m.rho_c[:] = rc
    t_end = 0.4 * L * L / alpha
    steps = 400
    f, _ = _run(m, [t_end / steps] * steps, 0.5, loadfn=lambda t: 0.0, T0=np.ones(m.assemble()["rhs"].size))
    x0 = m.nodes[:, 0] < 1e-12
    got = float(f[-1][x0].mean())
    exact = float((c * np.exp(-alpha * lam ** 2 * t_end / L ** 2)).sum())
    assert abs(got / exact - 1.0) < 5e-4, (got, exact)


def _semi_infinite(first=2e-6, ratio=1.15, depth=6e-3, k=0.3, rc=1.665e6):
    """!
    @brief A graded 1D column that stands for a semi-infinite solid, a unit flux on its first face.
    @param first Size of the first element in m.
    @param ratio Growth of the element size.
    @param depth Depth in m.
    @param k Conductivity in W/mK.
    @param rc Volumetric heat capacity in J/m3K.
    @return Tuple (model, effusivity in W s^0.5/m2K, node ids of the heated face on the unknowns).
    """
    z, hh = [0.0], first
    while z[-1] < depth:
        z.append(z[-1] + hh)
        hh *= ratio
    m = fc.structured_model([0, 1e-3], [0, 1e-3], z, k=k, films={"top": 1.0})
    m.rho_c[:] = rc
    fn, _ = fc.structured_face(m.elems, (1, 1, len(z) - 1), "bottom")
    m.add_faces(fn, flux=1.0)
    face = np.unique(fn)
    return m, float(np.sqrt(k * rc)), face


def _face_error(steps, theta, start, dt=0.06):
    """!
    @brief Relative error of the face temperature after `steps` equal steps of a flux switched on, against 2 q sqrt(t / pi) / e.
    @param steps Number of steps behind the output.
    @param theta 1 (Euler) or 0.5.
    @param start True for the Rannacher start.
    @param dt Step in s (the table is self-similar: any dt that the mesh resolves).
    @return float (computed / exact - 1).
    """
    m, eff, face = _semi_infinite()
    fields, a = _run(m, [dt] * steps, theta, start=start)
    t = steps * dt
    rise = float(fields[-1][face].mean())
    area = 1e-6
    exact = 2.0 * (1.0 / area * area) * np.sqrt(t / np.pi) / eff        # q = 1 W/m2 over the face
    return rise / exact - 1.0


@pytest.mark.parametrize("theta,start,expected", [(1.0, False, [-11.42, -6.04, -3.11, -1.59]), (0.5, True, [-6.04, -0.34, -0.17, -0.08]), (0.5, False, [25.27, -11.41, -6.04, -3.11])])
def test_the_first_seconds_table_of_the_design_note(theta, start, expected):
    """!
    @brief The error of the face temperature against the semi-infinite closed form after 1, 2, 4 and 8 steps reproduces the table of DESIGN.md 3 (percent, to 0.15 point): implicit
           Euler, Crank-Nicolson with the Rannacher start, Crank-Nicolson without it. The consistent mass of the program is the one used there.
    @param theta Implicitness.
    @param start Rannacher start.
    @param expected Table row in percent.
    @return None.
    """
    got = [100.0 * _face_error(s, theta, start) for s in (1, 2, 4, 8)]
    assert np.allclose(got, expected, atol=0.15), got


def test_the_two_exact_one_step_values_on_a_fine_mesh():
    """!
    @brief One implicit-Euler step of a flux switched on gives the face rise q sqrt(dt) / e, i.e. sqrt(pi) / 2 - 1 = -11.38 % of the exact value; one Crank-Nicolson step without a
           start gives sqrt(2) q sqrt(dt) / e, i.e. sqrt(pi / 2) - 1 = +25.33 % (DESIGN.md 14.1, derived there on the exact continuum); the mesh brings 0.1 point.
    @return None.
    """
    assert abs(100 * _face_error(1, 1.0, False) - 100 * (np.sqrt(np.pi) / 2 - 1)) < 0.1
    assert abs(100 * _face_error(1, 0.5, False) - 100 * (np.sqrt(np.pi / 2) - 1)) < 0.1


def test_rannacher_half_step_with_the_crank_nicolson_factor_equals_a_fresh_euler_factor():
    """!
    @brief The implicit-Euler step of h/2 solved with the factor of the Crank-Nicolson step of h (`Stepper.euler_half_step`) equals the same step with its own factor to
           round-off, and costs no factorisation.
    @return None.
    """
    m, _, _ = _semi_infinite()
    a = m.assemble(capacity=True)
    T0 = np.random.default_rng(3).random(a["rhs"].size)
    st = fc.Stepper(a["A"], a["M"])
    st.prepare(0.2, 0.5)
    n0 = st.factorisations
    via_cn = st.euler_half_step(T0, 0.2, a["rhs"])
    assert st.factorisations == n0
    fresh = fc.Stepper(a["A"], a["M"])
    direct = fresh.step(T0, 0.1, 1.0, a["rhs"], a["rhs"])
    assert np.abs(via_cn - direct).max() < 1e-10 * np.abs(direct).max()


def test_the_one_dimensional_transient_benchmark():
    """!
    @brief A bar of 0.1 m (k 35 W/mK, rho 7200 kg/m3, c 440.5 J/kgK) from 0 degC, x = 0 held at 0 and x = 0.1 m held at 100 sin(pi t / 40) degC: 36.60 degC at x = 0.08 m,
           t = 32 s. The held temperatures are films of a very large h (the penalty form of the program's Robin face) with a time factor on the load. SOURCES: the case and the
           value 36.60 degC are those of [NAFEMS-T3] as read in [MOOSE-T3], [Abaqus-T3], [Altair-T3] and [Wolfram-T3] (research/theory/BIBLIOGRAPHY.md; the NAFEMS publication
           itself was not obtained); the exact value is 36.6031 degC (eigenfunction series and method of lines, research/transient-published-case/lib/exact1d.py), and the
           program's FEM gives 36.6106 degC with 100 elements and 36.6050 with 200.
    @return None.
    """
    n, L, big = 100, 0.1, 1e10
    m = fc.structured_model(np.linspace(0, L, n + 1), [0, 0.01], [0, 0.01], k=35.0, films={"xmin": big})
    m.rho_c[:] = 7200.0 * 440.5
    fn, _ = fc.structured_face(m.elems, (n, 1, 1), "xmax")
    m.add_faces(fn, h=big, t_amb=1.0)
    a = m.assemble(capacity=True)
    st = fc.Stepper(a["A"], a["M"])
    steps = 3200
    dt = 32.0 / steps
    T = np.zeros(a["rhs"].size)
    g = lambda t: 100.0 * np.sin(np.pi * t / 40.0)             # noqa: E731
    for i in range(steps):
        T = st.step(T, dt, 0.5, g(i * dt) * a["rhs"], g((i + 1) * dt) * a["rhs"])
    x = m.nodes[a["used"], 0]
    got = float(T[np.abs(x - 0.08) < 1e-9].mean())
    assert abs(got - 36.6031) < 0.02, got                      # the exact value; 100 elements read 36.6106
