"""!
@file test_models_agree.py
@brief The three independent models must agree on the reference board.
"""

import pytest

from pcbthermal import Problem, SolverOptions, analytic, fvm, lumped, simulate
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


def test_lumped_does_not_depend_on_the_ring_count_or_jump_with_the_source_size():
    # Rings thinner than a cell used to make the Lumped hotter with more rings (40 rings: +3 to +13 % against the FVM) and to jump by 1 % from one
    # millimetre of source size to the next; rings narrower than a cell are now merged (lumped.RING_MIN_WIDTH)
    from pcbthermal.model import Materials
    cu, gap = 35.6e-6, 1.5789e-3
    errs = {}
    for side in (33.0, 35.0, 36.0):
        mat = Materials(k_copper=400, k_fr4_through=0.4, k_fr4_inplane=0.4)
        p = Problem.new(50.0, 50.0, layers=2, thickness_mm=(2 * cu + gap) * 1e3, copper_um=cu * 1e6, ambient=0.0, h_top=5, h_bottom=5, h_side=None, materials=mat)
        p.add_full_copper()
        p.add_heater(1, 2.5, rect=(25 - side / 2, 25 - side / 2, 25 + side / 2, 25 + side / 2), name="U")
        f = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max
        for rings in (10, 20, 40):
            errs[(side, rings)] = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5, lumped_rings=rings)).results["lumped"].t_max / f - 1.0
    vals = list(errs.values())
    assert max(abs(e) for e in vals) < 0.01 and max(vals) - min(vals) < 0.005
