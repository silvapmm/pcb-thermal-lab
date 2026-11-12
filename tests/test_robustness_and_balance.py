#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_robustness_and_balance.py
@brief Gaps of the test strategy found by the independent review: the traceback of a failed job, the energy balance of the transient and of every feature combined, the SOR fallback, the maximum principle and the monotone response on random boards, the `blocks` key and the floor of the via well.
"""

import copy
import math
import os
import queue

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, copper, fdm, fvm, jobs, simulate, viawell


# ------------------------------------------------------------------------------------------------------- the calculation process
def _serve_one(name):
    """!
    @brief Run one job through `jobs.serve` in this process and return the message it puts back.
    @param name Key of JOBS.
    @return Tuple (kind, payload) of the last message.
    """
    tasks, results = queue.Queue(), queue.Queue()
    tasks.put((7, name, ()))
    tasks.put(None)
    jobs.serve(tasks, results)
    last = None
    while not results.empty():
        last = results.get_nowait()
    for h in jobs.log.handlers:
        h.flush()
    return last[1], last[2]


def test_a_failing_job_logs_the_traceback_and_sends_a_short_safe_message(monkeypatch):
    """!
    @brief An unexpected exception leaves its full traceback in the log file of the configuration folder and the window gets a short message without a path.
    @param monkeypatch pytest fixture.
    @return None.
    """
    def boom(progress):
        """!
        @brief A job with a bug.
        @param progress Progress callback (unused).
        @return None.
        """
        raise IndexError("index 9 is out of bounds " + "x" * 2000)

    monkeypatch.setitem(jobs.JOBS, "boom", boom)
    kind, msg = _serve_one("boom")
    assert kind == "failed"
    assert "index 9 is out of bounds" in msg and len(msg) < jobs.MAX_MESSAGE_CHARS + 200 and jobs.LOG_NAME in msg
    assert os.sep not in msg and "Traceback" not in msg                     # No path, no traceback in what a screenshot shows
    text = open(os.path.join(os.environ["PCBTHERMAL_CONFIG"], jobs.LOG_NAME), encoding="utf-8").read()
    assert "Traceback (most recent call last)" in text and "in boom" in text and "IndexError" in text and "job boom failed" in text


def test_a_refusal_of_the_input_is_shown_as_it_is(monkeypatch):
    """!
    @brief A ValueError (a refusal of the input) goes back unchanged, with no pointer to the log.
    @param monkeypatch pytest fixture.
    @return None.
    """
    def refuse(progress):
        """!
        @brief A job that refuses.
        @param progress Progress callback (unused).
        @return None.
        """
        raise ValueError("the board is too large")

    monkeypatch.setitem(jobs.JOBS, "refuse", refuse)
    assert _serve_one("refuse") == ("failed", "the board is too large")


def test_an_unwritable_log_folder_does_not_break_the_message(monkeypatch, tmp_path):
    """!
    @brief A configuration folder that cannot be created leaves the message intact.
    @param monkeypatch pytest fixture.
    @param tmp_path pytest fixture.
    @return None.
    """
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(blocker / "sub"))             # A folder below a file: makedirs fails
    monkeypatch.setitem(jobs.JOBS, "bad", lambda progress: 1 / 0)
    kind, msg = _serve_one("bad")
    assert kind == "failed" and "division by zero" in msg


def test_a_path_in_the_home_folder_is_not_shown(monkeypatch):
    """!
    @brief An exception that names a file of the user (an OSError) shows the home folder as `~` in the window; the log keeps the full text.
    @param monkeypatch pytest fixture.
    @return None.
    """
    home = os.path.expanduser("~")

    def missing(progress):
        """!
        @brief A job that fails on a file in the home folder.
        @param progress Progress callback (unused).
        @return None.
        """
        raise FileNotFoundError(2, "No such file or directory", os.path.join(home, "secret-user-folder", "board.pcbt.json"))

    monkeypatch.setitem(jobs.JOBS, "missing", missing)
    kind, msg = _serve_one("missing")
    assert kind == "failed" and home not in msg and "~" in msg and "board.pcbt.json" in msg


def test_a_new_configuration_folder_gets_the_traceback_alone(monkeypatch, tmp_path):
    """!
    @brief When the configuration folder changes in the same process, the old log handler is closed: the next traceback goes to the new file only, and the handler rotates.
    @param monkeypatch pytest fixture.
    @param tmp_path pytest fixture.
    @return None.
    """
    import logging.handlers
    first, second = tmp_path / "a", tmp_path / "b"
    monkeypatch.setitem(jobs.JOBS, "bad", lambda progress: 1 / 0)
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(first))
    _serve_one("bad")
    size_first = (first / jobs.LOG_NAME).stat().st_size
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(second))
    _serve_one("bad")
    assert (first / jobs.LOG_NAME).stat().st_size == size_first and "ZeroDivisionError" in (second / jobs.LOG_NAME).read_text(encoding="utf-8")
    mine = [h for h in jobs.log.handlers if getattr(h, "baseFilename", "").endswith(jobs.LOG_NAME)]
    assert len(mine) == 1 and isinstance(mine[0], logging.handlers.RotatingFileHandler) and mine[0].maxBytes == jobs.LOG_MAX_BYTES


def test_the_process_that_dies_is_reported(qtbot):
    """!
    @brief A calculation process killed during a job (the real process) ends the job as failed and the next job still runs.
    @param qtbot pytest-qt fixture.
    @return None.
    """
    from pcbthermal.gui import compute
    compute.shutdown()
    try:
        w, errors, later, out = compute.ProcessWorker("sleep", 60.0), [], compute.ProcessWorker("sleep", 0.1), []
        w.failed.connect(errors.append)
        later.done.connect(out.append)
        compute.start(w)
        qtbot.waitUntil(lambda: w.state == "running", timeout=60000)
        compute.ENGINE.process.kill()
        qtbot.waitUntil(lambda: bool(errors), timeout=60000)
        assert "stopped unexpectedly" in errors[0]
        compute.start(later)
        qtbot.waitUntil(lambda: bool(out), timeout=60000)
    finally:
        compute.shutdown()


# ------------------------------------------------------------------------------------------------------- reporting and the well
def test_blocks_key_only_with_a_metal_block():
    """!
    @brief `power_out` has the key `blocks` only on a board with a metal block (the laminate rule fills `extra_links` on every board with a cut gap).
    @return None.
    """
    p = Problem.new(30, 20, 2).add_zone(1, rect=(0, 0, 30, 20)).add_heater(1, 1.0, rect=(10, 8, 14, 12))
    for res in (fvm.solve_steady(p, 1.0), fdm.solve_steady(p, 1.0)):
        assert "blocks" not in res.power_out
    p.add_heatsink(2, 5.0, rect=(5, 5, 25, 15), thickness_mm=2.0)
    for res in (fvm.solve_steady(p, 1.0), fdm.solve_steady(p, 1.0)):
        assert "blocks" in res.power_out and res.power_out["blocks"] > 0.0 and abs(res.balance_error) < 1e-9


def test_a_near_infinite_well_is_floored_and_normal_wells_are_untouched():
    """!
    @brief The well conductance has a floor on its logarithm (1e-6); wells with an ordinary logarithm are bit-identical to 2 pi S / ln(r_eff / r_t).
    @return None.
    """
    s, r_t = 0.0142, 1.0e-4
    for ratio in (1.5, 3.0, 40.0):
        assert viawell.well_conductance(s, ratio * r_t, r_t) == 2.0 * math.pi * s / math.log(ratio)
        assert viawell.well_conductance(s, ratio * r_t, r_t, 0.05) == 2.0 * math.pi * s / (math.log(ratio) + 0.05)
    tiny = viawell.well_conductance(s, r_t * (1.0 + 1e-8), r_t)               # ln = 1e-8: finite, but not the 2 pi S 1e8 of the raw formula
    assert tiny == pytest.approx(2.0 * math.pi * s / viawell.WELL_LOG_FLOOR)
    assert viawell.well_conductance(s, r_t * (1.0 + 1e-10), r_t) == math.inf   # Below 1e-9 the mean is the barrel potential (unchanged rule)
    g = viawell.kron_barrel(np.array([0.01, 0.01]), np.array([tiny, 5.0, tiny]))
    assert np.all(np.isfinite(g)) and np.allclose(g, g.T) and np.all(np.diag(g) == 0.0)


# ------------------------------------------------------------------------------------------------------- balances
def _combined(imported, block=True):
    """!
    @brief A board with every feature at once: an L outline, the edge coefficient, a cut gap (laminate band), a via array, optionally a metal block and imported copper.
    @param imported True to give the two layers imported copper (stripes on the top, solid bottom); False to draw zones.
    @param block True to add a metal block under the heater.
    @return Problem.
    """
    p = Problem.new(40, 30, 2, h_side=50.0, h_top=10.0, h_bottom=10.0)
    p.set_outline([[0, 0], [40, 0], [40, 15], [25, 15], [25, 30], [0, 30]])
    p.add_heater(1, 2.0, rect=(6, 6, 10, 10))
    p.add_via_array((12, 4, 16, 8), 3, 3, diameter=0.3)
    if block:
        p.add_heatsink(2, 5.0, rect=(4, 4, 18, 12), thickness_mm=2.0)
    if imported:
        top = np.full((300, 400), 255, np.uint8)
        top[:, ::7] = 0                                                      # Stripes: copper edges that cut the cells
        p.imported = copper.imported_from_rasters([top, np.full((300, 400), 255, np.uint8)], 0.1, "faces")
    else:
        p.add_zone(1, rect=(0, 0, 40, 30))
        p.add_zone(2, rect=(0, 0, 22, 30))                                   # Bottom copper on part of the board: the laminate rule cuts the gap into sub-gaps there
    return p


@pytest.mark.parametrize("block", [False, True])
@pytest.mark.parametrize("imported", [False, True])
def test_heat_balance_with_every_feature_combined(imported, block):
    """!
    @brief Outline + h_side + laminate band + vias + metal block (+ imported copper): the heat that leaves equals the heat that enters in the five models (the Analytic closes to its GMRES tolerance).
    @param imported True for imported copper.
    @param block True for the metal block (which switches the laminate ladder off); False keeps the ladder with the edge band.
    @return None.
    """
    sim = simulate(_combined(imported, block=block), SolverOptions(models=("fvm", "fdm", "solid3d", "lumped", "analytic"), cell_mm=1.0))
    for name, tol in (("fvm", 1e-9), ("fdm", 1e-9), ("solid3d", 1e-9), ("lumped", 1e-9), ("analytic", 1e-6)):
        r = sim.results[name]
        assert abs(r.balance_error) < tol, (name, r.balance_error)
        assert r.power_out["sides"] > 0.0 and (r.power_out.get("blocks", 0.0) > 0.0) == block, name
        assert sum(r.power_out.values()) == pytest.approx(2.0, rel=tol), name


@pytest.mark.parametrize("block", [False, True])
@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_transient_energy_balance(model, block):
    """!
    @brief Stored energy plus the heat lost over a power step equals the energy put in, for every node of the network (copper, laminate sub-gap nodes and the metal block), with a via array, an outline and the edge coefficient.
    @details The step is marched here with implicit Euler on the K, C and Q of the network, so that the laminate and block nodes (which the frames of `transient_from_network` leave out) are in the account.
             The sum holds for ANY positive C (review: C scaled by 2 or by random factors closes it to 1e-12), so it checks that the links of K conserve heat and that the
             loss vector is the row sum of K, not the capacities: those are checked against the closed form in `test_heat_capacity_equals_the_closed_form`. The march is
             then compared with the program's stepper (`transient_from_network`, same steps), so that the balance also holds for the field the program shows.
    @param model "fvm" or "fdm".
    @param block True for a board with a metal block (which has the legacy two laminate nodes, no sub-gap ladder), False for the ladder of sub-gaps.
    @return None.
    """
    import scipy.sparse as sp
    import scipy.sparse.linalg as spla
    p = _combined(False, block=block)
    net = fvm.Network(p, 40, 30) if model == "fvm" else fdm.Network(p, 1.0)
    assert net.nl > net.n_board + (0 if block else 1)                        # Laminate sub-gap nodes (no block) or the block layer are in the account
    t_end, steps = 2.0e3, 80
    dt = t_end / steps
    C, q, g_loss = net.C.ravel(), net.Q.ravel(), (net.g_amb - net.g_pin).ravel()   # The pin of the cells off the board is not a path to the air
    lu = spla.splu((sp.diags(C / dt) + net.K).tocsc())
    x, lost = np.zeros_like(q), 0.0
    for _ in range(steps):
        x = lu.solve(C / dt * x + q)
        lost += dt * float(g_loss @ x)                                       # Implicit Euler: the loss of a step uses the new field
    stored, put_in = float(C @ x), float(q.sum()) * t_end
    assert float(q.sum()) == pytest.approx(2.0)
    assert stored + lost == pytest.approx(put_in, rel=1e-9)
    assert stored > 0.0 and lost > 0.0 and stored < put_in                   # Neither side is trivial
    frames = fvm.transient_from_network(net, 0.0, t_end, n_out=4, substeps=steps // 4, log_times=False).frames
    assert np.allclose(frames[-1], x.reshape(net.nl, net.ny, net.nx)[:net.n_board], rtol=0, atol=1e-8)   # The library stepper gives the same field


@pytest.mark.parametrize("model", ["fvm", "fdm"])
@pytest.mark.parametrize("half", [False, True])
def test_heat_capacity_equals_the_closed_form(model, half):
    """!
    @brief The total heat capacity of the network is rho c V of the copper and the laminate, also when the bottom copper covers half the board (laminate sub-gap ladder, the copper replaced by laminate of the same thickness).
    @param model "fvm" or "fdm".
    @param half True to draw the bottom copper over half the board.
    @return None.
    """
    p = Problem.new(40, 30, 2).add_zone(1, rect=(0, 0, 40, 30)).add_heater(1, 1.0, rect=(10, 8, 14, 12)).add_zone(2, rect=(0, 0, 20 if half else 40, 30))
    b, m = p.board, p.board.materials
    area, t_cu = 40e-3 * 30e-3, b.copper_thickness[0]
    cu, fr4 = m.rho_copper * m.cp_copper, m.rho_fr4 * m.cp_fr4
    expected = area * (b.thickness - 2 * t_cu) * fr4 + area * t_cu * cu + area * t_cu * (cu if not half else 0.5 * (cu + fr4))
    net = fvm.Network(p, 40, 30) if model == "fvm" else fdm.Network(p, 1.0)
    assert net.nl > 2 if half else True                                      # The half board has the laminate ladder
    assert float(net.C.sum()) == pytest.approx(expected, rel=1e-12)


# ------------------------------------------------------------------------------------------------------- the SOR paths
def test_sor_falls_back_to_the_direct_solver_when_the_via_blocks_do_not_fit():
    """!
    @brief On an outline board with vias and the laminate band, a memory limit too small for the dense via blocks sends the SOR to the direct solver (same field); with room the block SOR converges to it.
    @return None.
    """
    net = fvm.Network(_combined(False, block=False), 40, 30)
    direct, _ = net.solve_steady("direct")
    theta, _, info = net.solve_sor(memory_limit=100.0)
    assert info.get("fallback") == "direct" and info["block"] > 0
    assert np.allclose(theta, direct, rtol=0, atol=1e-9)
    ok_theta, _, ok_info = net.solve_sor(memory_limit=None)
    assert ok_info.get("fallback") != "direct" and ok_info["converged"]
    assert np.allclose(ok_theta, direct, rtol=0, atol=1e-5)


def test_sor_refuses_a_metal_block():
    """!
    @brief SOR does not support a metal block: it says so instead of returning a wrong field.
    @return None.
    """
    with pytest.raises(ValueError):
        fvm.Network(_combined(False), 40, 30).solve_sor()


# ------------------------------------------------------------------------------------------------------- random boards
def _random_board(rng, vias):
    """!
    @brief A random board: size, layers, film coefficients, an optional outline, 1 to 3 heaters, zones with random fill, optionally a via array.
    @param rng numpy Generator.
    @param vias True to add a via array.
    @return Problem.
    """
    w, h = float(rng.uniform(30, 60)), float(rng.uniform(20, 40))
    layers = int(rng.integers(2, 5))
    p = Problem.new(w, h, layers, h_top=float(rng.uniform(5, 30)), h_bottom=float(rng.uniform(5, 30)), h_side=float(rng.choice([0.0, 20.0, 100.0])))
    if rng.random() < 0.5:
        p.set_outline([[0, 0], [w, 0], [w, h * 0.5], [w * 0.6, h * 0.5], [w * 0.6, h], [0, h]])
    for ly in range(1, layers + 1):
        p.add_zone(ly, rect=(0, 0, w, h), fill=float(rng.uniform(0.3, 1.0)))
    for _ in range(int(rng.integers(1, 4))):
        x, y = float(rng.uniform(3, w * 0.5 - 4)), float(rng.uniform(3, h * 0.5 - 4))
        p.add_heater(1, float(rng.uniform(0.5, 3.0)), rect=(x, y, x + float(rng.uniform(2, 5)), y + float(rng.uniform(2, 5))))
    if vias:
        p.add_via_array((w * 0.1, h * 0.1, w * 0.1 + 6, h * 0.1 + 6), 3, 3, diameter=0.3)
    return p


def _scaled(p, power=1.0, h=1.0):
    """!
    @brief A copy of the problem with every heater power and every film coefficient multiplied.
    @param p Problem.
    @param power Factor of the power.
    @param h Factor of the film coefficients (faces and edge).
    @return Problem.
    """
    q = copy.deepcopy(p)
    for hh in q.heaters:
        hh.power *= power
    q.board.h_top *= h
    q.board.h_bottom *= h
    if q.board.h_side:
        q.board.h_side *= h
    return q


@pytest.mark.parametrize("seed", range(4))
def test_maximum_principle_and_monotone_response_on_random_boards(seed):
    """!
    @brief Random boards without vias: no cell is below the ambient, the hottest temperature is linear in the power and falls as the film coefficients grow (FVM and FDM).
    @param seed Seed of the board.
    @return None.
    """
    p = _random_board(np.random.default_rng(1000 + seed), vias=False)
    amb = p.board.ambient
    for solver in (fvm.solve_steady, fdm.solve_steady):
        r = solver(p, 2.0)
        assert np.nanmin(r.T) >= amb - 1e-9                                  # No cold spot: the maximum principle of a network with positive links
        rises = [solver(_scaled(p, power=f), 2.0).t_max - amb for f in (0.5, 1.0, 2.0)]
        assert rises[0] < rises[1] < rises[2]
        assert rises[1] == pytest.approx(2.0 * rises[0], rel=1e-6) and rises[2] == pytest.approx(2.0 * rises[1], rel=1e-6)   # Constant coefficients: affine in the power
        hot = [solver(_scaled(p, h=k), 2.0).t_max for k in (1.0, 2.0, 4.0)]
        assert hot[0] > hot[1] > hot[2]


@pytest.mark.parametrize("seed", range(3))
def test_random_boards_with_vias_close_the_balance(seed):
    """!
    @brief Random boards with a via array: the heat balance closes in the FVM and the FDM, and the vias never raise the hottest temperature above the board without them.
    @param seed Seed of the board.
    @return None.
    """
    p = _random_board(np.random.default_rng(2000 + seed), vias=True)
    plain = _random_board(np.random.default_rng(2000 + seed), vias=False)
    for solver in (fvm.solve_steady, fdm.solve_steady):
        r = solver(p, 2.0)
        assert abs(r.balance_error) < 1e-9
        assert r.t_max <= solver(plain, 2.0).t_max + 1e-6
