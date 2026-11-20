#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_transient_memory.py
@brief The memory and time guard of the FEM time simulation: the factor per model and per solver path, the frames added in bytes, the law against the recorded transient peaks of
       the design review, the refusal BEFORE the run (never a crash), the time prediction and its limit.
@details The two recorded peaks are those of DESIGN.md 14.3 (the example board at 2 mm, 67 229 unknowns, one run per case in a fresh process on a loaded machine): the constants
         shipped now (2.0) must cover them; the measurement that refits them is `releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py`, which is NOT run here.
"""

import numpy as np
import pytest

from pcbthermal import femcore, fem, femmesh, memory
from pcbthermal.model import Problem

# (path, unknowns, growth in bytes) of the review's prototype (DESIGN.md 14.3)
RECORDED = [("cg", 67229, 478_500_000), ("direct", 67229, 1_845_000_000)]


def _board(width=60.0, height=40.0, layers=2):
    """!
    @brief A full-copper board with a part, in mm.
    @param width Board width in mm.
    @param height Board height in mm.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(width, height, layers=layers)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(width / 2 - 2, height / 2 - 2, width / 2 + 2, height / 2 + 2))
    return p


def test_the_factor_is_per_model_and_per_path_and_does_not_touch_the_others():
    """!
    @brief The FEM transient factor depends on the solver path (direct up to the transient direct limit, CG above); the FVM and FDM keep `TRANSIENT_FACTOR` and
           `PROFILE_FACTOR`; a steady FEM check has factor 1.
    @return None.
    """
    assert memory.fem_transient_factor(femcore.FEM_TRANSIENT_DIRECT_MAX) == memory.FEM_TRANSIENT_FACTOR_DIRECT
    assert memory.fem_transient_factor(femcore.FEM_TRANSIENT_DIRECT_MAX + 1) == memory.FEM_TRANSIENT_FACTOR_CG
    p = _board()
    kw = dict(refuse="return", ram=64 * 10 ** 9, available=64 * 10 ** 9, base=0.1e9, quiet=True)
    steady = memory.check(p, ("fem",), 2.0, **kw)[0].estimate
    trans = memory.check(p, ("fem",), 2.0, transient=True, **kw)[0].estimate
    n = femmesh.unknowns(p, 2.0)[0]
    grown = steady - 0.1e9
    assert trans - 0.1e9 == pytest.approx(grown * memory.fem_transient_factor(n), rel=1e-9)
    prof = memory.check(p, ("fem",), 2.0, factor=memory.PROFILE_FACTOR, **kw)[0].estimate
    assert prof == pytest.approx(trans, rel=1e-12)                      # the FEM has one factor for a time run, whatever the caller passes
    fvm_t = memory.check(p, ("fvm",), 2.0, transient=True, **kw)[0].estimate
    fvm_s = memory.check(p, ("fvm",), 2.0, **kw)[0].estimate
    assert (fvm_t - 0.1e9) == pytest.approx((fvm_s - 0.1e9) * memory.TRANSIENT_FACTOR, rel=1e-6)


def test_the_frames_are_added_in_bytes_not_multiplied():
    """!
    @brief `frames_bytes` is added to the FEM estimate once, whatever the time factor.
    @return None.
    """
    p = _board()
    kw = dict(refuse="return", ram=64 * 10 ** 9, available=64 * 10 ** 9, base=0.1e9, quiet=True, transient=True)
    a = memory.check(p, ("fem",), 2.0, **kw)[0].estimate
    b = memory.check(p, ("fem",), 2.0, frames_bytes=5e8, **kw)[0].estimate
    assert b - a == pytest.approx(5e8, rel=1e-9)


@pytest.mark.parametrize("path,n,growth", RECORDED)
def test_the_shipped_factor_covers_the_recorded_transient_peaks(path, n, growth):
    """!
    @brief The estimate of the transient (without the base) is at least the recorded growth of the review's prototype on both paths at the recorded size, the way the
           constants are meant to be refitted: largest measured ratio times 1.1, never below.
    @param path "cg" or "direct".
    @param n Unknowns of the recorded run.
    @param growth Recorded growth in bytes.
    @return None.
    """
    mult = memory.FEM_TRANSIENT_FACTOR_CG if path == "cg" else memory.FEM_TRANSIENT_FACTOR_DIRECT
    if path == "cg":
        est = memory.estimate_bytes("fem", n, n / 10.0, base=0.0, factor=mult)
    else:
        est = memory.FEM_DIRECT_BYTES * n * mult                        # the steady direct law applied above its fitted range, as the guard would until refitted
    assert est >= growth


def test_the_refusal_comes_before_any_build_and_is_a_guard_error(monkeypatch):
    """!
    @brief `fem.solve_transient` on a machine too small for the mesh raises MemoryGuardError and builds no mesh (femmesh.build is never called).
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _board()
    called = []
    monkeypatch.setattr(femmesh, "build", lambda *a, **k: called.append(1))
    with pytest.raises(memory.MemoryGuardError):
        fem.solve_transient(p, 100.0, n_out=10, cell_mm=1.0, memory_fraction=memory.MIN_FRACTION * 1e-6)
    assert not called


def test_without_pyamg_a_mesh_above_the_direct_limit_is_refused_with_the_reason(monkeypatch):
    """!
    @brief Above `FEM_TRANSIENT_DIRECT_MAX` unknowns and without pyamg the run raises FemUnavailable naming the limit, before any build.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _board()
    monkeypatch.setattr(femcore, "available", lambda: False)
    monkeypatch.setattr(femcore, "FEM_TRANSIENT_DIRECT_MAX", 100)
    monkeypatch.setattr(memory, "check", lambda *a, **k: [])
    with pytest.raises(femcore.FemUnavailable, match="pyamg"):
        fem.solve_transient(p, 100.0, n_out=10, cell_mm=4.0)


def test_the_time_prediction_grows_with_unknowns_and_steps_and_the_cg_path_costs_more():
    """!
    @brief `fem_transient_seconds` is linear in the steps and the unknowns, and a step on the CG path costs more than a back substitution.
    @return None.
    """
    s = memory.fem_transient_seconds
    assert s(20_000, 2000) == pytest.approx(2 * s(20_000, 1000)) and s(40_000, 1000) > s(20_000, 1000)
    assert s(100_000, 1000) / 100_000 > s(20_000, 1000) / 20_000


def test_the_transient_direct_limit_does_not_outrun_the_direct_memory_law():
    """!
    @brief `femcore.FEM_TRANSIENT_DIRECT_MAX` stays at or below `femcore.FEM_DIRECT_MAX` while `memory.estimate_bytes` has a direct law only below the steady limit: a time run on the
           direct path above it would be estimated with the conjugate-gradient law (6.7 kB per unknown against 24 kB measured for a direct factor at 67 229 unknowns, DESIGN.md 14.3).
           Raising the transient limit (after `measure_fem_transient_direct_limit.py`) must come with a direct law above 30 000 unknowns in `estimate_bytes`, and this test changes then.
    @return None.
    """
    assert femcore.FEM_TRANSIENT_DIRECT_MAX <= femcore.FEM_DIRECT_MAX
    n = femcore.FEM_TRANSIENT_DIRECT_MAX
    assert memory.estimate_bytes("fem", n, n / 10.0, base=0.0) == pytest.approx(memory.FEM_DIRECT_BYTES * n)
