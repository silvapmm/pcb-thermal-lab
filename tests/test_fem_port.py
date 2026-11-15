#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_port.py
@brief Tests of `pcbthermal/femcore.py`, the port of the independent finite-element tool: it reproduces the research solver to 1e-9 (on the research cases when the research
       folder is present, and on stored reference numbers always), the closed forms (1D column with films, slab with a source and Robin ends, hollow cylinder), the energy
       balance, the direct against the CG + pyamg solution (skipped without pyamg) and the behaviour without pyamg.
@details The optional cross-check against scikit-fem lives in the research folder's own tests; the program does not depend on it. Light: a few seconds in all.
"""

import contextlib
import importlib
import os
import sys

import numpy as np
import pytest

from pcbthermal import femcore as fc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "helpers"))
import fem_exact as ex                                         # noqa: E402

ROOT = os.path.dirname(HERE)
RESEARCH_LIBS = [os.path.join(ROOT, "research", "independent-fem-edge", "lib"), os.path.join(ROOT, "research", "independent-fem-extensions", "lib")]


@contextlib.contextmanager
def research_modules():
    """!
    @brief Import the research libraries under their own names for one block and remove them again (their module names `fem`, `board`... must not stay).
    @return Context manager yielding a dict name -> module, or skipping the test when the research folder is absent.
    """
    if not all(os.path.isdir(p) for p in RESEARCH_LIBS):
        pytest.skip("research folders not present")
    before = set(sys.modules)
    for p in reversed(RESEARCH_LIBS):
        sys.path.insert(0, p)
    try:
        yield {n: importlib.import_module(n) for n in ("fem", "board", "cases", "hollow", "mesh2d")}
    finally:
        for p in RESEARCH_LIBS:
            if p in sys.path:
                sys.path.remove(p)
        for n in set(sys.modules) - before:
            if n in ("fem", "board", "cases", "hollow", "mesh2d", "stack_ext", "sheets", "cluster", "transient", "exact", "refine"):
                del sys.modules[n]


def _copy_into_core(m_ref):
    """!
    @brief Copy a research model (nodes, elements, conductivities, sources, faces) into a femcore.Model.
    @param m_ref A research fem.Model.
    @return femcore.Model.
    """
    m = fc.Model(m_ref.nodes, m_ref.elems)
    m.k = m_ref.k.copy()
    m.q = m_ref.q.copy()
    m.faces = [{k: (v.copy() if hasattr(v, "copy") else v) for k, v in f.items()} for f in m_ref.faces]
    return m


def test_port_matches_the_research_solver_on_the_research_cases():
    """!
    @brief On seven research boards (strong edge with and without a via, the turned square, the T, the hollow barrel open and filled with copper, Lee's plate with a flux
           face) the nodal temperatures of femcore equal the research solver's to 1e-9 relative, and the balance is 1 to 1e-9.
    @return None.
    """
    with research_modules() as r:
        cases, hollow = r["cases"], r["hollow"]
        boards = {"edge": cases.strong_edge(200, hf=0.4, hmax=1.0, n_gap=3), "edge_via": cases.strong_edge(200, hf=0.4, hmax=1.0, n_gap=3, via_dist=2.0),
                  "square": cases.square(200, hf=0.6, hmax=2.0, n_gap=3), "T": cases.t_outline(200, hf=0.8, hmax=2.5, n_gap=3),
                  "hollow_open": hollow.strong_board(200, [(7.0, 5.0)], hf=0.4, hmax=1.0, n_gap=3, core="open"),
                  "hollow_cu": hollow.strong_board(200, [(7.0, 5.0)], hf=0.4, hmax=1.0, n_gap=3, core="solid"),
                  "lee": cases.lee_plate("centre", hf=4.0, hmax=10.0)[0]}
        for name, b in boards.items():
            m_ref, _ = b.build()
            ref = m_ref.solve()
            got = _copy_into_core(m_ref).solve()
            both = ~np.isnan(ref["T"])
            assert (both == ~np.isnan(got["T"])).all(), name
            scale = np.abs(ref["T"][both]).max()
            assert np.abs(got["T"][both] - ref["T"][both]).max() < 1e-9 * scale, name
            assert abs(got["balance"] - 1.0) < 1e-9, name
            assert got["n"] == ref["n"] and got["E"] == ref["E"]


def _stored_case(which, mod):
    """!
    @brief Build one of two small layered boards (graded node lines, orthotropic laminate, copper skins, a source patch, a via-rod region of higher kz, film arrays and an
           ambient of 25, a prescribed flux on one wall) on any solver module with the Model API.
    @param which 1 or 2.
    @param mod Module providing `Model` (femcore or the research fem) and, through femcore, the mesh helpers.
    @return Model.
    """
    if which == 1:
        xn, yn, dz, qv = [0, 1e-3, 2.5e-3, 5e-3, 8e-3], [0, 2e-3, 3e-3, 6e-3], [35e-6, 0.3e-3, 0.5e-3, 0.3e-3, 35e-6], 3e8
    else:
        xn, yn, dz, qv = np.linspace(0, 6e-3, 7), np.linspace(0, 4e-3, 5), [35e-6, 0.4e-3, 0.4e-3, 35e-6], 1.5e8
    zn = np.concatenate([[0], np.cumsum(dz)])
    nodes, elems = fc.structured_mesh(xn, yn, zn)
    nx, ny, nz = len(xn) - 1, len(yn) - 1, len(zn) - 1
    m = mod.Model(nodes, elems)
    k = np.ones((nz, ny, nx, 3))
    for s in range(nz):
        k[s] = 385.0 if s in (0, nz - 1) else np.array([0.9, 0.9, 0.3])
    k[1:nz - 1, 1, 1:3, 2] = 200.0                              # a rod region with a higher through-thickness conductivity
    m.k[:] = k.reshape(-1, 3)
    q = np.zeros((nz, ny, nx))
    q[0, 1:, 1:3] = qv
    m.q[:] = q.reshape(-1)
    cells = (nx, ny, nz)
    for side, h in (("top", 12.0), ("bottom", np.linspace(50, 150, nx * ny).reshape(-1)), ("xmax", 300.0)):
        fn, _ = fc.structured_face(elems, cells, side)
        m.add_faces(fn, h=h, t_amb=25.0)
    fn, _ = fc.structured_face(elems, cells, "xmin")
    m.add_faces(fn, flux=500.0)
    return m


# reference numbers printed by the research solver (research/independent-fem-edge/lib/fem.py) on the same meshes, copied here so that the test runs without the research folder
STORED = {1: {"max": 49.06442747244862, "min": 43.593779872479715, "mean": 47.213453920842376, "n": 120},
          2: {"max": 34.69290262385773, "min": 32.56867974951201, "mean": 34.139052660375974, "n": 175}}


@pytest.mark.parametrize("which", [1, 2])
def test_port_reproduces_stored_research_numbers(which):
    """!
    @brief femcore reproduces the maximum, minimum and mean temperature that the research solver printed on two structured boards, to 1e-9 relative.
    @param which Which stored board.
    @return None.
    """
    r = _stored_case(which, fc).solve()
    ref = STORED[which]
    T = r["T"]
    assert r["n"] == ref["n"]
    for key, val in (("max", np.nanmax(T)), ("min", np.nanmin(T)), ("mean", np.nanmean(T))):
        assert abs(val - ref[key]) < 1e-9 * abs(ref[key]), (key, val, ref[key])
    assert abs(r["balance"] - 1.0) < 1e-9


def test_the_stored_boards_agree_with_the_live_research_solver():
    """!
    @brief The same two structured boards on the live research solver equal femcore nodal by nodal to 1e-9 (guards the stored numbers).
    @return None.
    """
    with research_modules() as r:
        for which in (1, 2):
            a = _stored_case(which, r["fem"]).solve()["T"]
            b = _stored_case(which, fc).solve()["T"]
            assert np.abs(a - b).max() < 1e-9 * np.abs(a).max()


def test_one_dimensional_column_with_films_matches_the_closed_form():
    """!
    @brief Copper, laminate and copper stack with a source in the top copper and films on both faces: every interface temperature equals the series closed form to 1e-9
           (linear elements are nodally exact in 1D) and the film heats are the closed form's.
    @return None.
    """
    t = [35e-6, 0.3e-3, 0.5e-3, 0.3e-3, 35e-6]
    kk = [385.0, 0.3, 0.3, 0.3, 385.0]
    q_area = 1000.0
    zn = np.concatenate([[0], np.cumsum(t)])
    m = fc.structured_model(np.linspace(0, 1e-3, 3), np.linspace(0, 1e-3, 3), zn, k=np.array(kk)[:, None, None] * np.ones((5, 2, 2)), q=np.where(np.arange(5) == 0, q_area / t[0], 0.0)[:, None, None] * np.ones((5, 2, 2)),
                            films={"bottom": 10.0, "top": 200.0})   # z grows downwards in the closed form, so its "top" face is the lowest z
    r = m.solve()
    ref = ex.series_stack(t, kk, 10.0, 200.0, q_area)
    nxy = 9
    for s in range(zn.size):
        assert abs(r["T"][s * nxy] - ref["T"][s]) < 1e-9 * abs(ref["T"][s]), s
    assert abs(r["T"][0] * 10.0 - ref["q_up"]) < 1e-9 * ref["q_up"]
    assert abs(r["T"][-1] * 200.0 - ref["q_down"]) < 1e-9 * ref["q_down"]
    assert abs(r["balance"] - 1.0) < 1e-9


def test_slab_with_uniform_source_and_robin_ends_matches_the_closed_form():
    """!
    @brief A bar with a uniform source, Robin films on its two ends and insulated sides (the plate with a Robin edge, 1D) equals the parabola to 1e-9.
    @return None.
    """
    L, k, qv, h = 10e-3, 20.0, 2e7, 80.0
    xn = np.linspace(-L / 2, L / 2, 21)
    m = fc.structured_model(xn, [0, 1e-3], [0, 1e-3], k=k, q=qv, films={"xmin": h, "xmax": h})
    r = m.solve()
    T = r["T"].reshape(2, 2, xn.size)[0, 0]
    ref = ex.slab_with_source(xn, L, k, qv, h)
    assert np.abs(T - ref).max() < 1e-9 * ref.max()
    assert abs(r["balance"] - 1.0) < 1e-9


def _annulus(n_theta, r_in, r_out, n_r, height, k, h_in, h_out, t_in):
    """!
    @brief A ring of mapped bricks (a hollow cylinder of height `height`, one element through it) with films on the inner and outer cylinders.
    @param n_theta Elements around the circumference.
    @param r_in Inner radius in m.
    @param r_out Outer radius in m.
    @param n_r Elements across the wall (logarithmic spacing).
    @param height Axial height in m.
    @param k Conductivity in W/mK.
    @param h_in Inner film in W/m2K.
    @param h_out Outer film in W/m2K.
    @param t_in Ambient inside in K (outside 0).
    @return Tuple (Model, outer face nodes, inner face nodes).
    """
    rr = np.geomspace(r_in, r_out, n_r + 1)
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    nid = lambda j, a, z: z * (n_r + 1) * n_theta + (a % n_theta) * (n_r + 1) + j     # noqa: E731
    nodes = np.array([[rr[j] * np.cos(th[a]), rr[j] * np.sin(th[a]), z * height] for z in (0, 1) for a in range(n_theta) for j in range(n_r + 1)])
    elems, inner, outer = [], [], []
    for a in range(n_theta):
        for j in range(n_r):
            elems.append([nid(j, a, 0), nid(j + 1, a, 0), nid(j + 1, a + 1, 0), nid(j, a + 1, 0), nid(j, a, 1), nid(j + 1, a, 1), nid(j + 1, a + 1, 1), nid(j, a + 1, 1)])
        inner.append([nid(0, a, 0), nid(0, a + 1, 0), nid(0, a + 1, 1), nid(0, a, 1)])
        outer.append([nid(n_r, a, 0), nid(n_r, a + 1, 0), nid(n_r, a + 1, 1), nid(n_r, a, 1)])
    m = fc.Model(nodes, elems)
    m.k[:] = k
    m.add_faces(inner, h=h_in, t_amb=t_in)
    m.add_faces(outer, h=h_out, t_amb=0.0)
    return m, np.array(outer), np.array(inner)


def test_hollow_barrel_matches_the_radial_closed_form_and_converges_at_second_order():
    """!
    @brief A 25 um-class plated wall (copper) between an inner and an outer film, the radial closed form: the heat per metre agrees within the chord error of the polygon
           (under 0.1 % at 48 sectors) and the error falls by about four when the sectors double.
    @return None.
    """
    r_in, r_out, k, h_in, h_out, t_in, height = 0.125e-3, 0.15e-3, 385.0, 2.0e4, 1.0e4, 100.0, 1e-3
    errs = []
    for n_theta in (12, 24, 48):
        m, outer, inner = _annulus(n_theta, r_in, r_out, 3, height, k, h_in, h_out, t_in)
        r = m.solve()
        q_out = m.face_integral(r["T"], outer)[0] * h_out
        # no source: the heat that enters through the inner film leaves through the outer one (the balance ratio is undefined with q_in = 0)
        q_inner = h_in * (t_in * m.face_integral(np.ones(m.nodes.shape[0]), inner)[1] - m.face_integral(r["T"], inner)[0])
        assert abs(q_inner - q_out) < 1e-9 * abs(q_out)
        q_ref, _, _ = ex.hollow_cylinder(r_in, r_out, k, h_in, h_out, t_in)
        errs.append(abs(q_out / height - q_ref) / q_ref)
    assert errs[2] < 1e-3
    assert errs[1] / errs[2] > 3.0 and errs[0] / errs[1] > 3.0


def test_energy_balance_holds_on_every_structured_case():
    """!
    @brief The heat leaving through the films equals the heat put in (sources and fluxes), to 1e-9, on the two stored boards and on a case with a non-zero ambient.
    @return None.
    """
    for which in (1, 2):
        assert abs(_stored_case(which, fc).solve()["balance"] - 1.0) < 1e-9


def test_direct_and_cg_amg_solutions_agree():
    """!
    @brief The direct solution and the conjugate-gradient solution with the pyamg preconditioner differ by less than 1e-8 relative on a 4000-unknown board.
    @return None.
    """
    pytest.importorskip("pyamg")
    xn = np.linspace(0, 20e-3, 21)
    zn = np.concatenate([[0], np.cumsum([35e-6, 0.4e-3, 0.4e-3, 0.4e-3, 35e-6])])
    k = np.ones((5, 20, 20, 3)) * np.array([0.9, 0.9, 0.3])
    k[0] = 385.0
    k[-1] = 385.0
    q = np.zeros((5, 20, 20))
    q[0, 8:12, 8:12] = 1e8
    m = fc.structured_model(xn, xn, zn, k=k, q=q, films={"top": 10.0, "bottom": 10.0, "xmax": 100.0})
    a = m.solve(force="direct")
    b = m.solve(force="cg")
    assert a["solver"] == "direct" and b["solver"] == "cg"
    assert np.nanmax(np.abs(a["T"] - b["T"])) < 1e-8 * np.nanmax(a["T"])
    assert abs(b["balance"] - 1.0) < 1e-8


def test_without_pyamg_a_small_mesh_solves_and_a_large_one_raises_a_clear_error(monkeypatch):
    """!
    @brief With pyamg made unimportable, `available()` is False, a small mesh still solves directly and the CG path raises FemUnavailable naming pyamg.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setitem(sys.modules, "pyamg", None)             # a None entry makes `import pyamg` raise ImportError
    assert fc.available() is False
    m = _stored_case(2, fc)
    assert m.solve()["solver"] == "direct"
    with pytest.raises(fc.FemUnavailable, match="pyamg"):
        m.solve(direct_max=10)
    with pytest.raises(fc.FemUnavailable):
        m.solve(force="cg")


def test_structured_helpers_faces_volumes_and_rods():
    """!
    @brief The structured mesh has the right counts, the face areas and volumes add up, the rod mix is a parallel mix and a cancel callback stops the assembly.
    @return None.
    """
    xn, yn, zn = np.linspace(0, 4e-3, 5), np.linspace(0, 3e-3, 4), np.array([0, 1e-3, 3e-3])
    nodes, elems = fc.structured_mesh(xn, yn, zn)
    assert nodes.shape == (5 * 4 * 3, 3) and elems.shape == (4 * 3 * 2, 8)
    m = fc.Model(nodes, elems)
    assert abs(m.element_volumes().sum() - 4e-3 * 3e-3 * 3e-3) < 1e-18
    for side, area in (("top", 12e-6), ("bottom", 12e-6), ("xmin", 9e-6), ("xmax", 9e-6), ("ymin", 12e-6), ("ymax", 12e-6)):
        fn, _ = fc.structured_face(elems, (4, 3, 2), side)
        assert abs(m.face_integral(np.ones(nodes.shape[0]), fn)[1] - area) < 1e-15, side
    assert abs(fc.rod_conductivity(0.3, 385.0, 0.25) - (0.75 * 0.3 + 0.25 * 385.0)) < 1e-12
    with pytest.raises(ValueError):
        fc.rod_conductivity(0.3, 385.0, 1.5)
    with pytest.raises(ValueError):
        fc.structured_mesh([0, 1, 1], [0, 1], [0, 1])
    with pytest.raises(fc.FemCancelled):
        m.solve(cancel=lambda: True)
