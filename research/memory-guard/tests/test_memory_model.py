#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_memory_model.py
@brief Tests of the estimator prototype: the RAM is read, the estimate is monotone and ordered by class, the verdict refuses above the limit, the fit recovers known coefficients and the cell that fits really fits.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import memory_model as mm                                  # noqa: E402


def test_ram_is_a_positive_number():
    """!
    @brief The physical memory is read on this machine (a plausible size: between 256 MB and 16 TB).
    @return None.
    """
    r = mm.ram_bytes()
    assert r is not None and 256e6 < r < 16e12


@pytest.mark.parametrize("klass", list(mm.COEFFS))
def test_estimate_is_monotone_and_above_the_base(klass):
    """!
    @brief For every class the estimate grows with the unknowns and never falls below the base.
    @param klass Class key.
    @return None.
    """
    ns = np.geomspace(1e3, 5e6, 30)
    est = [mm.estimate_bytes(n, klass) for n in ns]
    assert all(b > a for a, b in zip(est, est[1:]))
    assert est[0] >= mm.COEFFS[klass].base


def test_classes_are_ordered():
    """!
    @brief At the same unknowns a laminate board with more layers takes more than one with fewer, and the 3D solid with many slabs more than with few.
    @return None.
    """
    n = 600_000
    assert mm.estimate_bytes(n, "layered_plain") < mm.estimate_bytes(n, "layered_laminate_few") < mm.estimate_bytes(n, "layered_laminate_many")
    assert mm.estimate_bytes(n, "solid3d_few") < mm.estimate_bytes(n, "solid3d_many")
    assert mm.estimate_bytes(n, "lumped") < mm.estimate_bytes(n, "layered_plain")


def test_transient_costs_more():
    """!
    @brief A time simulation holds two factorisations: its estimate is larger.
    @return None.
    """
    assert mm.estimate_bytes(1e5, "layered_plain", transient=True) > mm.estimate_bytes(1e5, "layered_plain")


def test_classification():
    """!
    @brief The class helpers follow the documented rules.
    @return None.
    """
    assert mm.classify_layered(4, False) == "layered_plain"
    assert mm.classify_layered(2, True) == "layered_laminate_few"
    assert mm.classify_layered(4, True) == "layered_laminate_many"
    assert mm.classify_solid3d(6) == "solid3d_few" and mm.classify_solid3d(7) == "solid3d_many"


def test_refusal_above_the_limit_and_simulated_machines():
    """!
    @brief The verdict is refuse above the limit, slow in between and ok below, for simulated machines of 8, 16 and 64 GB; a million-unknown 4-layer laminate board is refused on 8 GB and run on 64 GB.
    @return None.
    """
    big = mm.estimate_bytes(1_000_000, "layered_laminate_many")
    for ram_gb, expect in ((8, "refuse"), (64, "ok")):
        ram = ram_gb * 1e9
        v = mm.verdict(big, mm.limit_bytes(0.7, ram), ram=ram)
        assert v == expect or (expect == "ok" and v == "slow")
    ram = 16e9
    lim = mm.limit_bytes(0.7, ram)
    assert mm.verdict(0.2 * ram, lim, ram=ram) == "ok"
    assert mm.verdict(0.5 * ram, lim, ram=ram) == "slow"
    assert mm.verdict(0.8 * ram, lim, ram=ram) == "refuse"


def test_unreadable_ram_falls_back_to_the_fixed_limit():
    """!
    @brief When the RAM cannot be read the limit is the fixed fallback, never zero or infinite.
    @return None.
    """
    assert mm.limit_bytes(0.7, ram=None) in (mm.FALLBACK_LIMIT, mm.limit_bytes(0.7))
    assert mm.verdict(1e9, mm.FALLBACK_LIMIT, ram=None) in ("ok", "slow")


def test_largest_unknowns_inverts_the_estimate():
    """!
    @brief largest_unknowns is the inverse of estimate_bytes at the limit.
    @return None.
    """
    lim = 8e9
    n = mm.largest_unknowns("layered_laminate_few", lim)
    assert mm.estimate_bytes(n, "layered_laminate_few") <= lim < mm.estimate_bytes(n * 1.01 + 10, "layered_laminate_few")
    assert mm.largest_unknowns("layered_plain", 1e6) == 0              # Below the base nothing fits


def test_cell_that_fits_really_fits():
    """!
    @brief For a board whose unknowns go as 1 / cell^2, the cell returned fits the limit and a cell 20 % smaller does not (the search grows the cell in steps of 10 %).
    @return None.
    """
    count = lambda c: int(4 * (100.0 / c) ** 2)                        # noqa: E731  A 4-layer board of 100 mm
    lim = 4e9
    c = mm.cell_that_fits(count, "layered_laminate_many", lim, 0.1)
    assert c is not None and mm.estimate_bytes(count(c), "layered_laminate_many") <= lim
    assert mm.estimate_bytes(count(c * 0.8), "layered_laminate_many") > lim


def test_fit_recovers_known_coefficients():
    """!
    @brief The fit returns the exponent and the coefficient of synthetic points made with the law (with 3 % noise it stays within 10 %).
    @return None.
    """
    true = mm.Coeffs(0.4e9, 8.0e3, 4.0 / 3.0)
    ns = [5e4, 1e5, 2e5, 4e5, 8e5]
    pts = [(n, mm.estimate_bytes(n, "x", {"x": true})) for n in ns]
    c = mm.fit_class(pts, base=0.4e9)
    assert c.p == pytest.approx(4 / 3, rel=1e-6) and c.k == pytest.approx(8.0e3, rel=1e-6)
    rng = np.random.default_rng(1)
    noisy = [(n, m * (1 + 0.03 * rng.standard_normal())) for n, m in pts]
    c2 = mm.fit_class(noisy, base=0.4e9)
    assert c2.k == pytest.approx(8.0e3, rel=0.10) and 1.1 < c2.p < 1.6


def test_fit_needs_two_sizes():
    """!
    @brief One size cannot give an exponent.
    @return None.
    """
    with pytest.raises(ValueError):
        mm.fit_class([(1e5, 1e9), (1e5, 1.1e9)])


def test_sor_block_guard_replaces_the_constant():
    """!
    @brief 5 000 unknowns (16 n^2 = 400 MB) fit on a 16 GB machine at 70 %, 30 000 (14 GB) do not.
    @return None.
    """
    lim = mm.limit_bytes(0.7, 16e9)
    assert mm.sor_block_fits(5000, lim) and not mm.sor_block_fits(30000, lim)


def test_analytic_estimate_grows_with_the_square_of_the_tiles():
    """!
    @brief The dense correction of the Analytic model goes as (tiles x layers)^2: doubling the tiles about quadruples the part above the base.
    @return None.
    """
    a = mm.analytic_bytes(2000, 4, modes=0) - mm.BASE_DEFAULT
    b = mm.analytic_bytes(4000, 4, modes=0) - mm.BASE_DEFAULT
    assert 3.9 < b / a < 4.1
