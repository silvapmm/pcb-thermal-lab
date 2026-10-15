"""!
@file test_models_agree.py
@brief The three independent models must agree on the reference board.
"""

import pytest

from pcbthermal import analytic, fvm, lumped
from pcbthermal.model import reference_problem


@pytest.mark.parametrize("layers", [1, 2, 4])
def test_analytic_equals_fvm_with_insulated_edges(layers):
    # Same physics, independent maths (cosine series versus finite volumes): must match closely
    p = reference_problem(layers=layers)
    p.board.h_side = None
    a = analytic.solve_steady(p).t_max
    f = fvm.solve_steady(p, cell_mm=1.0).t_max
    assert a == pytest.approx(f, rel=0.005)


@pytest.mark.parametrize("layers", [1, 2, 4])
def test_lumped_close_to_fvm(layers):
    p = reference_problem(layers=layers)
    l = lumped.solve_steady(p)
    f = fvm.solve_steady(p, cell_mm=1.0)
    # The lumped network is an approximation: within 8 % of the temperature rise
    assert l.delta_t == pytest.approx(f.delta_t, rel=0.08)
    assert l.t_mean == pytest.approx(f.t_mean, abs=0.5)
    assert abs(l.balance_error) < 1e-9


def test_all_models_conserve_energy():
    p = reference_problem()
    for r in (fvm.solve_steady(p), lumped.solve_steady(p), analytic.solve_steady(p)):
        assert abs(r.balance_error) < 1e-9


def test_vertical_coupling_matters():
    # Perfectly coupled layers give a lower peak than the real dielectric: the old merged-sheet
    # assumption is optimistic by more than 10 % on the reference board
    p = reference_problem()
    real = analytic.solve_steady(p).t_max
    p.board.materials.k_fr4_through = 1e4
    merged = analytic.solve_steady(p).t_max
    assert merged < real - 5.0
