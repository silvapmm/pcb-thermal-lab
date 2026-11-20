#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_transient_default_stepping.py
@brief The default stepping of the FVM and FDM power-step run (`fix/transient-default-stepping`): Crank-Nicolson with the Rannacher start, the first stage in quarter steps.

@details Before the change the defaults were implicit Euler with one step per frame: the first frame of the example board was one Euler step (-12.4 % of the peak rise in the
         Animation, -16.5 % on the command line) and the peak was 0.7 to 1.9 % low after the first seconds (`research/transient-published-case` 4). The reference is the same network
         integrated with implicit Euler at 64 and 128 substeps between frames, Richardson-extrapolated (it only removes the time-step error), and an independent dense step of a
         three-node network for the start. Measured with the change: first frame -0.12 % and every frame within 0.3 % on the two-layer board at the Animation defaults.
"""

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.sparse.linalg import splu

from pcbthermal import cli, fdm, fem, fvm
from pcbthermal.model import Problem, load_problem

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def two_layer():
    """!
    @brief The two-layer board of `research/transient-reference-boards` (`two2`): 60 x 40 mm, 35 um copper, a 1 W part, h 10 W/m2K on both faces, insulated sides.
    @return Problem.
    """
    p = Problem.new(60, 40, 2, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None)
    p.add_zone(1, rect=(0, 0, 60, 40))
    p.add_zone(2, rect=(0, 0, 60, 40))
    p.add_heater(1, 1.0, rect=(25, 15, 35, 25), role="source")
    return p


def peak_error_percent(problem, cell, t_end, n_out, m=64, **kw):
    """!
    @brief Error of the peak rise of a run against the same network without its time-step error, at every frame after t = 0.
    @param problem Problem.
    @param cell Cell in mm.
    @param t_end Final time in s (None: five estimated time constants).
    @param n_out Frames.
    @param m Substeps per frame of the coarse reference run (count).
    @param kw Keywords of `fvm.transient_from_network` (the stepping under test).
    @return numpy.ndarray Relative error in percent, one per frame after t = 0.
    """
    b = problem.board
    net = fvm.Network(problem, max(int(round(b.width * 1e3 / cell)), 2), max(int(round(b.height * 1e3 / cell)), 2))
    t_end = 5 * fvm.estimate_time_constant(problem) if t_end is None else t_end
    tr = fvm.transient_from_network(net, b.ambient, t_end, n_out, **kw)
    kk, cc, q = net.K.tocsc(), net.C.ravel(), net.Q.ravel()

    def run(mm):
        x, out, lu, key = np.zeros(kk.shape[0]), [], None, None
        for a, c in zip(tr.times[:-1], tr.times[1:]):
            dt = (c - a) / mm
            if key != round(dt, 12):
                lu, key = splu((sp.diags(cc / dt) + kk).tocsc()), round(dt, 12)
            for _ in range(mm):
                x = lu.solve(cc / dt * x + q)
            out.append(x.copy())
        return np.array(out)

    ref = (2.0 * run(2 * m) - run(m)).reshape(len(tr.times) - 1, net.nl, net.ny, net.nx)[:, :tr.frames.shape[1]]
    want = ref.reshape(len(tr.times) - 1, -1).max(axis=1)
    got = (tr.frames[1:] - b.ambient).reshape(len(tr.times) - 1, -1).max(axis=1)
    return 100.0 * (got / want - 1.0)


def test_the_default_run_has_no_first_frame_error_and_a_small_peak_error():
    """!
    @brief Two-layer board, the Animation defaults (60 frames, five time constants): the first frame within 1 % and every frame within 0.3 % of the reference (measured -0.12 %);
           the stepping of 2.8 (Euler, one step for the first frame) gave -4.1 % at the first frames, so the check can fail.
    @return None.
    """
    p = two_layer()
    new = peak_error_percent(p, 2.0, None, 60)
    old = peak_error_percent(p, 2.0, None, 60, theta_scheme=1.0, first_stage_split=1)
    assert abs(new[0]) < 1.0 and np.abs(new).max() < 0.3
    assert np.abs(old).max() > 3.0                      # the reference does see the old error (measured -4.14 %)


def test_the_example_board_first_frame_is_no_longer_one_euler_step():
    """!
    @brief Example board at 4 mm, the Animation defaults: the first frame is within 1 % of the reference (the stepping of 2.8 read about -12 % there) and the peak within 0.5 %.
    @return None.
    """
    p = load_problem(os.path.join(ROOT, "examples", "example_board.pcbt.json"))
    new = peak_error_percent(p, 4.0, None, 60)
    old = peak_error_percent(p, 4.0, None, 60, theta_scheme=1.0, first_stage_split=1)
    assert abs(new[0]) < 1.0 and np.abs(new).max() < 0.5
    assert old[0] < -5.0


def test_euler_with_the_quarter_steps_improves_the_first_frame_and_keeps_the_later_ones():
    """!
    @brief Implicit Euler with the first stage in quarter steps: the first frame of the two-layer board moves from -3.7 % to -0.9 % (measured) and the last frames are those of
           one step per frame within 0.01 point (the later stages are not split; the early difference dies out).
    @return None.
    """
    p = two_layer()
    one = peak_error_percent(p, 2.0, None, 60, theta_scheme=1.0, first_stage_split=1)
    four = peak_error_percent(p, 2.0, None, 60, theta_scheme=1.0, first_stage_split=4)
    assert abs(four[0]) < abs(one[0]) / 3.0
    assert np.allclose(four[-20:], one[-20:], atol=1e-2)      # the later stages are walked the same; the early state differs and its difference dies out


def test_the_grid_keeps_the_nominal_output_times_and_has_four_steps_behind_the_first_frame():
    """!
    @brief `fvm.transient_grid`: the output times do not depend on the split, the steps sum to the output times, the first stage has `split` steps per frame, a linear run is unchanged.
    @return None.
    """
    hs1, e1, t1 = fvm.transient_grid(500.0, 40, 4, True, 1)
    hs4, e4, t4 = fvm.transient_grid(500.0, 40, 4, True, 4)
    assert np.array_equal(t1, t4) and e1.all() and e4.sum() == e1.sum() == 40
    assert np.allclose(np.cumsum(hs4)[e4], t4[1:], rtol=1e-12) and np.isclose(t4[-1], 500.0)
    assert np.flatnonzero(e4)[0] == 3 and np.isclose(hs4[0], t4[1] / 4.0)           # four steps behind the first frame
    assert hs4.size == hs1.size + 3 * 4                                              # per_stage = 4 at 40 frames
    hl, el, tl = fvm.transient_grid(100.0, 5, 4, False, 4)
    assert hl.size == 20 and el.sum() == 5 and np.allclose(tl, np.linspace(0.0, 100.0, 6))


def test_the_start_is_two_euler_half_steps_then_crank_nicolson():
    """!
    @brief A three-node network stepped by a dense reference written here: two implicit-Euler half steps for the first step, Crank-Nicolson after; the program's frames equal it.
    @return None.
    """
    k = np.array([[3.0, -1.0, 0.0], [-1.0, 3.0, -1.0], [0.0, -1.0, 2.0]]) * 0.7
    c = np.array([2.0, 1.0, 0.5])
    q = np.array([1.0, 0.0, 0.0])

    class Net:
        """! @brief Minimal network with the attributes of `fvm.Network` that `transient_from_network` reads. @param self Object. @return None. """
        nl, ny, nx = 1, 1, 3
        K = sp.csc_matrix(k)
        C = c.reshape(1, 1, 3)
        Q = q.reshape(1, 1, 3)
        area = np.ones((1, 3))

        def solve_steady(self):
            """! @brief Steady rise. @param self Object. @return Tuple (rise, residual). """
            return np.linalg.solve(k, q), 0.0

    hs, emit, times = fvm.transient_grid(20.0, 10, 4, True, 4)
    tr = fvm.transient_from_network(Net(), 0.0, 20.0, 10, theta_scheme=0.5)
    x, out, d = np.zeros(3), [], np.diag(c)
    for i, h in enumerate(hs):
        if i == 0:
            for _ in range(2):
                x = np.linalg.solve(d / (h / 2) + k, d @ x / (h / 2) + q)
        else:
            x = np.linalg.solve(d / h + 0.5 * k, (d / h - 0.5 * k) @ x + q)
        if emit[i]:
            out.append(x.copy())
    assert np.allclose(tr.frames[1:, 0, 0, :], np.array(out), rtol=1e-10, atol=1e-12)


def test_crank_nicolson_default_is_monotone_at_the_defaults_and_conserves_the_end_state():
    """!
    @brief At the Animation and command-line defaults the peak of the two-layer and example boards rises monotonically and ends within 0.1 % of the steady value after ten time
           constants (the ringing of Crank-Nicolson shows only far beyond the run: the full measurement is in the study).
    @return None.
    """
    p = two_layer()
    for t_end, n in ((None, 60), (600.0, 40), (None, 20)):
        tr = fvm.solve_transient(p, t_end if t_end else 5 * fvm.estimate_time_constant(p), n, 2.0)
        assert np.all(np.diff(tr.t_max) > 0.0)
    long = fvm.solve_transient(p, 12 * fvm.estimate_time_constant(p), 60, 2.0)
    assert abs(long.t_max[-1] / long.steady_t_max - 1.0) < 1e-3


def test_the_defaults_are_crank_nicolson_and_euler_stays_selectable():
    """!
    @brief The default theta of `fvm.solve_transient`, `fdm.solve_transient`, `fem.solve_transient` and of `transient --theta` is 0.5; implicit Euler (1.0) is still accepted by all three, and a theta of 1
           with one step per frame is the stepping of 2.8 bit for bit (the frames equal an Euler run that is not split).
    @return None.
    """
    for fn in (fvm.solve_transient, fdm.solve_transient):
        sig = inspect.signature(fn).parameters
        assert sig["theta_scheme"].default == 0.5 == fvm.DEFAULT_THETA and sig["first_stage_split"].default == 4 and sig["rannacher"].default is True
    # The FEM run follows (review): the Animation tab and `transient --model fem` pass the box or --theta anyway, and its Python default no longer differs from the FVM's
    assert inspect.signature(fem.solve_transient).parameters["theta_scheme"].default == fvm.DEFAULT_THETA and fem.FIRST_STAGE_SPLIT == fvm.FIRST_STAGE_SPLIT
    parser = cli.build_parser()
    args = parser.parse_args(["transient", "x.pcbt.json"])
    assert args.theta == 0.5
    assert parser.parse_args(["transient", "x.pcbt.json", "--theta", "1"]).theta == 1.0
    p = two_layer()
    a = fvm.solve_transient(p, 300.0, 20, 4.0, theta_scheme=1.0, first_stage_split=1)
    b = fvm.solve_transient(p, 300.0, 20, 4.0, theta_scheme=1.0, first_stage_split=1, rannacher=True)       # the start applies to theta < 1 only
    assert np.array_equal(a.frames, b.frames)


def test_the_fdm_has_the_same_default_stepping():
    """!
    @brief The FDM run (the same code on the node network) at the defaults: first frame within 1 % of its own reference on the two-layer board, as the FVM.
    @return None.
    """
    p = two_layer()
    net = fdm.Network(p, 2.0)
    tr = fvm.transient_from_network(net, p.board.ambient, 600.0, 40, grid="nodes")
    one = fvm.transient_from_network(net, p.board.ambient, 600.0, 40, theta_scheme=1.0, first_stage_split=1, grid="nodes")
    fine = fvm.transient_from_network(net, p.board.ambient, 600.0, 40, theta_scheme=1.0, first_stage_split=512, grid="nodes")
    rel = lambda r: (r.t_max[1] - p.board.ambient) / (fine.t_max[1] - p.board.ambient) - 1.0          # the first frame, the stepping error only
    assert abs(rel(tr)) < 0.01 < abs(rel(one))
