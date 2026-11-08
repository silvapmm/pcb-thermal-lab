#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_measure_and_ordering.py
@brief Tests of the measurement wrapper (a tiny board in a child process: the peak is recorded and a tiny cutoff kills it) and of the cell-major ordering (same temperatures as the program, small boards).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import cases                                               # noqa: E402
import cell_major                                          # noqa: E402
import measure                                             # noqa: E402
from pcbthermal import fvm                                 # noqa: E402

TINY = dict(family="plain", layers=2, size_mm=20.0, cell_mm=2.0, model="fvm", order="layer", series="test")


def test_case_counts_follow_the_cell():
    """!
    @brief Halving the cell about quadruples the unknowns, and the families build.
    @return None.
    """
    import numpy as np
    from pcbthermal import laminate
    a = cases.count(dict(TINY, cell_mm=2.0))[0]
    b = cases.count(dict(TINY, cell_mm=1.0))[0]
    # 2.6.0 (fix/laminate-edge-band) adds laminate nodes in a band along the edge, a fixed width in cells, so on a 20 mm board at 2 mm cells (452 -> 1568 unknowns) the edge band is
    # a larger share than at 1 mm and the ratio is 3.47 instead of 4.0; with the band switched off (the 2.5.x plan) the count is 200 -> 800, exactly four times.
    assert 3.0 < b / a < 4.5
    saved = laminate.edge_band
    laminate.edge_band = lambda edge, d, dx, active: np.zeros(np.shape(active), dtype=bool)
    try:
        a0 = cases.count(dict(TINY, cell_mm=2.0))[0]
        b0 = cases.count(dict(TINY, cell_mm=1.0))[0]
    finally:
        laminate.edge_band = saved
    assert 3.5 < b0 / a0 < 4.5
    for fam in cases.FAMILIES:
        try:
            n = cases.count(dict(TINY, family=fam, layers=4, size_mm=30.0))[0]
        except RuntimeError as exc:                     # a family built from the open boards needs PCBT_REAL_BOARDS: skip without it instead of failing
            if "PCBT_REAL_BOARDS" in str(exc):
                pytest.skip(str(exc))
            raise
        assert n > 0


def test_wrapper_records_a_peak_and_the_answer():
    """!
    @brief A tiny board runs in a child; the peak is larger than 50 MB (the interpreter, NumPy, SciPy) and the answer is a positive rise.
    @return None.
    """
    rec = measure.run_case(TINY, kill_bytes=4e9, timeout_s=120)
    assert rec["status"] == "ok"
    assert rec["peak_bytes"] > 50e6 and rec["theta_max"] > 0 and rec["unknowns"] > 0


def test_wrapper_kills_above_the_cutoff():
    """!
    @brief With a cutoff below the size of the interpreter the child is killed and the status says so.
    @return None.
    """
    rec = measure.run_case(dict(TINY, size_mm=60.0, cell_mm=0.5), kill_bytes=60e6, timeout_s=120)
    assert rec["status"] in ("killed_memory", "error")


@pytest.mark.parametrize("family,layers,cell", [("plain", 2, 4.0), ("partial", 2, 3.0), ("partial", 4, 3.0), ("outline", 2, 3.0), ("vias", 4, 3.0)])
def test_cell_major_gives_the_same_temperatures(family, layers, cell):
    """!
    @brief The renumbered solve agrees with the program's solve to 1e-9 K on small boards of the families.
    @param family Board family.
    @param layers Copper layers.
    @param cell Cell in mm.
    @return None.
    """
    p = cases.build(dict(family=family, layers=layers, size_mm=60.0))
    nx = ny = int(round(60.0 / cell))
    net = fvm.Network(p, nx, ny)
    a, _ = net.solve_steady()
    b, res = cell_major.solve_cell_major(net)
    assert np.abs(a - b).max() < 1e-9
    assert res < 1e-9


def test_cell_major_order_is_a_permutation():
    """!
    @brief The order lists every index once and puts the nodes of a cell next to each other.
    @return None.
    """
    o = cell_major.cell_major_order(3, 5)
    assert sorted(o) == list(range(15))
    assert list(o[:3]) == [0, 5, 10]
