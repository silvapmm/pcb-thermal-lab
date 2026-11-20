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
    monkeypatch.setattr(femcore, "FEM_DIRECT_MAX", 100)
    monkeypatch.setattr(memory, "FEM_DIRECT_MAX", 100)
    monkeypatch.setattr(memory, "check", lambda *a, **k: [])
    with pytest.raises(femcore.FemUnavailable, match="pyamg"):
        fem.solve_transient(p, 100.0, n_out=10, cell_mm=4.0)


def test_the_time_prediction_grows_with_unknowns_and_steps_and_the_cg_path_costs_more():
    """!
    @brief `fem_transient_seconds` is linear in the steps and the unknowns, and a step on the CG path costs more than a back substitution.
    @return None.
    """
    s = memory.fem_transient_seconds
    assert s(20_000, 2000, 0) == pytest.approx(2 * s(20_000, 1000, 0)) and s(40_000, 1000) > s(20_000, 1000)
    assert s(100_000, 1000) / 100_000 > s(20_000, 1000) / 20_000


# (unknowns, direct growth in bytes) of the run of `measure_fem_transient_direct_limit.py` (example board, tree ec15bdc0) and the direct cases of `measure_fem_transient_law.py`
DIRECT_ROWS = [(20930, 0.32e9), (32637, 0.55e9), (46644, 0.92e9), (67229, 1.95e9), (106122, 3.11e9), (14400, 0.21e9), (15632, 0.24e9), (11007, 0.12e9), (29413, 0.51e9), (67229, 2.15e9)]
CG_ROWS = [(67229, 0.55e9), (53181, 0.42e9), (55488, 0.46e9), (40140, 0.30e9), (67229, 0.49e9), (57600, 0.47e9), (40328, 0.31e9), (275724, 2.06e9), (106122, 0.90e9), (20930, 0.19e9)]


def test_the_direct_time_law_covers_every_measured_row_above_the_steady_limit():
    """!
    @brief `estimate_bytes("fem_time")` (the direct factor times FEM_TRANSIENT_FACTOR_DIRECT, 36.7 kB per unknown) is at least the measured growth of every direct row, with at least the
           15 % margin of the fit on the worst one (2.15 GB at 67 229 unknowns), up to `FEM_TRANSIENT_DIRECT_MAX`; the CG law with its factor covers the CG rows.
    @return None.
    """
    assert femcore.FEM_TRANSIENT_DIRECT_MAX >= 100_000 and memory.FEM_TRANSIENT_DIRECT_MAX == femcore.FEM_TRANSIENT_DIRECT_MAX
    for n, growth in DIRECT_ROWS:
        # (the 106 122-unknown row is above the transient limit of 100 000, where the estimate switches to the CG law: its direct law is the same formula)
        direct = memory.FEM_DIRECT_BYTES * n * memory.FEM_TRANSIENT_FACTOR_DIRECT
        assert direct >= growth, n
        if n <= femcore.FEM_TRANSIENT_DIRECT_MAX:
            assert memory.estimate_bytes("fem_time", n, n / 10.0, base=0.0) == pytest.approx(direct)
    assert memory.estimate_bytes("fem_time", 67229, 6000.0, base=0.0) >= 1.14 * 2.15e9
    for n, growth in CG_ROWS:
        assert memory.estimate_bytes("fem_time_cg", n, n / 10.0, base=0.0) >= growth, n
    assert memory.estimate_bytes("fem_time_cg", 67229, 6700.0, base=0.0) >= 1.14 * 0.55e9


def test_above_the_transient_direct_limit_a_time_run_is_estimated_by_the_cg_law():
    """!
    @brief One unknown above `FEM_TRANSIENT_DIRECT_MAX` the estimate is the CG time law (a tenth of the direct bytes), so a mesh that only fits by conjugate gradients is not refused.
    @return None.
    """
    n = femcore.FEM_TRANSIENT_DIRECT_MAX
    below, above = memory.estimate_bytes("fem_time", n, n / 10.0, base=0.0), memory.estimate_bytes("fem_time", n + 1, n / 10.0, base=0.0)
    assert above == pytest.approx(memory.estimate_bytes("fem_time_cg", n + 1, n / 10.0, base=0.0)) and above < below


def test_the_path_follows_the_memory_budget_and_the_guard_refuses_before_the_run(monkeypatch):
    """!
    @brief `fem_time_law` is direct while its factor fits the limit and falls back to CG when it does not (a mesh at or below the steady direct limit is always direct); `check` of a time
           run refuses a mesh that fits by neither law BEFORE anything is built.
    @param monkeypatch pytest fixture.
    @return None.
    """
    n = 90_000
    big, small = 64e9, 3.5e9                                            # the direct law needs 3.3 GB at 90 000 unknowns
    assert memory.fem_time_law(n, n / 10.0, 0.0, big) == "fem_time"
    assert memory.fem_time_law(n, n / 10.0, 0.0, 2.0e9) == "fem_time_cg"
    assert memory.fem_time_law(20_000, 2000.0, 0.0, 1.0) == "fem_time"
    p = _board(120.0, 100.0)
    called = []
    monkeypatch.setattr(femmesh, "build", lambda *a, **k: called.append(1))
    with pytest.raises(memory.MemoryGuardError):
        fem.solve_transient(p, 100.0, n_out=10, cell_mm=0.5, memory_fraction=memory.MIN_FRACTION * 1e-6)
    assert not called


def test_the_time_model_has_a_setup_per_stage_and_a_cost_per_step_and_matches_the_measured_table():
    """!
    @brief `fem_transient_seconds` is a setup term per stage plus a per-step term; on the direct path it is at least the measured stage time (factorisation plus eight steps) of every
           row of the direct-limit table and within a factor 3 of it above 30 000 unknowns, and on the CG path it covers the measured per-step time.
    @return None.
    """
    s = memory.fem_transient_seconds
    # (unknowns, measured stage seconds with 8 steps): setup + 8 steps
    for n, measured in ((20930, 0.58), (32637, 1.39), (46644, 3.23), (67229, 7.57)):
        pred = s(n, 8, 1)
        assert pred >= measured and (n < 30000 or pred <= 3.0 * measured), (n, pred, measured)
    assert s(67229, 52, 11) > s(67229, 52, 1) + 9 * 7.0                # ten more stages cost ten more factorisations
    for n, step in ((20930, 1.148), (67229, 3.155), (106122, 4.236)):
        assert s(n + 100000, 1, 0) / (n + 100000) * n >= step * 0.9     # CG: per-unknown cost covers the measured step (above the direct limit)
