#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_memory.py
@brief Tests of the memory guard (`pcbthermal/memory.py`): the estimate law, the verdict, fake machines of 8, 16 and 64 GB, the fallback and the refusal text.
"""

import pytest

from pcbthermal import memory, solid3d
from pcbthermal.model import reference_problem

GB = 1.0e9
BASE = 0.108e9


@pytest.fixture(autouse=True)
def fixed_base(monkeypatch):
    """!
    @brief Fix the resident size of the process to the measured base so the estimates do not depend on what pytest has loaded.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(memory, "resident_bytes", lambda: BASE)


def test_estimate_matches_measured_points_of_the_ladder():
    """!
    @brief The estimate is at or above the measured peaks of the review (safety factor included) and grows faster than linearly.
    @details The pairs are (model, unknowns, plan cells, measured peak in GB) of research/memory-guard README 5 and the documents' 3D solid points.
    @return None.
    """
    points = [("solid3d", 392_000, 24_500, 7.4), ("solid3d", 512_000, 32_000, 9.9), ("solid3d", 500_000, 83_333, 3.3),
              ("fvm", 992_000, 248_000, 2.7), ("fvm", 1_975_000, 494_000, 5.5), ("solid3d", 247_000, 15_437, 3.5)]
    for model, n, cells, peak in points:
        assert memory.estimate_bytes(model, n, cells, BASE) / GB >= peak, (model, n)
    assert memory.estimate_bytes("fvm", 2_000_000, 500_000, BASE) > 2.0 * memory.estimate_bytes("fvm", 1_000_000, 250_000, BASE) * 0.99


def test_transient_factor_scales_the_peak():
    """!
    @brief A time simulation is estimated at TRANSIENT_FACTOR times a steady solve.
    @return None.
    """
    s = memory.estimate_bytes("fvm", 500_000, 100_000, BASE)
    assert memory.estimate_bytes("fvm", 500_000, 100_000, BASE, memory.TRANSIENT_FACTOR) == pytest.approx(s * memory.TRANSIENT_FACTOR)


def test_verdict_rules():
    """!
    @brief Refuse above the limit, slow above the predicted time, ok otherwise.
    @return None.
    """
    assert memory.verdict(9 * GB, 8 * GB) == "refuse"
    assert memory.verdict(1 * GB, 8 * GB, seconds=60.0) == "slow"
    assert memory.verdict(1 * GB, 8 * GB, seconds=5.0) == "ok"


def test_limit_uses_the_fraction_and_the_fallback():
    """!
    @brief The limit is fraction x RAM; an unreadable RAM gives the fixed fallback.
    @param monkeypatch pytest fixture (not used).
    @return None.
    """
    assert memory.limit_bytes(0.6, ram=16_000_000_000) == pytest.approx(9.6 * GB)
    assert memory.limit_bytes(0.6, ram=None) in (memory.FALLBACK_LIMIT, memory.limit_bytes(0.6, ram=memory.ram_bytes()))


def test_failed_ram_read_falls_back(monkeypatch):
    """!
    @brief With the RAM read failing the fixed limit is used.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(memory, "ram_bytes", lambda: None)
    assert memory.limit_bytes() == memory.FALLBACK_LIMIT


def test_ram_is_readable_here():
    """!
    @brief The machine's memory and the available memory are positive numbers.
    @return None.
    """
    assert memory.ram_bytes() > 1e9
    assert memory.available_bytes() is None or memory.available_bytes() > 0


def test_sor_block_rule():
    """!
    @brief 75 n^2 bytes, allowed within 25 % of the limit: 5 000 unknowns are 1.9 GB, not 200 MB.
    @return None.
    """
    assert memory.sor_block_bytes(5000) == pytest.approx(1.875e9)
    assert memory.sor_block_fits(5000, 8e9)           # 1.875 <= 2.0
    assert not memory.sor_block_fits(5000, 6e9)
    assert not memory.sor_block_fits(10_000, 16e9)


def test_largest_unknowns_is_the_inverse_of_the_estimate():
    """!
    @brief The unknown count returned fits the limit and one more percent does not.
    @return None.
    """
    cells = 100_000
    n = memory.largest_unknowns("fvm", cells, 8 * GB, BASE)
    assert memory.estimate_bytes("fvm", n, cells, BASE) <= 8 * GB
    assert memory.estimate_bytes("fvm", n * 1.01, cells, BASE) > 8 * GB


@pytest.mark.parametrize("model, ram_gb, expected", [("fvm", 8, "refuse"), ("fvm", 16, "ok"), ("fvm", 64, "ok"), ("fdm", 8, "refuse"), ("fdm", 16, "slow"), ("fdm", 64, "slow")])
def test_fake_machines_give_ok_slow_refuse(model, ram_gb, expected):
    """!
    @brief The same 4-layer reference board at a 0.2 mm cell (about 1 million unknowns, an estimated 7.4 GB for the FVM and 8.2 GB for the FDM) on fake machines.
    @details The FVM is refused on 8 GB (limit 4.8 GB) and fits on 16 GB (9.6 GB); the FDM fits on 16 GB but its predicted solve time is above 30 s, so it is "slow" there.
    @param model "fvm" or "fdm".
    @param ram_gb Fake physical memory in GB.
    @param expected Expected verdict.
    @return None.
    """
    p = reference_problem(layers=4)
    v = memory.check(p, (model,), 0.2, fraction=0.6, ram=int(ram_gb * GB), available=int(ram_gb * GB), refuse="return")[0]
    assert v.verdict == expected
    if expected == "refuse":
        assert v.cell_fit is not None and v.cell_fit > 0.2 and f"{v.cell_fit:.1f} mm" in v.message
    else:
        assert v.cell_fit is None


def test_check_raises_a_guard_error_with_the_cell_that_fits():
    """!
    @brief A refusal raises MemoryGuardError (a ValueError) and the message names a cell that really fits.
    @return None.
    """
    p = reference_problem(layers=4)
    with pytest.raises(memory.MemoryGuardError) as exc:
        memory.check(p, ("fvm",), 0.2, fraction=0.5, ram=int(4 * GB), available=int(4 * GB))
    assert isinstance(exc.value, ValueError)
    assert "use a cell of" in str(exc.value)
    fit = float(str(exc.value).split("use a cell of ")[1].split(" mm")[0])
    ok = memory.check(p, ("fvm",), fit, fraction=0.5, ram=int(4 * GB), available=int(4 * GB), refuse="return")[0]
    assert ok.verdict != "refuse"


def test_lumped_and_analytic_are_not_checked():
    """!
    @brief The models without a law give no verdict.
    @return None.
    """
    assert memory.check(reference_problem(), ("lumped", "analytic"), 0.5) == []


def test_size_limit_accepts_a_3d_model_whatever_the_memory():
    """!
    @brief Inside solid3d.size_limit a model up to the given unknown count is not refused, and the ceiling is lifted to it.
    @return None.
    """
    p = reference_problem(layers=4)
    n = solid3d.unknowns(p, 0.5)[0]
    with pytest.raises(memory.MemoryGuardError):
        memory.check(p, ("solid3d",), 0.5, fraction=0.1, ram=int(4 * GB))
    with solid3d.size_limit(n + 1):
        res = memory.check(p, ("solid3d",), 0.5, fraction=0.1, ram=int(4 * GB))
        assert res[0].verdict != "refuse"
    with pytest.raises(memory.MemoryGuardError):
        memory.check(p, ("solid3d",), 0.5, fraction=0.1, ram=int(4 * GB))


def test_the_3d_ceiling_refuses_whatever_the_memory():
    """!
    @brief Above CEILING_3D unknowns the 3D solid is refused even with a huge machine, and the message gives a cell under the ceiling.
    @return None.
    """
    p = reference_problem(layers=4)
    with pytest.raises(memory.MemoryGuardError) as exc:
        memory.check(p, ("solid3d",), 0.1, fraction=0.95, ram=int(10_000 * GB), available=int(10_000 * GB))
    assert "no machine" in str(exc.value) and "use a cell of" in str(exc.value)


def test_simulate_refuses_a_huge_model_fast_and_allocates_nothing_large(monkeypatch):
    """!
    @brief api.simulate refuses a 502 mm board at 0.5 mm (computed h) in seconds and the Python allocations stay below 500 MB (counting the unknowns of 1 million plan cells itself takes 0.31 GB; no solver array is made).
    @param monkeypatch pytest fixture.
    @return None.
    """
    import time
    import tracemalloc
    from pcbthermal import SolverOptions, simulate
    from pcbthermal.examples import example_profile_board
    monkeypatch.setattr(memory, "ram_bytes", lambda: 16 * 10 ** 9)
    p = example_profile_board()
    p.board.width = p.board.height = 0.5025
    p.board.h_mode = "computed"
    tracemalloc.start()
    t0 = time.time()
    with pytest.raises(memory.MemoryGuardError, match=r"use a cell of \d"):
        simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5))
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert time.time() - t0 < 60 and peak < 500e6


def test_options_validate_the_fraction():
    """!
    @brief memory_fraction outside 0.1 to 0.95 is rejected and the field is saved with the options.
    @return None.
    """
    from pcbthermal import SolverOptions
    with pytest.raises(ValueError):
        SolverOptions(memory_fraction=0.99).validate()
    assert SolverOptions.from_dict(SolverOptions(memory_fraction=0.5).to_dict()).memory_fraction == 0.5
