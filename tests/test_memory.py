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


def test_transient_factor_scales_the_solve_not_the_base():
    """!
    @brief A time simulation is estimated at TRANSIENT_FACTOR times the part a steady solve allocates; the resident base of the process is counted once.
    @details Regression of the review: the base was multiplied by the safety and time factors, so a test process holding 1.5 GB saw 4.2 GB of base in a transient.
    @return None.
    """
    s = memory.estimate_bytes("fvm", 500_000, 100_000, BASE)
    t = memory.estimate_bytes("fvm", 500_000, 100_000, BASE, memory.TRANSIENT_FACTOR)
    assert t - BASE == pytest.approx((s - BASE) * memory.TRANSIENT_FACTOR)
    big = memory.estimate_bytes("fvm", 500_000, 100_000, 1.5 * GB, memory.TRANSIENT_FACTOR)
    assert big - t == pytest.approx(1.5 * GB - BASE)


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


def test_ram_is_readable_here(monkeypatch):
    """!
    @brief The machine's memory (read, without the override of the battery) and the available memory are positive numbers.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.delenv(memory.MEMORY_ENV, raising=False)
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
    # Every inverse is kept: the rule is on the sum over the blocks (300 blocks of 2 000 unknowns each fit alone and not together)
    assert memory.sor_block_fits(2000, 9.6e9) and not memory.sor_block_fits([2000] * 300, 9.6e9)
    import numpy as np
    assert memory.sor_block_fits(np.int64(5000), 8e9)


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
    @brief api.simulate refuses a 502 mm board at 0.5 mm (computed h) in seconds and the Python allocations stay below 200 MB (the refusal comes from the bound
           of one node per layer and cell; the exact count of 1 million plan cells took 0.31 GB before the bound; no solver array is made).
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
    assert time.time() - t0 < 60 and peak < 200e6


def test_a_huge_board_is_refused_from_the_lower_bound_without_the_exact_count(monkeypatch):
    """!
    @brief A 0.5 m board at 0.05 mm (100 million plan cells) is refused from the bound of one node per copper layer and cell, without the exact count, whose
           copper sampling alone would take about 30 GB; the cell that fits is found the same way and counted exactly only where the bound fits.
    @param monkeypatch pytest fixture.
    @return None.
    """
    import tracemalloc
    from pcbthermal import fvm
    from pcbthermal.examples import example_profile_board
    p = example_profile_board()
    p.board.width = p.board.height = 0.5025
    counted = []
    real = fvm.unknowns
    monkeypatch.setattr(fvm, "unknowns", lambda prob, c=2.0: (counted.append(c), real(prob, c))[1])
    tracemalloc.start()
    v = memory.check(p, ("fvm",), 0.05, fraction=0.6, ram=int(16 * GB), available=int(16 * GB), refuse="return")[0]
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert v.verdict == "refuse" and "at least" in v.message and v.cell_fit is not None
    assert min(counted) >= 0.5 and peak < 200e6                # Only cells whose bound fits were counted exactly
    fit = memory.check(p, ("fvm",), v.cell_fit, fraction=0.6, ram=int(16 * GB), available=int(16 * GB), refuse="return")[0]
    assert fit.verdict != "refuse"


def test_the_bound_is_never_above_the_exact_count():
    """!
    @brief The lower bound of the unknowns (used to refuse without counting) is at most the exact count on boards with laminate nodes, an outline, a block and one layer.
    @return None.
    """
    from pcbthermal.examples import example_board, example_profile_board
    from pcbthermal.model import reference_problem
    for p in (reference_problem(layers=1), reference_problem(layers=4), example_board(), example_profile_board()):
        for model in ("fvm", "fdm", "solid3d"):
            for c in (2.0, 0.7):
                assert memory._bound(p, model)(c)[0] <= memory._counter(p, model)(c)[0]


def test_size_limit_is_a_window_refused_above_it():
    """!
    @brief solid3d.size_limit(n) keeps its meaning of before the guard: accepted up to n whatever the memory, refused above n (study_validation_rows uses 250 000).
    @return None.
    """
    p = reference_problem(layers=4)
    n = solid3d.unknowns(p, 1.0)[0]
    with solid3d.size_limit(n - 1):
        with pytest.raises(memory.MemoryGuardError, match="accepted by this study"):
            memory.check(p, ("solid3d",), 1.0, fraction=0.95, ram=int(1000 * GB))
        v = memory.check(p, ("solid3d",), 1.0, fraction=0.95, ram=int(1000 * GB), refuse="return")[0]
        assert v.cell_fit is not None and solid3d.unknowns(p, v.cell_fit)[0] <= n - 1


def test_solid_built_directly_is_guarded(monkeypatch):
    """!
    @brief The 3D solid built directly (studies, tests) is checked by its constructor, as it was by check_size before the guard; a ValueError, so the studies that
           print "-" for a model too large keep working.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(memory, "ram_bytes", lambda: 2 * 10 ** 8)
    with pytest.raises(ValueError, match="memory|no cell"):
        solid3d.Solid(reference_problem(), 2.0)
    with solid3d.size_limit(10 ** 6):
        assert solid3d.Solid(reference_problem(), 4.0).n > 0


def test_a_profile_run_too_large_leaves_the_steady_results(monkeypatch):
    """!
    @brief With a power profile the time simulation (about twice a steady solve) is checked too: on a machine where the steady FVM fits and the profile run does not,
           the steady result is there and profile_error says why the time simulation was not run.
    @param monkeypatch pytest fixture.
    @return None.
    """
    from pcbthermal import SolverOptions, simulate
    from pcbthermal.examples import example_profile_board
    p = example_profile_board()
    steady = memory.check(p, ("fvm",), 1.0, refuse="return", ram=int(16 * GB), available=int(16 * GB))[0].estimate
    timed = memory.check(p, ("fvm",), 1.0, factor=memory.PROFILE_FACTOR, refuse="return", ram=int(16 * GB), available=int(16 * GB))[0].estimate
    ram = int((steady + timed) / 2 / 0.6)                       # Between the two estimates at a fraction of 0.6
    monkeypatch.setattr(memory, "ram_bytes", lambda: ram)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0, memory_fraction=0.6))
    assert "fvm" in sim.results and not sim.profile_results
    assert sim.profile_error and sim.profile_error.startswith("time simulation not run")


def test_the_memory_of_the_machine_can_be_stated(monkeypatch):
    """!
    @brief The environment variable MEMORY_ENV replaces the reading (the battery sets 16 GB in conftest); a bad value falls back to the reading.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setenv(memory.MEMORY_ENV, "8e9")
    assert memory.ram_bytes() == 8 * 10 ** 9
    monkeypatch.setenv(memory.MEMORY_ENV, "lots")
    assert memory.ram_bytes() > 1e9


def test_options_validate_the_fraction():
    """!
    @brief memory_fraction outside 0.1 to 0.95 is rejected; the field is a machine preference and is not saved with the options.
    @return None.
    """
    from pcbthermal import SolverOptions
    with pytest.raises(ValueError):
        SolverOptions(memory_fraction=0.99).validate()
    d = SolverOptions(memory_fraction=0.5).to_dict()
    assert "memory_fraction" not in d
    assert SolverOptions.from_dict(d).memory_fraction == memory.default_fraction()


def test_an_old_project_with_the_key_loads_and_ignores_it():
    """!
    @brief A project file saved before the field became a preference still loads, and its value does not reach the options.
    @return None.
    """
    from pcbthermal import SolverOptions
    o = SolverOptions.from_dict({"cell_mm": 2.0, "memory_fraction": 0.2})
    assert o.cell_mm == 2.0 and o.memory_fraction == memory.default_fraction() != 0.2


def test_the_fraction_comes_from_the_preferences(monkeypatch):
    """!
    @brief The default fraction is solver.memory_fraction of the defaults (the user's file), 0.60 shipped; a bad value falls back; the command-line override wins.
    @param monkeypatch pytest fixture.
    @return None.
    """
    from pcbthermal import SolverOptions, defaults
    assert defaults.shipped()["solver"]["memory_fraction"] == 0.6
    assert memory.default_fraction() == 0.6
    monkeypatch.setattr(defaults, "load", lambda: {"solver": {"memory_fraction": 0.3}})
    assert memory.default_fraction() == 0.3 and SolverOptions().memory_fraction == 0.3
    monkeypatch.setattr(defaults, "load", lambda: {"solver": {"memory_fraction": 7.0}})
    assert memory.default_fraction() == memory.DEFAULT_FRACTION
    memory.set_default_fraction(0.2)
    try:
        assert memory.default_fraction() == 0.2
    finally:
        memory.set_default_fraction(None)


@pytest.fixture
def cli_board(tmp_path):
    """!
    @brief The example board written to a project file for the command-line tests.
    @param tmp_path pytest temporary folder.
    @return Path of the project file as a string.
    """
    from pcbthermal import cli
    path = tmp_path / "board.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    return str(path)


@pytest.mark.parametrize("command", [["run", "--model", "fvm", "--cell-mm", "0.05"], ["transient", "--cell-mm", "0.05"], ["solvers", "--cell-mm", "0.05"],
                                      ["convergence"]])
def test_the_commands_exit_with_code_3_on_a_refusal(command, cli_board, tmp_path, monkeypatch, capsys):
    """!
    @brief run, transient, solvers and convergence refuse an over-large model before solving: exit code 3 (memory.EXIT_CODE), the message on stderr, nothing written.
    @param command Command and its arguments (without the file).
    @param cli_board Project file.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @param capsys pytest fixture.
    @return None.
    """
    from pcbthermal import cli
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(1.0 * GB))      # A 1 GB machine at the default fraction: every cell of these commands is refused
    out = tmp_path / "o"
    code = cli.main([command[0], cli_board, *command[1:], "--out", str(out), "--no-plots"])
    assert code == memory.EXIT_CODE == 3
    err = capsys.readouterr().err
    assert "error:" in err and "GB" in err
    assert not out.exists()
    assert memory.default_fraction() == memory.DEFAULT_FRACTION       # The override of the command is gone


def test_memory_fraction_option_sets_the_limit(cli_board, tmp_path, monkeypatch, capsys):
    """!
    @brief --memory-fraction replaces the preference for the command: a run that fits at 0.6 is refused at 0.1 on a small machine, and a value out of range is a usage error.
    @param cli_board Project file.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @param capsys pytest fixture.
    @return None.
    """
    from pcbthermal import cli
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(1.0 * GB))
    args = ["run", cli_board, "--model", "fvm", "--cell-mm", "2", "--out", str(tmp_path / "o"), "--no-plots"]
    assert cli.main(args) == 0
    assert cli.main(args + ["--memory-fraction", "0.12"]) == memory.EXIT_CODE
    assert cli.main(args + ["--memory-fraction", "2"]) == 2
    capsys.readouterr()
