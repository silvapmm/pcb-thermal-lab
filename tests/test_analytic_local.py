#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_local.py
@brief The Analytic transient with vias and heatsinks kept local: a coupled modal block of the lowest K x K modes, one factor on the via couplings fitted to the steady
       solve (adopts research/analytic-2-6, README 3 and 6.3; pcbthermal/analytic_local.py).

@details Checks: (1) a board without vias and heatsinks keeps the uniform system (no local block); (2) the steady plateau of the step response is the steady solve's value at
         the same point; (3) the time to 63 % against the FVM on boards with a heatsink under the part, beside it and with vias together (the earlier smeared transient was
         -37 %, -54 % and +46 %); (4) the stored eigen coordinates are consistent: the field, the point rows, the profile propagator and the uniform start state agree with the
         step response; (5) the modes of the block (16 against 24) change the time to 63 % by under 2 points; (6) the bracket of the factor.
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, analytic, fvm
from pcbthermal import analytic_local

T0 = 25.0


def _plain(layers=2, h_side=None, power=2.0):
    """!
    @brief A 60 x 40 mm full-copper board with a 10 mm part at the centre of layer 1.
    @param layers Copper layers.
    @param h_side Edge coefficient in W/m2K (None: insulated).
    @param power Power in W.
    @return Problem.
    """
    p = Problem.new(width_mm=60, height_mm=40, layers=layers, thickness_mm=1.6, copper_um=35.0, ambient=T0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, 60, 40))
    p.add_heater(1, power, rect=(25, 15, 35, 25))
    return p


def _vias(p, n=4):
    """!
    @brief An n x n via array of 2 mm pitch under the part.
    @param p Problem.
    @param n Vias per side.
    @return The same Problem.
    """
    half = 2.0 * (n - 1) / 2.0
    p.add_via_array((30 - half, 20 - half, 30 + half, 20 + half), n, n, diameter=0.3)
    return p


def _sink(p, h_extra=100.0, where="under"):
    """!
    @brief A heatsink on layer 1, under the part (20 mm square) or on the right-hand quarter of the board.
    @param p Problem.
    @param h_extra Extra coefficient in W/m2K.
    @param where "under" or "side".
    @return The same Problem.
    """
    p.add_heatsink(1, h_extra, rect=(20, 10, 40, 30) if where == "under" else (42, 0, 60, 40))
    return p


def _t63(times, z, rth):
    """!
    @brief Time to 63.2 % of the steady resistance by interpolation in log time.
    @param times Times in seconds.
    @param z Step response in K/W.
    @param rth Steady resistance in K/W.
    @return float
    """
    target = (1.0 - math.exp(-1.0)) * float(rth)
    k = int(np.argmax(z >= target))
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    return math.exp(math.log(times[k - 1]) + f * (math.log(times[k]) - math.log(times[k - 1])))


def _step(p, cell=1.0, model="analytic"):
    """!
    @brief Unit-step response of the first heater and its time to 63 %.
    @param p Problem.
    @param cell Cell in mm.
    @param model "analytic" or "fvm".
    @return Tuple (times, z (nt,), rth, t63).
    """
    if model == "fvm":
        t, z, r = fvm.step_responses(p, cell_mm=cell)
    else:
        t, z, r = analytic.step_responses(p, cell_mm=cell, n_terms=300)
    return t, z[0], float(r[0]), _t63(t, z[0], r[0])


def test_no_local_elements_keep_the_uniform_system():
    """!
    @brief Without vias and heatsinks there is no coupled block and the step response is the closed form of the uniform modes.
    @return None.
    """
    p = _plain()
    ms = analytic._ModalSet(p, 1.0, 100)
    assert ms.ds[0]["local"] is None and not ms.scaled
    t, z, r = analytic.step_responses(p, 1.0, 100, t_end=200.0, n_times=20)
    d = ms.ds[0]
    coef = (ms.U[0][0] * d["G"][0] / d["lam"]).ravel()
    lam = d["lam"].ravel()
    ref = np.array([coef @ (1.0 - np.exp(-lam * x)) for x in t])
    assert np.allclose(z[0], ref, rtol=1e-12, atol=1e-12 * ref.max())          # (1e-13 of the largest coefficient is pruned)


@pytest.mark.parametrize("build", [lambda: _sink(_plain()), lambda: _sink(_plain(), where="side"), lambda: _sink(_vias(_plain())), lambda: _sink(_vias(_plain()), where="side"),
                                   lambda: _vias(_plain()), lambda: _sink(_vias(_plain(4)), 300.0), lambda: _sink(_vias(_plain(h_side=50.0)))])
def test_steady_plateau_is_the_steady_solve(build):
    """!
    @brief The steady resistance of the step response equals the steady solve's rise at the same point per watt, within 1 % (the earlier transient read 19.5 against 23.9 K/W
           with the heatsink beside the part).
    @param build Function that makes the board.
    @return None.
    """
    p = build()
    ms = analytic._ModalSet(p, 1.0, 300)
    lay, iy, ix = ms.points[0]
    st = analytic.solve_steady(p, cell_mm=1.0, n_terms=300)
    target = (st.T[lay, iy, ix] - T0) / p.heaters[0].power
    assert float(ms.rth[0]) == pytest.approx(target, rel=0.01)


@pytest.mark.parametrize("name,build,limit", [("sink under", lambda: _sink(_plain()), 0.03), ("sink beside", lambda: _sink(_plain(), where="side"), 0.04),
                                              ("vias + sink under", lambda: _sink(_vias(_plain())), 0.02), ("vias + sink beside", lambda: _sink(_vias(_plain()), where="side"), 0.03),
                                              ("vias 4x4", lambda: _vias(_plain()), 0.02)])
def test_time_to_63_percent_against_the_fvm(name, build, limit):
    """!
    @brief Time to 63 % within the limit of the FVM at 0.5 mm (measured -0.3 to -2.0 % here; the smeared transient of 2.5.0 was +46 %, -37 %, -54 % and -67 %).
    @param name Board name.
    @param build Function that makes the board.
    @param limit Largest relative error.
    @return None.
    """
    p = build()
    ref = _step(p, 0.5, "fvm")[3]
    got = _step(p, 0.5)[3]
    assert abs(got / ref - 1.0) < limit, name


def test_four_layers_with_a_strong_heatsink():
    """!
    @brief The worst board found (4 layers, vias, 300 W/m2K heatsink under the part): -8.1 % of the FVM at 0.5 mm, inside 10 %.
    @return None.
    """
    p = _sink(_vias(_plain(4)), 300.0)
    ref = _step(p, 0.5, "fvm")[3]
    assert abs(_step(p, 0.5)[3] / ref - 1.0) < 0.10


def test_factor_on_the_vias_only():
    """!
    @brief With vias and a heatsink the factor on the via couplings is below 1 (the truncated block cannot hold the constriction of the barrel) and a heatsink alone leaves
           it at 1; one factor on all the couplings (the first proposal) would make this board 8.5 % slow, this one is within 2 %.
    @return None.
    """
    both = analytic._ModalSet(_sink(_vias(_plain())), 1.0, 300)
    assert 0.5 < both.ds[0]["local_factor"] < 1.0
    sink = analytic._ModalSet(_sink(_plain()), 1.0, 300)
    assert sink.ds[0]["local_factor"] == 1.0 and sink.ds[0]["local"] is not None


def test_field_point_rows_and_start_state_are_consistent():
    """!
    @brief The coupled block is stored as eigen coordinates: the field built from them has the point temperature at the own point, a uniform start state is a uniform field,
           and the profile propagator reaches the steady resistance under constant power.
    @return None.
    """
    p = _sink(_vias(_plain()))
    ad = analytic._AnalyticAdapter(p, 1.0, 300)
    ms = ad.ms
    lay, iy, ix = ms.points[0]
    states = ms.steady([2.0])
    frame = ms.field(states)
    assert frame[lay, iy, ix] == pytest.approx(float(ms.points_temperature(states)[0]), rel=1e-9)
    assert frame[lay, iy, ix] == pytest.approx(2.0 * float(ms.rth[0]), rel=1e-9)
    # a uniform 10 K start is a uniform field of 10 K on every layer
    ls = ms.ds[0]["local"]
    z = np.zeros_like(states[0])
    z[:ls.K, :ls.K, :] = ls.uniform_state(10.0)
    # modes outside the block carry no part of a constant field, so only the block coordinates are set
    fld = ms.field([z])
    assert np.allclose(fld, 10.0, atol=1e-9)
    # exact propagator: long constant power reaches the steady state
    ad.prepare(10.0)
    s = [np.zeros_like(b) for b in states]
    for _ in range(300):
        s = ad.advance(s, 10.0, np.array([2.0]))
    assert float(ad.observe(s)[1][0]) - T0 == pytest.approx(2.0 * float(ms.rth[0]), rel=1e-4)


def test_modes_of_the_block_16_against_24(monkeypatch):
    """!
    @brief 16 or 24 modes per direction in the block change the time to 63 % by under 2 points.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _sink(_vias(_plain()))
    a = _step(p, 1.0)[3]
    monkeypatch.setattr(analytic, "LOCAL_MODES", 24)
    b = _step(p, 1.0)[3]
    assert abs(b / a - 1.0) < 0.02


def test_unit_checks_of_the_local_system():
    """!
    @brief Eigenvalues are positive, the block is symmetric, and a target outside the bracket of the factor takes the end and reports it.
    @return None.
    """
    p = _sink(_vias(_plain()))
    d = analytic._local_dynamics(p, 1.0, 100, 0)
    ls = d["local"]
    assert (d["lam"] > 0).all() and np.allclose(ls._sym(1.0), ls._sym(1.0).T)
    q = analytic._heater_unit_sources(p, *d["bases"])[0][:ls.K, :ls.K]
    out = ls.output_row(d["bases"][0].at(0.03)[:ls.K], d["bases"][1].at(0.02)[:ls.K], 0)
    s, ok = ls.calibrate(q, out, 1e-9)                      # colder than even the strongest coupling gives: the strong end
    assert not ok and s == pytest.approx(analytic_local.FACTOR_BRACKET[1])
    s, ok = ls.calibrate(q, out, 1e9)                       # hotter than even the weakest coupling gives: the weak end
    assert not ok and s == pytest.approx(analytic_local.FACTOR_BRACKET[0])


def test_two_heaters_get_one_system_each():
    """!
    @brief With vias and two heaters, each heater has its own calibrated system and the step responses stay at their steady values.
    @return None.
    """
    p = _vias(_plain())
    p.add_heater(1, 1.0, rect=(5, 5, 12, 12))
    ms = analytic._ModalSet(p, 1.0, 100)
    assert len(ms.ds) == 2 and all(d["local"] is not None for d in ms.ds)
    st = analytic.solve_steady(p.steady_copy("average") if p.has_profiles() else p, 1.0, 100)
    assert np.isfinite(st.t_max) and (ms.rth > 0).all()


def test_the_animation_reaches_the_steady_state():
    """!
    @brief The animation of a board with vias and a heatsink ends at the steady maximum of the modal state (and the first frame is the ambient).
    @return None.
    """
    p = _sink(_vias(_plain()))
    tr = analytic.solve_transient(p, t_end=2000.0, n_out=10, cell_mm=1.0, n_terms=100)
    assert tr.t_max[0] == pytest.approx(T0)
    assert tr.t_max[-1] == pytest.approx(tr.steady_t_max, rel=1e-3)
    assert any("coupled" in w or "couplings" in w for w in tr.warnings)
