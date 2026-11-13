#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_verification.py
@brief The 3D solid against an analytical benchmark (spreading resistance of a circular source, Yovanovich 2003) and a grid-convergence study (Richardson, GCI).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "solid3d-verification", "scripts"))

import solid3d_verification as sv                                              # noqa: E402
from pcbthermal import memory                                                  # noqa: E402


@pytest.fixture(autouse=True)
def small_process_baseline(monkeypatch):
    """!
    @brief Give the memory guard the base of a fresh process, whatever the size of the pytest process.
    @details The guard reads the resident size ONCE per process (`memory.baseline_bytes`), at the first estimate; in the whole battery that first estimate
             happens late, in a process of several GB (GUI tests), and the 105 000-unknown solid of these tests then reads 10.5 GB against 3.7 GB alone and is refused.
             The tests check the physics of the solid, not the guard, so the base is fixed at the measured fresh-process value and restored afterwards.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(memory, "_BASELINE", 0.108e9)


@pytest.mark.parametrize("eps", [0.2, 0.3])
def test_circular_source_spreading_resistance_matches_the_published_table(eps):
    """Within 2 % of Table 3 (isoflux source, semi-infinite flux tube) at a cell of 1 mm; the square block of the same area replaces the cylinder."""
    psi = sv.circular_psi(eps, cell_mm=1.0, n_diel=40)
    assert psi == pytest.approx(sv.PSI_ISOFLUX[eps], rel=2e-2)


def test_grid_convergence_is_monotone_second_order_like_and_small():
    """A source aligned with every mesh: monotone convergence, an observed order between 1 and 2.5, a fine-mesh GCI under 3 % and an extrapolated value within 1 % of the fine one."""
    g = sv.grid_convergence(cells=(4.0, 2.0, 1.0))
    assert g["monotone"]
    assert 1.0 < g["order"] < 2.5
    assert g["gci"] < 0.03
    assert g["extrapolated"] == pytest.approx(g["values"][2], rel=1e-2)
