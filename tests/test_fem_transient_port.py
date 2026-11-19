#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_transient_port.py
@brief Port test of the finite-element time stepper: the program's `femcore.Stepper` and `fem.march` against the independent research tool
       `research/independent-fem-extensions/lib/transient.py` (`Transient.march`, `Transient.step_response`) on the same mesh, the same heat capacity per element and the same steps.
@details The tool's `step_response` puts the two Rannacher half steps in the first two slots of the first stage, so its grid is shifted by one step against the program's
         nominal grid (the program keeps the nominal grid and adds the half steps, so that its output times are those of `fvm.transient_from_network`); the comparison is
         therefore made at the TOOL's own times, which the test checks are cumulative sums of the same step sizes. The tool runs with its consistent mass. Skipped when the research
         folders are absent. Light: a few seconds.
"""

import os
import sys

import numpy as np
import pytest

from pcbthermal import femcore as fc
from pcbthermal import fem

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from test_fem_port import _copy_into_core, research_modules             # noqa: E402


def _rho_c(model):
    """!
    @brief A heat capacity per element that varies from element to element (like the copper and laminate slabs of a board).
    @param model A model with E elements.
    @return numpy.ndarray (E,) in J/m3K.
    """
    rng = np.random.default_rng(11)
    return rng.choice([1.665e6, 3.45e6, 2.2e6], size=model.elems.shape[0])


def _program_run(model, rho_c, hs, emit, theta):
    """!
    @brief The program's march from rest on the model with its own load, the readouts of the test recorded at every output.
    @param model femcore.Model.
    @param rho_c Heat capacity per element in J/m3K.
    @param hs Step sizes in s.
    @param emit bool per step.
    @param theta 0.5 or 1.
    @return Tuple (list of fields at the output frames, final field, assembled dict).
    """
    model.rho_c[:] = rho_c
    a = model.assemble(capacity=True)
    st = fc.Stepper(a["A"], a["M"])
    frames = []
    T, _ = fem.march(st, a["M"], a["A"], a["rhs"], hs, emit, theta, lambda k, T: frames.append(T.copy()), start=True)
    return frames, T, a


def test_the_consistent_mass_equals_the_research_tool():
    """!
    @brief The mass matrix of `assemble(capacity=True)` equals the research `consistent_mass` on the used unknowns to round-off, and its row sums the `lumped_mass`.
    @return None.
    """
    with research_modules() as r:
        import transient as tr
        m_ref, _ = r["cases"].strong_edge(200, hf=0.6, hmax=1.5, n_gap=3).build()
        rc = _rho_c(m_ref)
        ref = tr.Transient(m_ref, rc, consistent=True)
        mine = _copy_into_core(m_ref)
        mine.rho_c[:] = rc
        a = mine.assemble(capacity=True)
        assert abs(a["M"] - ref.M).max() < 1e-12 * abs(ref.M).max()
        assert np.abs(a["m_lump"] - tr.lumped_mass(m_ref, rc)[a["used"]]).max() < 1e-12 * a["m_lump"].max()
        assert abs(a["capacity_total"] / float((rc * m_ref.element_volumes()).sum()) - 1.0) < 1e-12


def test_step_response_of_the_program_equals_the_tool_at_the_tools_own_times():
    """!
    @brief The nominal grid (dt0, six steps per level, doubling) with the Rannacher start: the program's field at every output equals the research `step_response` field at the
           same cumulative time to 1e-9 of the field scale, for Crank-Nicolson with the start; the tool's times are checked to be those of the program shifted by one slot.
    @return None.
    """
    with research_modules() as r:
        import transient as tr
        m_ref, _ = r["cases"].strong_edge(200, hf=0.6, hmax=1.5, n_gap=3).build()
        rc = _rho_c(m_ref)
        ref = tr.Transient(m_ref, rc, consistent=True)
        dt0, per_level, levels = 1e-3, 6, 4
        w = np.random.default_rng(5).random(ref.n)
        out = ref.step_response({"w": w, "hot": (np.arange(ref.n) == int(np.argmax(ref.steady()))).astype(float)}, t_end=dt0 * per_level * (2 ** levels - 1) * 0.999, dt0=dt0, per_level=per_level)
        # the program marches the TOOL's sequence of steps: the first stage is five steps of dt0 (the first one opened by the two half steps, so the stage ends at 5 dt0, one
        # step short of the nominal 6 dt0), the next stages six steps of 2 dt0, 4 dt0, ... The grid of the program's own runs keeps the nominal times (tests of `time_grid`)
        hs = [dt0] * (per_level - 1)
        for j in range(1, levels):
            hs += [dt0 * 2 ** j] * per_level
        emit = [True] * len(hs)
        frames, T_end, a = _program_run(_copy_into_core(m_ref), rc, np.asarray(hs), np.asarray(emit), 0.5)
        t_prog = np.cumsum(hs)
        t_tool = out["t"]
        # the tool also records the middle of the opened step (its record 1), so the program's frame k is the tool's record k + 1
        assert np.isclose(t_tool[1], 0.5 * hs[0]) and len(t_tool) == len(t_prog) + 2
        for k in range(1, len(t_prog) + 1):
            assert np.isclose(t_tool[k + 1], t_prog[k - 1], rtol=1e-12), (k, t_tool[k + 1], t_prog[k - 1])
        # fields: the readouts of the tool are w @ T and the hottest node (at the steady maximum); compare the two series
        got_w = np.array([float(w @ f) for f in frames])
        assert len(frames) == len(out['series']['w']) - 2
        got_hot = np.array([float(f[int(np.argmax(ref.steady()))]) for f in frames])
        assert np.abs(got_w - out["series"]["w"][2:2 + len(frames)]).max() < 1e-9 * np.abs(got_w).max()
        assert np.abs(got_hot - out["series"]["hot"][2:2 + len(frames)]).max() < 1e-9 * np.abs(got_hot).max()
        assert np.abs(T_end - out["T"]).max() < 1e-9 * np.abs(out["T"]).max()


def test_euler_and_a_square_wave_march_equal_the_tool():
    """!
    @brief Implicit Euler (no start) from rest and a Crank-Nicolson run from a non-zero start with a zero load equal the tool's `march` to 1e-9 of the field scale.
    @return None.
    """
    with research_modules() as r:
        import transient as tr
        m_ref, _ = r["cases"].strong_edge(200, hf=0.6, hmax=1.5, n_gap=3).build()
        rc = _rho_c(m_ref)
        ref = tr.Transient(m_ref, rc, consistent=True)
        mine = _copy_into_core(m_ref)
        mine.rho_c[:] = rc
        a = mine.assemble(capacity=True)
        w = np.random.default_rng(6).random(ref.n)
        hs = np.array([0.002, 0.002, 0.004, 0.008, 0.016, 0.032])
        st = fc.Stepper(a["A"], a["M"])
        got = []
        T, _ = fem.march(st, a["M"], a["A"], a["rhs"], hs, np.ones(hs.size, bool), 1.0, lambda k, T: got.append(float(w @ T)))
        # the tool: Euler with the same step sizes (one segment per size)
        res = ref.march(np.zeros(ref.n), [(float(sum(hs[:i])), float(sum(hs[:i + 1])), 1) for i in range(hs.size)], lambda t: 1.0, {"w": w}, rannacher=False, theta=1.0)
        assert np.abs(np.array(got) - res["series"]["w"][1:]).max() < 1e-9 * max(abs(got[-1]), 1e-30)
        # Crank-Nicolson decay from a field, no load
        T0 = np.random.default_rng(7).random(ref.n)
        got2 = []
        fem.march(st, a["M"], a["A"], np.zeros(ref.n), hs, np.ones(hs.size, bool), 0.5, lambda k, T: got2.append(float(w @ T)), start=False, T0=T0)
        res2 = ref.march(T0, [(float(sum(hs[:i])), float(sum(hs[:i + 1])), 1) for i in range(hs.size)], lambda t: 0.0, {"w": w}, rannacher=False, theta=0.5)
        assert np.abs(np.array(got2) - res2["series"]["w"][1:]).max() < 1e-9 * max(abs(got2[0]), 1e-30)


def test_the_cg_path_equals_the_direct_path():
    """!
    @brief The conjugate-gradient time stepping with pyamg reproduces the direct factorisation to 1e-7 of the field scale on a small mesh (skipped without pyamg).
    @return None.
    """
    if not fc.available():
        pytest.skip("pyamg not installed")
    m = fc.structured_model(np.linspace(0, 0.02, 11), np.linspace(0, 0.02, 11), [0, 1e-4, 1.5e-3, 1.6e-3], k=5.0, q=1e6, films={"top": 20.0, "bottom": 20.0})
    m.rho_c[:] = 2e6
    a = m.assemble(capacity=True)
    runs = {}
    for how in ("direct", "cg"):
        st = fc.Stepper(a["A"], a["M"], force=how)
        T, _ = fem.march(st, a["M"], a["A"], a["rhs"], np.array([0.05, 0.05, 0.1, 0.2, 0.4]), np.ones(5, bool), 0.5, lambda k, T: None)
        runs[how] = T
    assert np.abs(runs["cg"] - runs["direct"]).max() < 1e-7 * np.abs(runs["direct"]).max()
