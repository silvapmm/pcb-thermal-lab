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
    memory.reset_baseline()                      # The baseline of an earlier test must not hide the fake size
    yield
    memory.reset_baseline()


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


def test_preferences_field_sets_the_machine_limit(qtbot, tmp_path, monkeypatch):
    """!
    @brief The Preferences field "memory limit" has a tooltip with the detected memory and a range of 0.10 to 0.95; saving it changes memory.default_fraction() and new options.
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))
    from pcbthermal import SolverOptions
    from pcbthermal.gui.preferences import PreferencesDialog
    d = PreferencesDialog()
    qtbot.addWidget(d)
    w = d.widgets[("solver", "memory_fraction")]
    assert (w.minimum(), w.maximum()) == (memory.MIN_FRACTION, memory.MAX_FRACTION) and w.value() == 0.6
    assert "Memory detected" in w.toolTip() and "not saved in project files" in w.toolTip()
    w.setValue(0.4)
    d.save()
    assert memory.default_fraction() == 0.4 and SolverOptions().memory_fraction == 0.4


def test_the_estimate_and_the_measured_peak_are_logged_once_per_run(caplog):
    """!
    @brief A steady run logs the estimate of each checked model and, once at the end, the measured peak next to the largest estimate.
    @param caplog pytest fixture.
    @return None.
    """
    import logging
    from pcbthermal import SolverOptions, simulate
    with caplog.at_level(logging.INFO, logger=memory.log.name):
        simulate(reference_problem(), SolverOptions(models=("fvm",), cell_mm=5.0))
    texts = [r.getMessage() for r in caplog.records]
    assert sum("estimate" in t and "limit" in t for t in texts) == 1
    assert sum("measured peak" in t for t in texts) == 1


@pytest.fixture
def cli_small_part(tmp_path):
    """!
    @brief A 200 x 200 mm board with one 2 mm part: the cell from the part (0.5 mm) is far above the memory of a 1 GB machine, so "auto" must enlarge it.
    @param tmp_path pytest temporary folder.
    @return Path of the project file as a string.
    """
    import json
    from pcbthermal.model import Problem, problem_to_dict
    p = Problem.new(200, 200, layers=2)
    p.add_heater(1, 2.0, rect=(99, 99, 101, 101))
    path = tmp_path / "small_part.pcbt.json"
    path.write_text(json.dumps(problem_to_dict(p)))
    return str(path)


@pytest.mark.parametrize("model", ["fvm", "all", "compare"])
def test_auto_cell_of_the_command_line_fits_every_model_choice(model, cli_small_part, tmp_path, monkeypatch, capsys):
    """!
    @brief Regression: `run --cell-mm auto` with the default `--model all` (and `compare`) passed the word "all" to the guard, which skipped it, so the cell from
           the part was used and the run was refused with exit code 3; the models of the choice are now expanded and the run passes.
    @param model Value of --model.
    @param cli_small_part Project file.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @param capsys pytest fixture.
    @return None.
    """
    from pcbthermal import cli
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(1.0 * GB))
    code = cli.main(["run", cli_small_part, "--model", model, "--cell-mm", "auto", "--out", str(tmp_path / "o"), "--no-plots"])
    assert code == 0, capsys.readouterr().err
    capsys.readouterr()


def test_auto_cell_of_the_transient_command_fits_the_time_factor(cli_small_part, tmp_path, monkeypatch, capsys):
    """!
    @brief Regression: `transient --cell-mm auto` chose a cell that fits a steady solve and was then refused by the guard of the time simulation (twice the
           memory); the automatic cell now fits the factor of a time simulation.
    @param cli_small_part Project file.
    @param tmp_path pytest temporary folder.
    @param monkeypatch pytest fixture.
    @param capsys pytest fixture.
    @return None.
    """
    from pcbthermal import cli
    from pcbthermal.api import suggest_cell_mm
    from pcbthermal.model import load_problem
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(1.0 * GB))
    p = load_problem(cli_small_part)
    assert suggest_cell_mm(p, models=("fvm",), transient=True) > suggest_cell_mm(p, models=("fvm",))
    code = cli.main(["transient", cli_small_part, "--cell-mm", "auto", "--t-end", "1", "--steps", "2", "--out", str(tmp_path / "o"), "--no-plots"])
    assert code == 0, capsys.readouterr().err
    capsys.readouterr()


def test_messages_and_panel_counts_have_no_thousands_separator():
    """!
    @brief The counts in the refusal text follow the rule of every number shown by the program: no thousands separator.
    @return None.
    """
    v = memory.check(reference_problem(layers=4), ("fvm",), 0.1, ram=int(1.0 * GB), available=int(1.0 * GB), refuse="return")[0]
    assert v.verdict == "refuse" and f"{v.unknowns} unknowns" in v.message and "," not in v.message.split(" GB")[0]


def test_a_check_that_is_not_a_run_writes_no_log_line(caplog):
    """!
    @brief The solver panel and the Auto cell ask the guard at every edit (quiet): only the runs write their estimate to the log.
    @param caplog pytest fixture.
    @return None.
    """
    import logging
    with caplog.at_level(logging.INFO, logger=memory.log.name):
        memory.check(reference_problem(), ("fvm",), 2.0, refuse="return", quiet=True)
        assert not caplog.records
        memory.check(reference_problem(), ("fvm",), 2.0, refuse="return")
        assert len(caplog.records) == 1


# ---------------------------------------------------------------------------------------------------- the via term
def test_no_via_estimates_are_unchanged():
    """!
    @brief Without vias (zero footprint cells) the estimate is the law of memory.CONTINUOUS exactly, for every model, and the 3D solid ignores the term.
    @return None.
    """
    for model, (k1, p, a, safety) in memory.CONTINUOUS.items():
        n, cells = 400_000, 50_000
        t_eff = max(min(n / cells, cells / (n / cells)), 1.0)
        law = BASE + k1 * t_eff ** a * n * (n / memory.N_REF) ** (p - 1.0) * safety
        assert memory.estimate_bytes(model, n, cells, BASE) == law
        assert memory.estimate_bytes(model, n, cells, BASE, 1.0, 0.0) == law
    assert memory.estimate_bytes("solid3d", 400_000, 50_000, BASE, 1.0, 5000.0) == memory.estimate_bytes("solid3d", 400_000, 50_000, BASE)


def test_via_gain_is_continuous_monotone_and_bounded():
    """!
    @brief The via factor starts at 1, grows with the footprint cells and never passes 1 + VIA_GAIN.
    @return None.
    """
    assert memory.via_gain("fvm", 0.0) == 1.0
    assert memory.via_gain("fvm", 1.0) == pytest.approx(1.0, abs=1e-3)           # one via is not a step
    f = [memory.via_gain("fdm", x) for x in (10, 100, 1000, 10_000, 1e7)]
    assert f == sorted(f) and f[-1] <= 1.0 + memory.VIA_GAIN + 1e-12 and f[-1] > 1.0 + 0.99 * memory.VIA_GAIN
    assert memory.via_gain("solid3d", 1e6) == 1.0


def test_via_cells_counts_the_footprints_of_the_vias_on_the_board():
    """!
    @brief The footprint cells are zero without vias, grow with the number of vias and with a finer cell, and leave out a via outside the board box.
    @return None.
    """
    from pcbthermal.model import Problem
    p = Problem.new(60, 60, layers=2)
    p.add_full_copper()
    assert memory.via_cells(p, 1.0) == 0.0
    p.add_via_array((10, 10, 40, 40), 5, 5, diameter=0.3)
    c1 = memory.via_cells(p, 1.0)
    assert 25 <= c1 <= 25 * 5
    assert memory.via_cells(p, 0.5) > c1                                           # a finer cell spreads the same drill over more cells
    p.add_via(100.0, 100.0, diameter=0.3)                                         # outside the 60 mm board
    assert memory.via_cells(p, 1.0) == c1
    q = Problem.new(60, 60, layers=2)
    q.add_via_array((10, 10, 40, 40), 10, 10, diameter=0.3)
    assert memory.via_cells(q, 1.0) == pytest.approx(4.0 * c1, rel=0.3)


def test_via_footprint_cells_agree_with_the_network():
    """!
    @brief The cheap count of the footprints is within 25 % of the cells the network builds for them (sum over the vias).
    @return None.
    """
    import numpy as np
    from pcbthermal import fvm
    from pcbthermal.model import Problem
    p = Problem.new(40, 40, layers=2)
    p.add_full_copper()
    # Scattered positions (a regular array on cell centres is the lucky case where every footprint is one cell; real boards are not on the grid)
    rng = np.random.default_rng(7)
    for x, y in rng.uniform(5.0, 35.0, size=(150, 2)):
        p.add_via(float(x), float(y), diameter=0.3)
    for x, y in rng.uniform(5.0, 35.0, size=(30, 2)):
        p.add_via(float(x), float(y), diameter=1.0)
    for cell in (1.0, 0.5):
        nx = int(round(40 / cell))
        net = fvm.Network(p, nx, nx)
        real = sum(len(b[0]) for b in net.via_blocks)
        assert memory.via_cells(p, cell) == pytest.approx(real, rel=0.25), cell


def test_the_law_with_vias_stays_above_the_measured_peaks_of_the_study():
    """!
    @brief The measured peaks of boards with scattered vias (CO60 plated holes, 769 of them, copper full or in stripes; research/memory-guard README 14.12) are at or below the estimate.
    @details Tuples are (model, unknowns, plan cells, footprint cells of the vias, measured peak in GB). The peaks are those of the symmetric-mode LU (`fvm.lu_factor`), after
             which the via term was refitted from 0.40 to 0.10; the worst underestimate on the 85 via cases of the reviewer's re-run is 1.27 (small CO60 boards the via-free law already misses).
    @return None.
    """
    pts = [("fvm", 545_305, 109_061, 5442.0, 2.42), ("fvm", 277_440, 55_488, 4071.0, 1.18), ("fvm", 135_375, 27_075, 2525.0, 0.55),
           ("fvm", 218_122, 109_061, 5442.0, 0.66), ("fvm", 110_976, 55_488, 4071.0, 0.37)]
    for model, n, cells, f, peak in pts:
        est = memory.estimate_bytes(model, n, cells, BASE, 1.0, f) / GB
        assert est >= peak, (model, n, est, peak)
        assert est <= 2.5 * peak, (model, n, est, peak)                              # not a blanket margin: the term is at most VIA_GAIN
    # The term costs boards with vias only, and at most VIA_GAIN of the allocated part
    n, cells = 545_305, 109_061
    no = memory.estimate_bytes("fvm", n, cells, BASE) - BASE
    yes = memory.estimate_bytes("fvm", n, cells, BASE, 1.0, 5442.0) - BASE
    assert 1.0 < yes / no <= 1.0 + memory.VIA_GAIN


def test_check_adds_the_via_term_and_keeps_the_bound_a_lower_bound():
    """!
    @brief A board with vias is estimated above the same board without them, the verdict objects carry the exact count, and the cell that fits is not finer for it.
    @return None.
    """
    from pcbthermal.model import Problem
    def board(vias):
        p = Problem.new(80, 80, layers=2)
        p.add_zone(1, rect=(0, 0, 80, 40))
        p.add_zone(2, rect=(0, 20, 80, 80))
        p.add_heater(1, 1.0, rect=(30, 30, 40, 40))
        if vias:
            p.add_via_array((10, 10, 70, 70), 25, 25, diameter=0.3)
        return p
    a = memory.check(board(False), ("fvm",), 0.5, refuse="return", quiet=True, base=BASE)[0]
    b = memory.check(board(True), ("fvm",), 0.5, refuse="return", quiet=True, base=BASE)[0]
    assert b.unknowns == a.unknowns and b.estimate > a.estimate
    assert b.estimate - BASE <= (1.0 + memory.VIA_GAIN) * (a.estimate - BASE) * 1.0000001
    # With a tiny machine both are refused from the bound, which carries no via term
    ra = memory.check(board(False), ("fvm",), 0.5, refuse="return", quiet=True, base=BASE, ram=int(0.2e9))[0]
    rb = memory.check(board(True), ("fvm",), 0.5, refuse="return", quiet=True, base=BASE, ram=int(0.2e9))[0]
    assert ra.verdict == rb.verdict == "refuse" and rb.estimate == ra.estimate


def test_estimate_does_not_follow_the_history_of_the_process(monkeypatch):
    """!
    @brief The estimate of the same problem is the same after the process has grown (the calculation process serves every job of a session).
    @details Found with the CO60 import at 0.365 mm in the calculation process: ok at 9.80 GB when fresh, refuse at 10.39 GB after one 1 mm run, from the live resident size alone.
    @param monkeypatch pytest fixture.
    @return None.
    """
    prob = reference_problem()
    fresh = memory.check(prob, ("fvm",), 0.5, refuse="return", quiet=True)[0].estimate
    monkeypatch.setattr(memory, "resident_bytes", lambda: BASE + 3.0e9)       # Ballast left by earlier solves
    after = memory.check(prob, ("fvm",), 0.5, refuse="return", quiet=True)[0].estimate
    assert after == fresh
    assert memory.estimate_bytes("fvm", 1.0e5, 5.0e4) == memory.estimate_bytes("fvm", 1.0e5, 5.0e4, base=BASE)
    memory.reset_baseline()                                                      # A new reading is a new baseline
    assert memory.baseline_bytes() == BASE + 3.0e9


def test_calculation_process_reads_the_baseline_before_its_first_job(monkeypatch):
    """!
    @brief The calculation process takes its base before any job: a first job without an estimate (the Power Calculator) must not freeze an inflated base.
    @details Found by the review: with the base read at the first estimate, a Power Calculator run of the CO60 at 0.7 mm left the process at 1.21 GB and the
             base stayed 1.21 GB for the whole session (0.365 mm: 10.93 GB refuse instead of 9.80 GB ok).
    @param monkeypatch pytest fixture.
    @return None.
    """
    import queue
    from pcbthermal import jobs
    size = [BASE]
    monkeypatch.setattr(memory, "resident_bytes", lambda: size[0])
    memory.reset_baseline()

    def grow(progress):
        """!
        @brief A job that leaves 2 GB in the process and makes no estimate.
        @param progress Progress callback (unused).
        @return None.
        """
        size[0] = BASE + 2.0e9

    monkeypatch.setitem(jobs.JOBS, "grow", grow)
    tasks, results = queue.Queue(), queue.Queue()
    tasks.put((1, "grow", ()))
    tasks.put(None)
    jobs.serve(tasks, results)
    assert results.get_nowait()[1] == "done"
    assert memory.baseline_bytes() == BASE


def test_baseline_is_read_once_by_concurrent_threads(monkeypatch):
    """!
    @brief Threads that estimate at the same moment (the import window's workers) read the resident size once and share it.
    @param monkeypatch pytest fixture.
    @return None.
    """
    import threading
    import time
    reads = []

    def slow_read():
        """!
        @brief A slow resident-size reading that returns a new number at each call.
        @return Bytes.
        """
        reads.append(1)
        time.sleep(0.05)
        return BASE + len(reads)

    monkeypatch.setattr(memory, "resident_bytes", slow_read)
    memory.reset_baseline()
    seen = []
    threads = [threading.Thread(target=lambda: seen.append(memory.baseline_bytes())) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(reads) == 1 and len(set(seen)) == 1
