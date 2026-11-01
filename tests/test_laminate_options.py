#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_laminate_options.py
@brief The laminate parameters S_MAX and N_MAX as options of the run (SolverOptions.laminate_s_max_mm and laminate_n_max): validation, saving only when not default, the
       default run bit for bit the constants, and the same numbers reaching the networks, the unknown counters, the memory guard and the command line.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_laminate_rule import window_board                     # noqa: E402

from pcbthermal import cli, fdm, fvm, laminate, memory         # noqa: E402
from pcbthermal.api import SolverOptions, simulate             # noqa: E402


def test_defaults_are_the_constants_and_are_not_saved():
    o = SolverOptions()
    assert o.laminate_params() == (laminate.S_MAX, laminate.N_MAX)
    d = o.to_dict()
    assert "laminate_s_max_mm" not in d and "laminate_n_max" not in d          # a project of the earlier versions is written as before
    o.laminate_n_max = 8
    assert SolverOptions.from_dict(o.to_dict()).laminate_n_max == 8 and "laminate_s_max_mm" not in o.to_dict()
    o.laminate_s_max_mm = 0.2
    back = SolverOptions.from_dict(json.loads(json.dumps(o.to_dict())))
    assert back.laminate_params() == (0.2e-3, 8)


@pytest.mark.parametrize("field,value", [("laminate_s_max_mm", 0.0), ("laminate_s_max_mm", 6.0), ("laminate_n_max", 0), ("laminate_n_max", 33), ("laminate_n_max", 2.5)])
def test_out_of_range_values_are_refused(field, value):
    o = SolverOptions()
    setattr(o, field, value)
    with pytest.raises(ValueError):
        o.validate()


def test_using_nests_and_restores():
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)
    with laminate.using(0.2e-3, 8):
        assert laminate.parameters() == (0.2e-3, 8)
        with laminate.using(n_max=2):
            assert laminate.parameters() == (0.2e-3, 2)
        assert laminate.parameters() == (0.2e-3, 8)
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)


def test_the_default_options_give_the_network_of_the_constants_bit_for_bit():
    p = window_board()
    a = fvm.solve_steady(p, 1.0).T
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    assert np.array_equal(sim.results["fvm"].T, a)
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0, laminate_n_max=4, laminate_s_max_mm=0.4))
    assert np.array_equal(sim.results["fvm"].T, a)


def test_the_options_reach_the_fvm_fdm_counts_and_the_solution():
    p = window_board()
    base_f, base_d = fvm.unknowns(p, 1.0)[0], fdm.unknowns(p, 1.0)[0]
    t4 = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=1.0))
    t8 = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=1.0, laminate_n_max=8, laminate_s_max_mm=0.2))
    with laminate.using(0.2e-3, 8):
        more_f, more_d = fvm.unknowns(p, 1.0)[0], fdm.unknowns(p, 1.0)[0]
        assert fvm.Network(p, 30, 30).nl > 2
    assert more_f > base_f and more_d > base_d
    for m in ("fvm", "fdm"):
        assert t8.results[m].T.max() != t4.results[m].T.max()                  # the solution moved with the sub-gaps (more sub-layers, warmer toward the resolved value)
    assert t8.results["fvm"].T.max() > t4.results["fvm"].T.max()               # the rule leaves the network cold: finer sub-gaps warm the part
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)           # nothing leaks out of the run


def test_the_memory_estimate_counts_the_extra_node_layers():
    p = window_board()
    v4 = memory.check(p, ("fvm",), 0.5, refuse="return", quiet=True)[0]
    v8 = memory.check(p, ("fvm",), 0.5, refuse="return", quiet=True, laminate_params=(0.2e-3, 8))[0]
    assert v8.unknowns > v4.unknowns and v8.estimate > v4.estimate
    off = memory.check(p, ("fvm",), 0.5, refuse="return", quiet=True, laminate_params=(0.4e-3, 1))[0]
    assert off.unknowns < v4.unknowns
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)


def test_the_command_line_flags(tmp_path):
    from pcbthermal.project import Project, save_project
    p = window_board()
    path = tmp_path / "w.pcbt.json"
    save_project(str(path), Project(p, SolverOptions(models=("fvm",), cell_mm=2.0)))
    for n in (1, 4):
        out = tmp_path / f"o{n}"
        assert cli.main(["run", str(path), "--model", "fvm", "--cell-mm", "2", "--laminate-n-max", str(n), "--out", str(out), "--no-plots"]) == 0
    # a value out of range is refused, not ignored
    with pytest.raises(ValueError):
        cli.main(["run", str(path), "--model", "fvm", "--laminate-n-max", "0", "--out", str(tmp_path / "x"), "--no-plots"])


def test_a_larger_n_max_alone_changes_nothing_on_a_board_of_four_sub_gaps():
    # The review: a gap gets min(n_max, ceil(d / s_max)) sub-gaps, so on a 1.6 mm two-layer board (d 1.53 mm) the default 0.4 mm already gives 4 and n_max 8 or 32 alone
    # builds the same network; the sub-gap has to be made smaller too (the tooltip and the command-line help say so)
    p = window_board()
    base = fvm.unknowns(p, 1.0)[0]
    with laminate.using(n_max=32):
        assert fvm.unknowns(p, 1.0)[0] == base
    with laminate.using(0.19e-3, 8):
        assert fvm.unknowns(p, 1.0)[0] > base


def test_the_power_calculator_and_the_calibration_use_the_laminate_of_the_project():
    # The review: the Power Calculator job and calibrate_convection ran the board with the default laminate rule whatever the project said
    from pcbthermal import jobs
    from pcbthermal.api import calibrate_convection
    p = window_board()
    progress = lambda *a: None                                                    # noqa: E731
    a = jobs.job_inverse(progress, p, 0, 60.0, "max", 25.0, 1.0)["power_w"]
    b = jobs.job_inverse(progress, p, 0, 60.0, "max", 25.0, 1.0, 0.0, False, None, (0.2e-3, 8))["power_w"]
    assert b != a and b < a                                                       # finer sub-gaps: the part warmer per watt, so less power for the same reading
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)
    m4 = calibrate_convection(p, 160.0, SolverOptions(models=("fvm",), cell_mm=1.0))[0]
    m8 = calibrate_convection(p, 160.0, SolverOptions(models=("fvm",), cell_mm=1.0, laminate_s_max_mm=0.2, laminate_n_max=8))[0]
    assert m8 != m4
