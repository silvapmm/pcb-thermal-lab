#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_profile_adapter.py
@brief The power-profile run of the finite-element model (`profiles.run_fem`, `_FEMAdapter`), its refusals and its place in the API: the adapter interface, the energy and the
       periodicity of a window on a small plate, implicit Euler against a direct stepper on the same matrices, the work limit and the memory refusal before the run, the FEM step
       response (and the latent defect that sent any unknown model to the Analytic), a refusal that does not stop the other models, the FEM alone.
@details Light: a plate of 60 mm at a 5 mm cell and three elements across the gaps (a few thousand unknowns, the direct path), one at a time.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "regression"))
import regress_boards as B                                                  # noqa: E402
from pcbthermal import SolverOptions, SquareWave, api, femcore, fem, fvm, memory, profiles          # noqa: E402
from pcbthermal.profiles import ProfileError, ProfileOptions                # noqa: E402

CELL = 5.0
GAP = 3


def _plate():
    """!
    @brief The 60 mm plate of the harness with its heater on a 60 s square wave (30 % on, 5 W on-power).
    @return Tuple (problem, decisions).
    """
    p = B.build("plate_uniform")
    p.heaters[0].set_profile(SquareWave(p_on=5.0, period=60.0, duty=0.3))
    resp = profiles.step_response_fvm(p, 2.0)
    d = profiles.decide(p, resp, 0.001)                                    # a threshold that resolves the wave
    assert d[0].regime == "resolved"
    return p, d


def test_the_adapter_interface_and_the_exact_energy_of_a_window():
    """!
    @brief The adapter has the interface of `run_windows`; over one window of the periodic state the energy in (the step means) equals the energy out through the films, to 1e-6 of
           the input per period, and the last two windows repeat.
    @return None.
    """
    p, d = _plate()
    opts = ProfileOptions(duration="stable", stable_c=1e-4, max_windows=60)
    ad = profiles._FEMAdapter(p, CELL, GAP)
    for name in ("dx", "dy", "ambient", "steady_average_max", "steady_peak_max", "offset"):
        assert hasattr(ad, name)
    r = profiles.run_windows(p, d, opts, ad, "fem")
    assert r.resolved and r.converged and r.model == "fem"
    assert r.steady_peak_max > r.steady_average_max > p.board.ambient
    assert r.oscillation > 0.0 and r.frames.shape[1:] == ad.shape
    # the energy of the periodic state: reconstruct one window from the adapter (same steps), start from the state at the end of the run, and balance it
    state, _ = ad.begin(opts)
    ad.prepare(r.dt)
    n = int(round(r.window / r.dt))
    w = p.heaters[0].profile
    gam = ad.asm["gam"][ad.asm["used"]]
    for k in range(8 * n):                                                  # settle
        t0 = k * r.dt
        state = ad.advance(state, r.dt, np.array([w.mean_power(t0, t0 + r.dt)]))
    e_in = e_loss = 0.0
    stored0 = float(ad.asm["m_lump"] @ state)
    for k in range(8 * n, 9 * n):
        t0 = k * r.dt
        pw = w.mean_power(t0, t0 + r.dt)
        new = ad.advance(state, r.dt, np.array([pw]))
        e_in += pw * r.dt
        e_loss += r.dt * float(gam @ new)                                   # Euler: the loss of the end of the step
        state = new
    stored1 = float(ad.asm["m_lump"] @ state)
    assert abs((e_in - e_loss - (stored1 - stored0)) / e_in) < 1e-6


def test_implicit_euler_equals_a_direct_stepper_on_the_same_matrices():
    """!
    @brief The adapter's steps equal a hand-written implicit-Euler march `(M/dt + A) T1 = M T0/dt + F p` with SuperLU on the same assembled matrices to round-off.
    @return None.
    """
    import scipy.sparse.linalg as spla
    p, d = _plate()
    ad = profiles._FEMAdapter(p, CELL, GAP)
    opts = ProfileOptions()
    state, _ = ad.begin(opts)
    dt = 0.5
    ad.prepare(dt)
    lu = spla.splu((ad.asm["M"] / dt + ad.asm["A"]).tocsc())
    ref = state.copy()
    for pw in (5.0, 5.0, 0.0, 0.0, 2.5):
        state = ad.advance(state, dt, np.array([pw]))
        ref = lu.solve(ad.asm["M"] @ ref / dt + ad.F @ np.array([pw]))
    assert np.abs(state - ref).max() < 1e-10 * np.abs(ref).max()


def test_fem_profile_agrees_with_the_fvm_within_the_model_difference():
    """!
    @brief At a 3 mm cell the peak and the minimum of the FEM run are within 3 % of the FVM's rise and the oscillation within 4 %, and the run reaches the same fraction of its own
           steady peak within 2 % (the models differ by 1 to 2 % in the steady state of this plate; at a 5 mm cell by 4 to 6 %, which is the steady difference and not the stepping).
    @return None.
    """
    p, d = _plate()
    opts = ProfileOptions(duration="stable")
    a = profiles.run_fem(p, d, opts, 3.0, gap_elements=GAP)
    b = profiles.run_fvm(p, d, opts, 3.0)
    amb = p.board.ambient
    assert abs((a.peak - amb) / (b.peak - amb) - 1.0) < 0.03
    assert abs((a.minimum - amb) / (b.minimum - amb) - 1.0) < 0.03
    assert abs(a.oscillation / b.oscillation - 1.0) < 0.04
    assert abs((a.peak - amb) / (a.steady_peak_max - amb) / ((b.peak - amb) / (b.steady_peak_max - amb)) - 1.0) < 0.02


def test_crank_nicolson_in_the_runner_agrees_with_euler():
    """!
    @brief The runner honours `ProfileOptions.theta`: Crank-Nicolson with the step-mean load gives the peak of the Euler run within 1 % of the rise on a slow wave (hypothesis H2 of
           the design note: no ringing above 1 % of the swing).
    @return None.
    """
    p, d = _plate()
    e = profiles.run_fem(p, d, ProfileOptions(theta=1.0), CELL, gap_elements=GAP)
    c = profiles.run_fem(p, d, ProfileOptions(theta=0.5), CELL, gap_elements=GAP)
    assert abs(c.peak - e.peak) < 0.01 * (e.peak - p.board.ambient)
    assert abs(c.oscillation - e.oscillation) < 0.01 * e.oscillation


def test_the_work_limit_refuses_before_the_mesh_is_built(monkeypatch):
    """!
    @brief A run whose predicted time (unknowns x steps x the per-step cost) is above the limit raises ProfileError with the text of `plan_run`, and builds no mesh.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p, d = _plate()
    monkeypatch.setattr(memory, "FEM_RUN_SECONDS_MAX", 1e-3)
    built = []
    monkeypatch.setattr(profiles, "_FEMAdapter", lambda *a, **k: built.append(1))
    with pytest.raises(ProfileError, match="needs about .* steps"):
        profiles.run_fem(p, d, ProfileOptions(), CELL, gap_elements=GAP)
    assert not built


def test_a_run_longer_than_twice_the_limit_is_stopped_while_it_steps(monkeypatch):
    """!
    @brief The bound of `run_fem` is a prediction (a run 'until stable' may need more windows than the plan counts): the adapter also stops the stepping past twice
           `memory.FEM_RUN_SECONDS_MAX` of wall time with a ProfileError (review), which `api` turns into the warning 'FEM: refused'.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p, d = _plate()
    monkeypatch.setattr(memory, "fem_transient_seconds", lambda n, s, st=1.0: 0.0)       # the prediction lets it start
    monkeypatch.setattr(memory, "FEM_RUN_SECONDS_MAX", 1e-9)                       # and the wall clock stops it at the first step
    with pytest.raises(ProfileError, match="was stopped after"):
        profiles.run_fem(p, d, ProfileOptions(), CELL, gap_elements=GAP)


def test_a_memory_refusal_comes_before_the_run_and_a_cancel_is_a_cancel():
    """!
    @brief With a fraction of the memory that cannot hold the mesh `run_fem` raises the guard's error before any build; a cancel callable stops the build, and one that turns True after 30 steps stops the stepping, with FemCancelled.
    @return None.
    """
    p, d = _plate()
    with pytest.raises(memory.MemoryGuardError):
        profiles.run_fem(p, d, ProfileOptions(), CELL, gap_elements=GAP, memory_fraction=memory.MIN_FRACTION * 1e-6)
    with pytest.raises(femcore.FemCancelled):
        profiles.run_fem(p, d, ProfileOptions(), CELL, gap_elements=GAP, cancel=lambda: True)
    # a cancel in the middle of the stepping (review): the callable says True only after the build and a few dozen solves of the windows
    calls = []
    st_solves = []
    orig_step = femcore.Stepper.step

    def counting_step(self, *a, **k):
        """!
        @brief Count the steps taken before the cancel.
        @param self The stepper.
        @param a Positional arguments of `Stepper.step`.
        @param k Keyword arguments of `Stepper.step`.
        @return The new field.
        """
        st_solves.append(1)
        return orig_step(self, *a, **k)
    femcore.Stepper.step = counting_step
    try:
        with pytest.raises(femcore.FemCancelled):
            profiles.run_fem(p, d, ProfileOptions(), CELL, gap_elements=GAP, cancel=lambda: (calls.append(1) or len(st_solves) > 30))
    finally:
        femcore.Stepper.step = orig_step
    assert 30 < len(st_solves) < 40


def test_step_response_of_the_fem_is_the_fems_and_an_unknown_model_raises():
    """!
    @brief `api.step_response(p, "fem", o)` is the finite-element response (model "fem", z rising to rth), not the Analytic's, and a model with no step response (the 3D solid,
           an unknown key) raises ValueError: before 2.9.0 any such key was answered by the Analytic without a word.
    @return None.
    """
    p, _ = _plate()
    o = SolverOptions(models=("fvm", "fem"), cell_mm=CELL, fem_gap_elements=GAP)
    r = api.step_response(p, "fem", o)
    assert r.model == "fem" and r.z.shape[0] == 1 and r.z[0, -1] > 0.9 * r.rth[0]
    for bad in ("solid3d", "nope"):
        with pytest.raises(ValueError, match="no step response"):
            api.step_response(p, bad, o)


def test_a_fem_refusal_keeps_the_other_models_profile_and_names_the_fem(monkeypatch):
    """!
    @brief When the FEM is refused in the profile run (memory guard, no pyamg, no mesh, work limit) the FVM profile stands, the FEM has no result and one warning says
           'FEM: refused (reason)'; the run does not abort (also for conjugate gradients that do not converge in a step).
    @param monkeypatch pytest fixture.
    @return None.
    """
    p, _ = _plate()
    o = SolverOptions(models=("fvm", "fem"), cell_mm=CELL, fem_gap_elements=GAP)
    o.profile = ProfileOptions(threshold_c=0.001)
    for exc in (memory.MemoryGuardError("too big"), femcore.FemUnavailable("no pyamg"), ProfileError("too many steps"), ValueError("slanted outline"),
                RuntimeError("conjugate gradients did not converge (info 5000)")):         # the last one: a CG failure in a step (review: it aborted every model's profile)
        def boom(*a, _e=exc, **k):
            raise _e
        monkeypatch.setattr(profiles, "run_fem", boom)
        sim = api.simulate(p, o)
        assert "fvm" in sim.profile_results and "fem" not in sim.profile_results
        assert sum("FEM: refused" in str(w) for w in sim.warnings) == 1 and not sim.profile_error
    monkeypatch.setattr(profiles, "run_fem", lambda *a, **k: (_ for _ in ()).throw(femcore.FemCancelled("c")))
    with pytest.raises(femcore.FemCancelled):
        api.simulate(p, o)


def test_the_fem_alone_in_the_profile_tab_says_it_needs_another_model_and_both_run_together():
    """!
    @brief With only the FEM ticked the profile run gives the clear message (no reference: the FEM never decides); with the FVM beside it both profiles are in the result and the
           decision is the FVM's.
    @return None.
    """
    p, _ = _plate()
    o = SolverOptions(models=("fem",), cell_mm=CELL, fem_gap_elements=GAP)
    sim = api.simulate(p, o)
    assert sim.profile_error and "FEM runs in time beside" in sim.profile_error and not sim.profile_results
    o2 = SolverOptions(models=("fvm", "fem"), cell_mm=CELL, fem_gap_elements=GAP)
    o2.profile = ProfileOptions(threshold_c=0.001)
    sim2 = api.simulate(p, o2)
    assert sim2.profile_reference == "fvm" and set(sim2.profile_results) == {"fvm", "fem"}
    assert sim2.profile_results["fem"].resolved


def test_the_command_line_runs_the_fem_in_time_and_says_why_when_it_refuses(tmp_path, monkeypatch, capsys):
    """!
    @brief `transient --model fem` writes its table, and a refusal of the FEM (no pyamg above the direct limit, no mesh) is the message 'FEM: refused' with the exit code of a
           refusal, not a traceback (review).
    @param tmp_path pytest fixture.
    @param monkeypatch pytest fixture.
    @param capsys pytest fixture.
    @return None.
    """
    from pcbthermal import cli
    path = tmp_path / "ref.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    assert cli.main(["transient", str(path), "--model", "fem", "--t-end", "30", "--steps", "10", "--cell-mm", "6", "--theta", "0.5", "--out", str(tmp_path / "f"),
                     "--no-plots"]) == 0
    assert (tmp_path / "f" / "transient.csv").exists()

    def refuse(*a, **k):
        """!
        @brief Stand-in for `fem.solve_transient` that refuses like a missing pyamg.
        @param a Positional arguments.
        @param k Keyword arguments.
        @return Never.
        @throws femcore.FemUnavailable Always.
        """
        raise femcore.FemUnavailable("pyamg is not installed")
    monkeypatch.setattr(fem, "solve_transient", refuse)
    assert cli.main(["transient", str(path), "--model", "fem", "--t-end", "30", "--steps", "10", "--cell-mm", "6", "--out", str(tmp_path / "g"), "--no-plots"]) == memory.EXIT_CODE
    assert "FEM: refused (pyamg is not installed)" in capsys.readouterr().err
