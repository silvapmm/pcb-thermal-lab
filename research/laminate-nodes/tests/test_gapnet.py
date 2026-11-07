#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gapnet.py
@brief Regression tests of the construction on the program's network (lib/gapnet.py, lib/fdmnet.py): the program is reproduced when the mask is empty, the one-layer ladder equals laminate.py for
        the same n, a one-dimensional column does not depend on n, the energy balance holds, the ragged solve and the general SOR agree with the direct solve. Small boards (12 mm, 1 mm cell).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import boards as BD  # noqa: E402
import fdmnet as FN  # noqa: E402
import gapnet as GN  # noqa: E402
import rule as RU  # noqa: E402
from pcbthermal import fdm, fvm, laminate  # noqa: E402


def _spec(name, **kw):
    """!
    @brief A small spec (12 mm board, 4 mm part).
    @param name Name.
    @param kw Fields of Spec.
    @return Spec.
    """
    return BD.Spec(name, size=12.0, part=4.0, **kw)


def test_empty_mask_is_the_program():
    """!
    @brief A board with copper in every cell of every gap (empty mask) has the program's matrix, to the last bit, for 2 and 4 layers, with the vertical correction on.
    @return None.
    """
    for spec in (_spec("2L", layers=2), _spec("4L", layers=4, stack="template")):
        p = BD.problem(spec)
        ref = fvm.Network(p, 12, 12, with_blocks=False, ladder=False)
        net = GN.build(p, 1.0, RU.Rule(n_fixed=4))
        assert net.nl == ref.nl
        assert abs(net.K - ref.K).max() == 0.0 and np.array_equal(net.C, ref.C)


def test_one_layer_ladder_equals_laminate_py():
    """!
    @brief On a one-layer board the ladder with n equal sub-gaps on every cell and no vertical correction equals the program's laminate nodes with the same count (1 and 2).
    @return None.
    """
    spec = _spec("1L", layers=1, shapes=[("pad", 6)])
    p = BD.problem(spec)
    for n in (1, 2):
        old = laminate.LAMINATE_NODES
        laminate.LAMINATE_NODES = n
        try:
            ref = fvm.Network(p, 12, 12, with_blocks=False, ladder=False)
        finally:
            laminate.LAMINATE_NODES = old
        th_ref, _ = ref.solve_steady()
        net = GN.build(p, 1.0, RU.Rule(n_fixed=n, mask="all", vert=False, face=-1.0))
        th, _ = net.solve_steady()
        assert abs(th[0].max() - th_ref[0].max()) < 1e-9 * th_ref[0].max()
        assert abs(th[net.laminate_layers[-1]].max() - th_ref[ref.laminate_layers[-1]].max()) < 1e-9 * th_ref[0].max()


def test_column_does_not_depend_on_n():
    """!
    @brief A heater over the whole board on a two-layer board with a window: heat flows only through the thickness, so any n and the single link give the same field (the nodes are
           in series; the lateral conduction carries nothing).
    @return None.
    """
    spec = BD.Spec("col", layers=2, size=12.0, part=12.0, shapes=[("window", 4), ("full",)])
    p = BD.problem(spec)
    base = GN.build(p, 1.0, RU.Rule(n_fixed=1, vert=False, face=-1.0))
    th0, _ = base.solve_steady()
    for n in (2, 4):
        net = GN.build(p, 1.0, RU.Rule(n_fixed=n, vert=False, face=-1.0))
        th, _ = net.solve_steady()
        assert np.allclose(th[:2], th0[:2], rtol=1e-9, atol=1e-12)


def test_energy_balance_and_nonnegative_arrays():
    """!
    @brief Heat out through the films equals the power, and no node holds a negative conductance or capacity (a laminate share moved that did not exist).
    @return None.
    """
    spec = _spec("bal", layers=2, shapes=[("pad", 6), ("none",)])
    p = BD.problem(spec)
    net = GN.build(p, 0.5, RU.Rule())
    assert net.S.min() >= -1e-18 and net.C.min() >= -1e-18
    th, _ = net.solve_steady()
    out = float(((net.g_amb - net.g_pin) * th).sum())
    assert abs(out / net.Q.sum() - 1.0) < 1e-9


def test_ragged_and_sor_agree_with_direct():
    """!
    @brief The ragged solve gives the direct field on the nodes it keeps; the general red-black SOR converges to the direct field of the same board without vias (the vias are dense couplings now).
    @return None.
    """
    spec = _spec("rag", layers=2, shapes=[("pad", 6), ("none",)], vias=((6.0, 6.0),))
    p = BD.problem(spec)
    net = GN.build(p, 1.0, RU.Rule(n_fixed=3))
    th, _ = net.solve_steady()
    thr, nun = GN.solve_ragged(net)
    assert nun < net.K.shape[0] or net.drop.sum() == 0
    assert np.allclose(thr[~net.drop], th[~net.drop], rtol=1e-9, atol=1e-12)
    # Since `fix/point-via` the vias are dense mean-potential couplings in the matrix, not barrels in the sub-links, so the point colouring of the general SOR no longer applies to a
    # board with vias (the hybrid SOR with via blocks is an open item of the README); the SOR check runs on the same board without the via
    p0 = BD.problem(_spec("rag0", layers=2, shapes=[("pad", 6), ("none",)]))
    net0 = GN.build(p0, 1.0, RU.Rule(n_fixed=3))
    th0, _ = net0.solve_steady()
    ths, res, info = GN.solve_sor_general(net0, tol=1e-10)
    assert info["colours_ok"] and info["converged"] and res < 1e-9
    assert np.allclose(ths, th0, rtol=1e-5, atol=1e-7 * th0.max())


def test_parallel_barrel_breaks_the_colouring_for_even_n(monkeypatch):
    """!
    @brief With the barrel across the whole gap (the old copy) and n = 2 the graph has an odd cycle: the two-colour sweep is not defined (README 7).
    @param monkeypatch pytest fixture. 2.6.0 (fix/via-barrel-and-rim-uncoupling) uncouples a plane that the rim of the drill misses; layer 2 of this board has no copper, so the
           program drops the barrel coupling to it and the graph is bipartite again. The odd cycle is reproduced with the rim shares forced to full contact (the 2.5.x program).
    @return None.
    """
    from pcbthermal import viawell
    spec = _spec("par", layers=2, shapes=[("pad", 6), ("none",)], vias=((6.0, 6.0),))
    p = BD.problem(spec)
    with monkeypatch.context() as m:
        m.setattr(viawell, "rim_copper_shares", lambda problem, v, n_layers, zone_index: [1.0] * n_layers)
        net = GN.build(p, 1.0, RU.Rule(n_fixed=2, via_mode="parallel"))
        assert GN.two_colour(net.K) is None
    net = GN.build(p, 1.0, RU.Rule(n_fixed=2, via_mode="parallel"))
    assert GN.two_colour(net.K) is not None                                # the 2.6.0 program: no barrel into the bare plane, no odd cycle


def test_mixed_columns_with_even_n_are_not_bipartite_and_column_sor_solves_them():
    """!
    @brief Review: refined columns (n links) next to single-link columns close a cycle of length n + 3, so the point colouring fails for every even n on one- and two-layer
           boards alike (odd n colours); the column (block) red-black SOR, coloured on the plan grid, converges to the direct solution in every case.
    @return None.
    """
    for spec in (BD.Spec("1L", size=24.0, part=4.0, layers=1, shapes=[("window", 4)]), BD.Spec("2L", size=24.0, part=4.0, layers=2, shapes=[("window", 4), ("full",)])):
        p = BD.problem(spec)
        for n in (2, 3, 4):
            net = GN.build(p, 1.0, RU.Rule(n_fixed=n))
            F = net.ladder.gaps[0].flagged
            assert F.any() and (~F).any()                                  # flagged and unflagged columns side by side
            assert (GN.two_colour(net.K) is None) == (n % 2 == 0)
            th, _ = net.solve_steady()
            ths, res, info = GN.solve_sor_columns(net, tol=1e-11)
            assert info["colours_ok"] and info["converged"]
            assert np.allclose(ths, th, rtol=1e-6, atol=1e-8 * th.max())


def test_program_preset_takes_a_given_fill():
    """!
    @brief Review: the preset "program" on a one-layer board takes a fill brought from a mask (it used to keep the fill of the Problem's zones, so on the real windows it solved a
           full-copper board); a full fill reproduces the zones' run and a half fill changes it.
    @return None.
    """
    p = BD.problem(_spec("1L full", layers=1, shapes=[("full",)]))
    rl = RU.PRESETS["program"]
    ref, _ = GN.build(p, 1.0, rl).solve_steady()
    same, _ = GN.build(p, 1.0, rl, fill=np.ones((1, 12, 12))).solve_steady()
    half, _ = GN.build(p, 1.0, rl, fill=np.full((1, 12, 12), 0.5)).solve_steady()
    assert np.array_equal(same, ref)
    assert half[0].max() > 1.01 * ref[0].max()


def test_fdm_empty_mask_is_the_program():
    """!
    @brief The FDM with the construction and an empty mask has the matrix of the program's FDM (copper everywhere, two layers).
    @return None.
    """
    spec = _spec("fdm2L", layers=2)
    p = BD.problem(spec)
    ref = fdm.Network(p, 1.0)
    net = FN.build(p, 1.0, RU.Rule(n_fixed=4))
    assert net.nl == ref.nl
    assert abs(net.K - ref.K).max() < 1e-12 * abs(ref.K).max()


def test_fdm_energy_balance():
    """!
    @brief Heat out equals the power in the FDM with nodes under a pad on a bare bottom (the zone border of the refined nodes leaks nothing).
    @return None.
    """
    spec = _spec("fdmbal", layers=2, shapes=[("pad", 6), ("none",)])
    p = BD.problem(spec)
    net = FN.build(p, 1.0, RU.Rule())
    th, _ = net.solve_steady()
    out = float(((net.g_amb - net.g_pin) * th).sum())
    assert abs(out / net.Q.sum() - 1.0) < 1e-9
