#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_memory.py
@brief Tests of the memory law of the model key `fem` in `pcbthermal/memory.py`: the law covers the measured growth, is monotone, gives verdicts consistent with the 3D solid, and refuses with the reason.
@details The measured pairs are the 21 runs of `releases/2.8.0/fem-model/scripts/measure_fem_law.py` (unknowns, growth of the resident size over the build and the solve in bytes, each run in a fresh process).
"""

import numpy as np
import pytest

from pcbthermal import femmesh, memory
from pcbthermal.model import Problem

# (solver, unknowns, growth in bytes) measured on 10 boards of the regression harness
MEASURED = [("d", 14400, 157089792), ("d", 15039, 162611200), ("d", 11007, 105136128), ("d", 15632, 192479232), ("d", 15876, 181469184), ("d", 18720, 217088000),
            ("d", 10368, 100040704), ("d", 8928, 89751552), ("c", 67229, 447201280), ("c", 54671, 380583936), ("c", 53181, 351485952), ("c", 55488, 383811584),
            ("c", 40140, 264765440), ("c", 40328, 263979008), ("c", 72000, 461504512), ("c", 57600, 386154496), ("c", 147456, 1001095168), ("c", 212724, 1422245888),
            ("c", 215172, 1453752320), ("c", 154568, 1029210112), ("c", 155196, 1040990208)]


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


def test_the_law_covers_every_measured_run_with_the_margin_of_ten_percent():
    """!
    @brief The estimate (without the base of the process) is at least the measured growth of every run, and at least 1.1 times the largest conjugate-gradient one per unknown.
    @return None.
    """
    for _, n, growth in MEASURED:
        assert memory.estimate_bytes("fem", n, n / 10.0, base=0.0) >= growth
    worst = max(g / n for s, n, g in MEASURED if s == "c")
    assert memory.estimate_bytes("fem", 200_000, 20_000.0, base=0.0) >= 1.1 * worst * 200_000 - 1.0
    worst_direct = max(g / n for s, n, g in MEASURED if s == "d")
    assert memory.estimate_bytes("fem", 20_000, 2_000.0, base=0.0) >= 1.1 * worst_direct * 20_000 - 1.0


def test_the_law_never_decreases_with_the_unknowns():
    """!
    @brief The estimate is non-decreasing in the unknowns, also across the limit of the direct solve.
    @return None.
    """
    ns = np.unique(np.concatenate([np.linspace(1_000, 400_000, 400), [memory.FEM_DIRECT_MAX - 1, memory.FEM_DIRECT_MAX, memory.FEM_DIRECT_MAX + 1]]))
    est = [memory.estimate_bytes("fem", n, n / 10.0, base=0.0) for n in ns]
    assert all(b >= a for a, b in zip(est, est[1:]))
    assert memory.largest_unknowns("fem", 1000.0, 4e9, base=0.0) > 400_000
    # the largest count fits and one more percent does not
    n = memory.largest_unknowns("fem", 1000.0, 2e9, base=0.0)
    assert memory.estimate_bytes("fem", n, 1000.0, 0.0) <= 2e9 < memory.estimate_bytes("fem", n * 1.01, 1000.0, 0.0)


def test_the_other_models_are_unchanged():
    """!
    @brief The laws of the FVM, the FDM and the 3D solid give the numbers of the formula they had (a fixed point of each).
    @return None.
    """
    for model, (k1, p, a, safety) in {"fvm": (1469.0, 1.24, 0.79, 1.40), "fdm": (1228.0, 1.34, 1.03, 1.24), "solid3d": (1063.0, 1.30, 0.98, 1.30)}.items():
        assert memory.CONTINUOUS[model] == (k1, p, a, safety)
    assert memory.estimate_bytes("solid3d", 500_000, 25_000.0, base=0.0) == pytest.approx(1063.0 * 20.0 ** 0.98 * 500_000 * 1.30)
    assert memory.via_gain("fem", 1e6) == 1.0 and memory.via_gain("fvm", 1e6) > 1.0


def test_verdicts_are_consistent_with_the_3d_solid():
    """!
    @brief On the same board and machine the FEM and the 3D solid both say ok when small, both refuse when large, and the messages name the cell that fits.
    @return None.
    """
    p = _board(60.0, 40.0, 4)
    ram = 16 * 10 ** 9
    v = memory.check(p, ("solid3d", "fem"), 2.0, fraction=0.6, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True)
    assert [x.model for x in v] == ["solid3d", "fem"] and all(x.verdict == "ok" for x in v)
    assert v[1].unknowns == femmesh.unknowns(p, 2.0)[0] and v[1].exact
    big = _board(300.0, 200.0, 4)
    v = memory.check(big, ("solid3d", "fem"), 0.5, fraction=0.6, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True)
    assert [x.verdict for x in v] == ["refuse", "refuse"]
    assert "finite elements (FEM)" in v[1].message and "use a cell of" in v[1].message
    assert v[1].cell_fit is not None and v[1].cell_fit > 0.5
    # the cell that fits does fit
    fit = memory.check(big, ("fem",), v[1].cell_fit, fraction=0.6, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True)[0]
    assert fit.verdict in ("ok", "slow")
    with pytest.raises(memory.MemoryGuardError, match="finite elements"):
        memory.check(big, ("fem",), 0.5, fraction=0.6, ram=ram, available=ram, base=0.1e9, quiet=True)


def test_a_problem_with_no_mesh_is_a_refusal_with_the_reason():
    """!
    @brief A slanted outline is a refused verdict of the FEM only, with the mesh's reason as the message; the other models in the list are still estimated.
    @return None.
    """
    p = _board(20.0, 20.0)
    p.set_outline([(0, 0), (20, 0), (0, 20)])
    v = memory.check(p, ("fvm", "fem"), 2.0, refuse="return", ram=16 * 10 ** 9, available=16 * 10 ** 9, base=0.1e9, quiet=True)
    assert [x.model for x in v] == ["fvm", "fem"]
    assert v[0].verdict == "ok" and v[1].verdict == "refuse"
    assert "axis-aligned outline" in v[1].message and v[1].unknowns == 0
    with pytest.raises(memory.MemoryGuardError, match="axis-aligned outline"):
        memory.check(p, ("fem",), 2.0, ram=16 * 10 ** 9, available=16 * 10 ** 9, base=0.1e9, quiet=True)


def test_the_fem_options_change_the_count_that_the_guard_sees():
    """!
    @brief The elements across a gap and the refinement ratio of the options reach the guard (more elements, more unknowns, a larger estimate).
    @return None.
    """
    p = _board(40.0, 30.0, 4)
    ram = 16 * 10 ** 9
    a = memory.check(p, ("fem",), 2.0, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True, fem_params=(4, 2.0))[0]
    b = memory.check(p, ("fem",), 2.0, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True, fem_params=(12, 2.0))[0]
    c = memory.check(p, ("fem",), 2.0, refuse="return", ram=ram, available=ram, base=0.1e9, quiet=True, fem_params=(4, 4.0))[0]
    assert b.unknowns > a.unknowns and b.estimate > a.estimate
    assert c.unknowns > a.unknowns
    assert a.unknowns == femmesh.unknowns(p, 2.0, 4, 2.0)[0]
