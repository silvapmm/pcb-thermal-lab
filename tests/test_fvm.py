#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fvm.py
@brief Verification of the finite-volume solver against exact or independent results.
"""

import copy

import numpy as np
import pytest

from pcbthermal import fvm, laminate
from pcbthermal.model import Heater, Heatsink, Via, reference_problem


def test_energy_balance_is_exact():
    r = fvm.solve_steady(reference_problem(), cell_mm=2.0)
    assert abs(r.balance_error) < 1e-9
    assert r.residual < 1e-9


def test_uniform_plate_matches_closed_form():
    # A heater covering the whole board on a single layer with insulated edges gives a uniform rise: the top film on the copper node,
    # the bottom film in series with the laminate under it (laminate.py), P / (A (h_top + 1 / (1/h_bottom + t_lam / k_through))) exactly
    p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
    p.board.h_side = None
    r = fvm.solve_steady(p, cell_mm=5.0)
    b = p.board
    t_lam = b.thickness - b.copper_thickness[0]
    expected = b.ambient + 10.0 / ((b.h_top + 1.0 / (1.0 / b.h_bottom + t_lam / b.materials.k_fr4_through)) * 0.1 * 0.1)
    assert r.t_max == pytest.approx(expected, abs=1e-6)
    assert r.t_min == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("cell_mm", [10.0, 5.0, 3.3, 2.0, 1.0])
def test_requested_power_is_always_injected(cell_mm):
    # The old solver lost power on coarse grids; the new one must conserve it for any grid
    p = reference_problem(heater_mm=4.0, power=5.0)
    r = fvm.solve_steady(p, cell_mm=cell_mm)
    assert r.power_in == pytest.approx(5.0, rel=1e-12)
    assert sum(r.power_out.values()) == pytest.approx(5.0, rel=1e-9)


def test_grid_convergence():
    p = reference_problem()
    t1 = fvm.solve_steady(p, cell_mm=1.0).t_max
    t05 = fvm.solve_steady(p, cell_mm=0.5).t_max
    t2 = fvm.solve_steady(p, cell_mm=2.0).t_max
    # The error shrinks when the cell shrinks and is already small at 1 mm
    assert abs(t1 - t05) < abs(t2 - t05)
    assert abs(t1 - t05) < 0.2


def test_symmetry_of_centered_heater():
    r = fvm.solve_steady(reference_problem(), cell_mm=2.0)
    T = r.T[0]
    assert np.allclose(T, T[:, ::-1], atol=1e-9)
    assert np.allclose(T, T[::-1, :], atol=1e-9)


def test_linearity_in_power():
    a = fvm.solve_steady(reference_problem(power=3.0), cell_mm=2.0).delta_t
    b = fvm.solve_steady(reference_problem(power=6.0), cell_mm=2.0).delta_t
    assert b == pytest.approx(2.0 * a, rel=1e-9)


def test_cg_matches_direct():
    p = reference_problem()
    d = fvm.solve_steady(p, cell_mm=2.0, method="direct")
    c = fvm.solve_steady(p, cell_mm=2.0, method="cg")
    assert c.t_max == pytest.approx(d.t_max, abs=1e-6)


def test_vias_lower_the_temperature_and_filled_is_better():
    base = reference_problem(power=5.0)
    # Make the bottom layer the better heat spreader so vias matter: higher h at the bottom
    base.board.h_bottom = 25.0

    def with_vias(filled):
        p = copy.deepcopy(base)
        for x in np.linspace(46, 54, 5):
            for y in np.linspace(46, 54, 5):
                p.vias.append(Via(x / 1000.0, y / 1000.0, 0.3e-3, filled=filled))
        return fvm.solve_steady(p, cell_mm=1.0).t_max

    t0 = fvm.solve_steady(base, cell_mm=1.0).t_max
    t_hollow, t_filled = with_vias(False), with_vias(True)
    assert t_hollow < t0
    assert t_filled < t_hollow


def test_heatsink_lowers_the_temperature():
    p = reference_problem()
    t0 = fvm.solve_steady(p, cell_mm=2.0).t_max
    area = np.array([[30, 30], [70, 30], [70, 70], [30, 70]]) / 1000.0
    p.heatsinks.append(Heatsink(0, area, 100.0))
    r = fvm.solve_steady(p, cell_mm=2.0)
    assert r.t_max < t0 - 5.0
    assert r.power_out["heatsinks"] > 0
    assert abs(r.balance_error) < 1e-9


def test_missing_copper_still_finite():
    # Without any zone the FR-4 in-plane conduction keeps the problem well posed and bounded
    p = reference_problem(full_copper=False)
    r = fvm.solve_steady(p, cell_mm=2.0)
    full = fvm.solve_steady(reference_problem(), cell_mm=2.0)
    assert np.isfinite(r.t_max) and r.t_max > full.t_max
    assert abs(r.balance_error) < 1e-9


def test_transient_reaches_steady_state_and_is_monotonic():
    p = reference_problem()
    tr = fvm.solve_transient(p, t_end=3000.0, n_out=30, cell_mm=4.0)
    assert np.all(np.diff(tr.t_max) >= -1e-9)
    assert tr.t_max[-1] == pytest.approx(tr.steady_t_max, abs=0.05)
    assert tr.t_max[0] == pytest.approx(p.board.ambient)
    # Crank-Nicolson and implicit Euler agree on the final state
    tr2 = fvm.solve_transient(p, t_end=3000.0, n_out=30, cell_mm=4.0, theta_scheme=0.5)
    assert tr2.t_max[-1] == pytest.approx(tr.t_max[-1], abs=0.05)
    assert np.isfinite(tr.time_constant())


def test_sor_matches_direct_with_residual_criterion():
    p = reference_problem()
    d = fvm.solve_steady(p, cell_mm=2.0, method="direct")
    s = fvm.solve_steady(p, cell_mm=2.0, method="sor", sor_tol=1e-9)
    assert float(abs(s.T - d.T).max()) < 1e-6
    assert s.extras["converged"] == 1.0 and s.extras["iterations"] > 10
    assert abs(s.balance_error) < 1e-6


def test_sor_step_criterion_of_the_original_program_stops_early():
    # The original program stopped when one sweep changed less than 0.01 K, with omega = 1.5.
    # On a weakly coupled board this leaves a large error, which the residual criterion avoids.
    p = reference_problem()
    d = fvm.solve_steady(p, cell_mm=2.0, method="direct")
    s = fvm.solve_steady(p, cell_mm=2.0, method="sor", sor_omega=1.5, sor_tol=0.01, sor_criterion="step")
    assert s.extras["converged"] == 1.0
    assert d.t_max - s.t_max > 0.5                 # Stopped well below the true maximum
    assert abs(s.balance_error) > 0.05             # and the heat balance is visibly violated


def _uniform_slab(monkeypatch):
    # One layer, heater over the whole board, insulated edges: the temperature is uniform, so the problem reduces to
    # C * dtheta/dt = P - G * theta with an exact exponential solution. That closed form is the one of a single node: the laminate nodes of a
    # one-layer board (the bottom node of the rule and the two nodes of the earlier versions) are switched off, since what is tested here is the time integrator
    monkeypatch.setattr(laminate, "LAMINATE_NODES", 0)
    monkeypatch.setattr(laminate, "uses_rule", lambda problem: False)
    p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
    p.board.h_side = None
    return p


def test_transient_matches_exact_exponential_and_has_the_right_order(monkeypatch):
    p = _uniform_slab(monkeypatch)
    net = fvm.Network(p, 8, 8, assemble=False)
    C, G, P = net.C.sum(), net.g_amb.sum(), net.Q.sum()
    tau = C / G
    exact = lambda t: p.board.ambient + P / G * (1.0 - np.exp(-t / tau))
    errs = {}
    for scheme, name in ((1.0, "euler"), (0.5, "cn")):
        for sub in (1, 4):
            tr = fvm.solve_transient(p, t_end=3 * tau, n_out=6, cell_mm=12.5, substeps=sub, theta_scheme=scheme,
                                     log_times=False)
            errs[(name, sub)] = float(np.abs(tr.t_max - exact(tr.times)).max())
    assert errs[("euler", 4)] < errs[("euler", 1)] / 3.0          # first order: error falls with the step
    assert errs[("cn", 1)] < errs[("euler", 1)] / 5.0             # Crank-Nicolson is more accurate
    assert errs[("cn", 4)] < 0.05                                 # and close to exact in kelvin
    # Total energy: stored heat + lost heat = injected heat (checked at the last step with CN)
    tr = fvm.solve_transient(p, t_end=3 * tau, n_out=40, cell_mm=12.5, substeps=4, theta_scheme=0.5, log_times=False)
    stored = C * (tr.t_mean[-1] - p.board.ambient)
    lost = np.trapezoid(G * (tr.t_mean - p.board.ambient), tr.times)
    assert stored + lost == pytest.approx(P * tr.times[-1], rel=2e-3)


def _transient_all_factors(net, ambient, t_end, n_out):
    """!
    @brief Reference of the transient with the time stepping of the program that keeps every factor (the code before the one-factor change).
    @param net The network.
    @param ambient Ambient temperature in degC.
    @param t_end Final time in s.
    @param n_out Output frames.
    @return Array of the frames (nt, layers, ny, nx) in degC.
    """
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    stages = 10
    per_stage = max(int(np.ceil(n_out / stages)), 1)
    dt0 = t_end / (per_stage * (2 ** stages - 1))
    dts = np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)])
    cache, x, out = {}, np.zeros(net.nl * net.ny * net.nx), [np.zeros(net.nl * net.ny * net.nx)]
    for dt in dts:
        key = round(float(dt), 12)
        if key not in cache:
            cache[key] = (spla.splu((sp.diags(net.C.ravel() / dt) + net.K).tocsc(), permc_spec=fvm.ORDERING), sp.diags(net.C.ravel() / dt).tocsr())
        lu, B = cache[key]
        x = lu.solve(B @ x + net.Q.ravel())
        out.append(x)
    nb = getattr(net, "n_board", net.nl)
    return np.asarray([o.reshape(net.nl, net.ny, net.nx)[:nb] + ambient for o in out])


def test_transient_keeps_one_factor_and_same_fields(monkeypatch):
    # The animation holds one LU factor at a time (not ten) and the frames are bit-identical to the all-factors stepping
    import scipy.sparse.linalg as spla
    p = reference_problem()
    net = fvm.Network(p, 20, 20)
    live, peak, real = [0], [0], spla.splu

    class Counted:
        """! @brief Wrapper that counts the factors alive at once. @param lu The factor. @return None. """
        def __init__(self, lu):
            self.lu = lu
            live[0] += 1
            peak[0] = max(peak[0], live[0])

        def solve(self, b):
            """! @brief Solve with the factor. @param b Right-hand side. @return Solution. """
            return self.lu.solve(b)

        def __del__(self):
            live[0] -= 1

    monkeypatch.setattr(fvm.spla, "splu", lambda *a, **k: Counted(real(*a, **k)))
    r = fvm.transient_from_network(net, p.board.ambient, 600.0, n_out=40, log_times=True)
    monkeypatch.undo()
    assert peak[0] <= 2          # the new factor is built while the old one is released, never ten at once
    ref = _transient_all_factors(net, p.board.ambient, 600.0, 40)
    assert r.frames.shape == ref.shape
    assert np.array_equal(r.frames, ref)
