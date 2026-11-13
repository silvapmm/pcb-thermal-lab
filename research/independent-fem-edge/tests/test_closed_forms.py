#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_closed_forms.py
@brief Validation (1), (2) and (5) of the finite-element solver: the 1D series stack, the 1D fin with a Robin end, the 2D sheet with two Robin walls
       and a rectangular source (own series), and the energy balance to 1e-9 on every solve.
"""

import numpy as np

import board
import exact
import fem
import mesh2d


def _stack_model(n_gap, h_top, h_bottom, q_area):
    """!
    @brief Two copper layers and a gap on a 1 x 1 mm plan (insulated sides), uniform source in the top copper.
    @param n_gap Elements through the gap.
    @param h_top Top film.
    @param h_bottom Bottom film.
    @param q_area Source per area W/m2.
    @return Tuple (model, extrusion dict).
    """
    plan = mesh2d.tensor(np.linspace(0, 1e-3, 3), np.linspace(0, 1e-3, 3))
    dz = np.concatenate([[35e-6], board.graded_gap(1.53e-3, n_gap, 1.3), [35e-6]])
    ex = board.extrude(plan, dz)
    m = fem.Model(ex["nodes"], ex["elems"])
    kk = np.array([385.0] + [0.3] * n_gap + [385.0])[ex["slab"]]
    m.k[:] = kk[:, None]
    m.q[ex["slab"] == 0] = q_area / 35e-6
    Np = ex["n_plan"]
    m.add_faces(plan.quads, h=h_top)
    m.add_faces(plan.quads + (n_gap + 2) * Np, h=h_bottom)
    return m, ex


def test_series_stack_matches_the_closed_form_at_every_interface():
    """!
    @brief The nodal temperatures of the 1D stack equal the closed form (1D linear elements are nodally exact for a piecewise-constant source).
    @return None.
    """
    q_area = 1000.0
    m, ex = _stack_model(5, 10.0, 200.0, q_area)
    r = m.solve()
    ref = exact.series_stack([35e-6, 1.53e-3, 35e-6], [385.0, 0.3, 385.0], 10.0, 200.0, q_area)
    Np = ex["n_plan"]
    zn = ex["zn"]
    for s, z in enumerate(zn):
        t_fem = r["T"][s * Np]
        assert abs(t_fem - ref["T_of"](z)) < 1e-9 * abs(ref["T_of"](z)), (z, t_fem, ref["T_of"](z))
    assert abs(r["balance"] - 1.0) < 1e-9
    # the heat split between the faces is the closed form's
    T = r["T"]
    assert abs(10.0 * T[0] - ref["q_up"]) < 1e-9 * ref["q_up"]
    assert abs(200.0 * T[(zn.size - 1) * Np] - ref["q_down"]) < 1e-9 * ref["q_down"]


def test_fin_with_robin_end_matches_the_closed_form():
    """!
    @brief A thin copper strip with a source on its first part, films on both faces and a Robin end: the 3D model equals the 1D fin to the fin approximation (Biot 1e-6).
    @return None.
    """
    L, Wd, t, a = 10e-3, 1e-3, 35e-6, 2e-3
    k, h, h_end = 385.0, 50.0, 1000.0
    q0 = 2000.0                                                     # W/m2 over [0, a]
    xn = np.linspace(0, L, 201)
    plan = mesh2d.tensor(xn, np.linspace(0, Wd, 3))
    b = board.Board(plan, 1, board_t=t, t_cu=t, k_cu=k, h_top=h, h_bottom=h, h_side=h_end, symmetry=[("x", 0.0), ("y", 0.0), ("y", Wd)],
                    heaters=[(np.array([[0, 0], [a, 0], [a, Wd], [0, Wd]]), q0 * a * Wd)], copper=None)
    r = b.solve()
    T = exact.fin_robin(k * t, 2 * h, L, a, q0, h_end * t)
    Np = r["info"]["ex"]["n_plan"]
    top = r["T"][:Np]
    x = plan.xy[:, 0]
    err = np.abs(top - T(x)) / T(0.0)
    assert err.max() < 1e-5, err.max()
    assert abs(r["balance"] - 1.0) < 1e-9
    # the Robin end carries the right share: -S T'(L) = h_end t T(L): check through the end flux of the closed form against the FEM wall heat
    T_end_fem = top[np.isclose(x, L)].mean()
    assert abs(T_end_fem - T(L)) < 1e-5 * T(0.0)


def _sheet(nx, ny):
    """!
    @brief 10 x 6 mm copper sheet, source on [0, 2] x [1, 3] mm, two Robin walls (x = L, y = W) with a strong film, insulated at x = 0, y = 0.
    @param nx Elements along x.
    @param ny Elements along y.
    @return Tuple (result dict, plan, closed-form callable).
    """
    L, Wd, t = 10e-3, 6e-3, 35e-6
    k, h, hs = 385.0, 50.0, 1e5
    rect = (0.0, 1e-3, 2e-3, 3e-3)
    q0 = 1000.0
    xn = np.unique(np.concatenate([np.linspace(0, L, nx + 1), [rect[2]]]))
    yn = np.unique(np.concatenate([np.linspace(0, Wd, ny + 1), [rect[1], rect[3]]]))
    plan = mesh2d.tensor(xn, yn)
    poly = np.array([[rect[0], rect[1]], [rect[2], rect[1]], [rect[2], rect[3]], [rect[0], rect[3]]])
    b = board.Board(plan, 1, board_t=t, t_cu=t, k_cu=k, h_top=h, h_bottom=h, h_side=hs, symmetry=[("x", 0.0), ("y", 0.0)],
                    heaters=[(poly, q0 * (rect[2] - rect[0]) * (rect[3] - rect[1]))], copper=None)
    r = b.solve()
    T = exact.sheet_robin_2d(k * t, 2 * h, L, Wd, rect, q0, hs * t, hs * t, n_modes=600)
    return r, plan, T


def test_sheet_with_two_robin_walls_matches_the_series_and_converges_at_second_order():
    """!
    @brief The 2D sheet with a rectangular source and two strongly cooled walls: the FEM equals the own Robin-eigenfunction series, error falling as h^2.
    @return None.
    """
    errs = []
    for n in (1, 2, 4):
        r, plan, T = _sheet(20 * n, 12 * n)
        Np = r["info"]["ex"]["n_plan"]
        top = r["T"][:Np]
        ref = T(plan.xy[:, 0], plan.xy[:, 1])
        errs.append(np.abs(top - ref).max() / ref.max())
        assert abs(r["balance"] - 1.0) < 1e-9
    assert errs[-1] < 2e-3, errs
    rate = np.log(errs[0] / errs[-1]) / np.log(4.0)
    assert rate > 1.7, (errs, rate)


def test_balance_identity_holds_with_a_varying_ambient_and_a_prescribed_flux():
    """!
    @brief The balance uses the heat leaving at the real ambient and counts prescribed fluxes: an ambient per face node and a flux face both close to 1e-9.
    @return None.
    """
    plan = mesh2d.tensor(np.linspace(0, 2e-3, 5), np.linspace(0, 1e-3, 3))
    ex = board.extrude(plan, np.array([0.1e-3] * 3))
    m = fem.Model(ex["nodes"], ex["elems"])
    m.k[:] = [2.0, 1.0, 0.5]
    Np = ex["n_plan"]
    m.add_faces(plan.quads, h=30.0, t_amb=np.linspace(1.0, 2.0, plan.quads.shape[0]))
    m.add_faces(plan.quads + 3 * Np, h=20.0, flux=500.0)
    r = m.solve()
    assert abs(r["balance"] - 1.0) < 1e-9
    assert abs(r["q_in"] - 500.0 * 2e-6) < 1e-15
