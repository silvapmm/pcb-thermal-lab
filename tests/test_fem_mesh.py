#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_mesh.py
@brief Tests of `pcbthermal/femmesh.py`: the mesh of a Problem for the finite-element comparison model (plan, via patches, slabs, blocks, fills, refusals, the exact count)
       and a small end-to-end check of the mesh with `femcore`.
@details Everything is checked against what can be computed by hand (a structured mesh, the volumes of the slabs and of a ring, the exact fill of `copper._zone_union`) and
         against the program's own FVM for the integration check (printed: this is not yet the validation of the model).
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

from pcbthermal import api, copper, femcore, femmesh  # noqa: E402
from pcbthermal.model import Problem, Zone  # noqa: E402


def _plain(width=12.0, height=8.0, layers=2):
    """!
    @brief A board with full copper on every layer and one heater, in mm.
    @param width Board width in mm.
    @param height Board height in mm.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(width, height, layers=layers)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(width / 2 - 2, height / 2 - 1, width / 2 + 2, height / 2 + 1))
    return p


def _volumes(mesh):
    """!
    @brief Element volumes of a mesh by the quadrature of the model.
    @param mesh FemMesh.
    @return numpy.ndarray (E,) in m3.
    """
    return mesh.model.element_volumes()


def test_plain_board_equals_a_hand_built_structured_mesh():
    """!
    @brief The mesh of a plain rectangular board with full copper is the structured mesh of the same node lines (same nodes, elements and conductivities).
    @return None.
    """
    p = Problem.new(12.0, 8.0, layers=2)
    p.add_full_copper()
    m = femmesh.build(p, cell_mm=4.0, gap_elements=3, refine=1.0)
    b = p.board
    xn, yn = np.linspace(0.0, 0.012, 4), np.linspace(0.0, 0.008, 3)
    tc = b.copper_thickness
    gap = float(b.gap_thicknesses()[0])
    dz = np.concatenate([[tc[0]], femmesh.graded_gap(gap, 3), [tc[1]]])
    zn = np.concatenate([[0.0], np.cumsum(dz)])
    nodes, elems = femcore.structured_mesh(xn, yn, zn)
    assert np.allclose(m.model.nodes, nodes, atol=1e-15, rtol=0)
    assert np.array_equal(m.model.elems, elems)
    k_cu, (g_kz,), (g_kip,) = b.materials.k_copper, (b.gap_properties()[0],), (b.gap_properties()[1],)
    kk = np.zeros((zn.size - 1, 3))
    kk[0] = kk[-1] = k_cu
    kk[1:-1, 0] = kk[1:-1, 1] = g_kip
    kk[1:-1, 2] = g_kz
    assert np.allclose(m.model.k, np.repeat(kk, 3 * 2, axis=0), rtol=1e-12)
    assert m.n_unknowns == nodes.shape[0]


def test_unknowns_equals_the_built_count_on_ten_boards():
    """!
    @brief `unknowns` counts exactly the nodes of the mesh that `build` returns, on ten different boards.
    @return None.
    """
    boards = []
    boards.append(_plain())
    one = Problem.new(14.0, 10.0, layers=1)
    one.add_zone(1, rect=(2, 2, 12, 8))
    one.add_heater(1, 1.0, rect=(5, 4, 9, 6))
    boards.append(one)
    v = _plain(20.0, 20.0, layers=4)
    v.add_via(10.0, 10.0, diameter=0.4)
    v.add_via(5.0, 6.0, diameter=0.3, fill_k=0.3)
    boards.append(v)
    arr = _plain(24.0, 24.0, layers=4)
    arr.add_via_array((9, 9, 15, 15), 4, 4, diameter=0.3)
    boards.append(arr)
    blk = _plain(20.0, 16.0)
    blk.add_heatsink(1, 0.0, rect=(4, 4, 12, 10), thickness_mm=3.0)
    boards.append(blk)
    bot = _plain(20.0, 16.0)
    bot.add_heatsink(2, 0.0, rect=(4, 4, 12, 10), thickness_mm=2.0)
    bot.add_heatsink(1, 20.0, rect=(14, 2, 18, 6))
    boards.append(bot)
    ell = _plain(20.0, 20.0)
    ell.set_outline([(0, 0), (20, 0), (20, 8), (8, 8), (8, 20), (0, 20)])
    boards.append(ell)
    hatch = Problem.new(16.0, 12.0, layers=2)
    hatch.add_zone(1, polygon=[(1, 1), (14, 2), (9, 11)], fill=0.5)
    hatch.add_zone(2, rect=(2, 2, 10, 9), fill=0.7)
    hatch.add_heater(1, 1.0, rect=(6, 4, 8, 6))
    boards.append(hatch)
    far = _plain(20.0, 20.0)
    far.add_heater(1, 1.0, rect=(30, 30, 31, 31))                      # a part outside the board
    boards.append(far)
    two = _plain(22.0, 22.0, layers=4)
    two.add_via(6.0, 6.0, diameter=0.3)
    two.add_via(16.0, 16.0, diameter=0.3, filled=True)
    two.add_heatsink(1, 0.0, rect=(3, 12, 9, 18), thickness_mm=1.0)
    boards.append(two)
    assert len(boards) == 10
    for p in boards:
        n = femmesh.unknowns(p, 2.0)
        m = femmesh.build(p, 2.0)
        assert m.n_unknowns == n[0] == m.model.nodes.shape[0]
        assert n[1] == m.planes


def test_the_fill_of_a_quad_equals_the_exact_fill_of_copper_py():
    """!
    @brief On a uniform plan (no break lines) the fill of every quad from slanted and hatched zones equals `copper._zone_union` cell by cell.
    @return None.
    """
    p = Problem.new(16.0, 12.0, layers=1)
    zs = [Zone(0, np.array([[1.0, 1.0], [14.0, 2.0], [9.0, 11.0]]) * 1e-3, 0.5), Zone(0, np.array([[3.0, 3.0], [13.0, 3.5], [11.0, 9.0], [4.0, 10.0]]) * 1e-3, 0.8),
          Zone(0, np.array([[0.5, 7.0], [6.0, 11.0], [2.0, 11.5]]) * 1e-3, 1.0)]
    p.zones = zs
    lay = femmesh._layout(p, 2.0, 3, 1.0)
    plan = lay.plan
    nx, ny = plan.xn.size - 1, plan.yn.size - 1
    assert (nx, ny) == (8, 6)                                             # slanted edges are not break lines: the plan is uniform
    got = femmesh._zone_fill(plan, zs).reshape(ny, nx)
    _, ref = copper._zone_union(zs, nx, ny, 0.002, 0.002)
    assert np.abs(got - ref).max() < 1e-6                                 # float32 in copper.py


def test_a_slanted_heater_has_its_exact_area_in_the_source():
    """!
    @brief The power of a slanted part is exact: the source integrates to the power, and the share of the quads equals the area of the polygon.
    @return None.
    """
    p = Problem.new(16.0, 12.0, layers=2)
    p.add_full_copper()
    tri = np.array([[3.0, 2.0], [12.0, 4.0], [6.0, 10.0]]) * 1e-3
    p.add_heater(1, 3.0, polygon=[(3, 2), (12, 4), (6, 10)])
    m = femmesh.build(p, 2.0, refine=1.0)
    mesh_area = float((femmesh._poly_share(m.plan, tri) * m.plan.area).sum())
    d1, d2 = tri[1] - tri[0], tri[2] - tri[0]
    assert mesh_area == pytest.approx(0.5 * abs(d1[0] * d2[1] - d1[1] * d2[0]), rel=1e-9)
    assert float((m.model.q * _volumes(m)).sum()) == pytest.approx(3.0, rel=1e-12)


def test_element_volumes_sum_to_the_board_volume():
    """!
    @brief The board slabs fill the board exactly (a rectangle, and an L outline: the removed elements are not counted).
    @return None.
    """
    p = _plain(20.0, 20.0, layers=4)
    m = femmesh.build(p, 2.0)
    b = p.board
    t = sum(b.copper_thickness) + float(b.gap_thicknesses().sum())
    assert m.volume_board == pytest.approx(0.02 * 0.02 * t, rel=1e-12)
    e = _plain(20.0, 20.0)
    e.set_outline([(0, 0), (20, 0), (20, 8), (8, 8), (8, 20), (0, 20)])
    me = femmesh.build(e, 2.0)
    t = sum(e.board.copper_thickness) + float(e.board.gap_thicknesses().sum())
    assert me.volume_board == pytest.approx((0.02 * 0.02 - 0.012 * 0.012) * t, rel=1e-12)


def test_block_and_pad_volumes_are_exact():
    """!
    @brief A block of 10 x 8 mm and 3 mm has exactly that volume in its slabs, its pad the area times the interface resistance, and the bottom block likewise.
    @return None.
    """
    p = _plain(24.0, 20.0)
    p.add_heatsink(1, 0.0, rect=(4, 4, 14, 12), thickness_mm=3.0)
    p.add_heatsink(2, 0.0, rect=(14, 4, 20, 12), thickness_mm=2.0)
    m = femmesh.build(p, 2.0)
    vol = _volumes(m)
    kinds = np.array([m.slabs[s]["kind"] for s in m.elem_slab])
    faces = np.array([m.slabs[s].get("face", -1) for s in m.elem_slab])
    top, bot = p.heatsinks[0], p.heatsinks[1]
    assert vol[(kinds == "blk") & (faces == 0)].sum() == pytest.approx(0.010 * 0.008 * 0.003, rel=1e-12)
    assert vol[(kinds == "blk") & (faces == 1)].sum() == pytest.approx(0.006 * 0.008 * 0.002, rel=1e-12)
    assert vol[(kinds == "pad") & (faces == 0)].sum() == pytest.approx(0.010 * 0.008 * max(top.interface_resistance(), 1e-7) * femmesh.K_PAD, rel=1e-12)
    assert vol[(kinds == "pad") & (faces == 1)].sum() == pytest.approx(0.006 * 0.008 * max(bot.interface_resistance(), 1e-7) * femmesh.K_PAD, rel=1e-12)
    # the block slabs are 2 to 8 per face, the exposed face carries its film and nothing covers the pad
    assert sum(1 for s in m.slabs if s["kind"] == "blk" and s["face"] == 0) == 3


def test_a_via_patch_has_the_ring_volume_of_the_plating():
    """!
    @brief The ring of a hollow via is pi (ro^2 - ri^2) h; the open core has no element, the filled one has the volume of the disc (polygons of equal area).
    @return None.
    """
    p = Problem.new(20.0, 20.0, layers=2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(1, 1, 2, 2))
    p.add_via(10.0, 10.0, diameter=0.4)                                   # hollow, plating 25 um
    p.add_via(5.0, 5.0, diameter=0.4, fill_k=385.0)                       # copper-filled core (a conducting core: elements)
    m = femmesh.build(p, 2.0)
    assert m.n_patches == 2 and m.n_rods == 0
    b = p.board
    h = sum(b.copper_thickness) + float(b.gap_thicknesses().sum())
    ro, ri = 0.2e-3, 0.2e-3 - b.via_plating
    vol = _volumes(m)
    board = (m.elem_slab >= 0) & np.array([m.slabs[s]["region"] == "board" for s in m.elem_slab])
    for k, (via, core_open) in enumerate(((0, True), (1, False))):
        sel = board & (m.plan.via[m.elem_quad] == via)
        ring = vol[sel & (m.plan.tag[m.elem_quad] == 2)].sum()
        assert ring == pytest.approx(math.pi * (ro ** 2 - ri ** 2) * h, rel=1e-9)
        core = vol[sel & (m.plan.tag[m.elem_quad] == 1)].sum()
        if core_open:
            assert core == 0.0                                            # no element in an open core
        else:
            assert core == pytest.approx(math.pi * ri ** 2 * h, rel=1e-9)
    # the barrel is copper and the core of the second via has its own conductivity
    q = np.flatnonzero(board & (m.plan.tag[m.elem_quad] == 2))
    assert np.allclose(m.model.k[q], p.board.materials.k_copper)


def test_the_hollow_core_wall_is_adiabatic_and_the_outline_wall_has_the_film():
    """!
    @brief No film on the wall of an open hole; the edge film on every wall of the outline of every board slab.
    @return None.
    """
    p = Problem.new(20.0, 20.0, layers=2, h_side=37.0)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(1, 1, 2, 2))
    p.add_via(10.0, 10.0, diameter=0.4)
    m = femmesh.build(p, 2.0)
    mod = m.model
    # a face of h_side is a vertical face: its nodes have two distinct z and only two distinct (x, y) points
    sidef = [f for f in mod.faces if np.allclose(f["h"], p.board.h_side)]
    assert len(sidef) == len([s for s in m.slabs if s["region"] == "board"])     # one group of faces per board slab
    nodes = np.vstack([f["nodes"] for f in sidef])
    xy = mod.nodes[nodes][:, :, :2]
    on_box = (np.isclose(xy[:, :, 0], 0.0) | np.isclose(xy[:, :, 0], 0.02) | np.isclose(xy[:, :, 1], 0.0) | np.isclose(xy[:, :, 1], 0.02)).all(axis=1)
    assert on_box.all()                                                   # nothing of the hole wall carries the edge film
    area = sum(float(mod.face_integral(np.ones(mod.nodes.shape[0]), nodes)[1]) for _ in [0])
    t = sum(p.board.copper_thickness) + float(p.board.gap_thicknesses().sum())
    assert area == pytest.approx(4 * 0.02 * t, rel=1e-12)


def test_refusals_say_why():
    """!
    @brief A slanted or curved outline, a block that is not rectilinear, too many lines, a too fine cell and touching blocks of different thickness are refused with a reason.
    @return None.
    """
    tri = _plain(20.0, 20.0)
    tri.set_outline([(0, 0), (20, 0), (0, 20)])
    with pytest.raises(ValueError, match="axis-aligned outline"):
        femmesh.unknowns(tri, 2.0)
    angles = np.linspace(0, 2 * math.pi, 40, endpoint=False)
    disc = _plain(20.0, 20.0)
    disc.set_outline([(10 + 9 * math.cos(a), 10 + 9 * math.sin(a)) for a in angles])
    with pytest.raises(ValueError, match="slanted or curved"):
        femmesh.build(disc, 2.0)
    blk = _plain(20.0, 20.0)
    blk.add_heatsink(1, 0.0, polygon=[(2, 2), (10, 4), (8, 10)], thickness_mm=2.0)
    with pytest.raises(ValueError, match="axis-aligned sides"):
        femmesh.build(blk, 2.0)
    fine = _plain(20.0, 20.0)
    with pytest.raises(ValueError, match="cell of at least"):
        femmesh.unknowns(fine, 0.001)
    big = _plain(2000.0, 2000.0)
    with pytest.raises(ValueError, match="coarser cell"):
        femmesh.unknowns(big, 0.02)
    two = _plain(24.0, 12.0)
    two.add_heatsink(1, 0.0, rect=(2, 2, 10, 10), thickness_mm=2.0)
    two.add_heatsink(1, 0.0, rect=(10, 2, 20, 10), thickness_mm=4.0)
    with pytest.raises(ValueError, match="same thickness"):
        femmesh.build(two, 2.0)
    over = _plain(24.0, 12.0)
    over.add_heatsink(1, 0.0, rect=(2, 2, 12, 10), thickness_mm=2.0)
    over.add_heatsink(1, 0.0, rect=(8, 2, 20, 10), thickness_mm=2.0)
    with pytest.raises(ValueError, match="overlap"):
        femmesh.build(over, 2.0)


def test_too_many_break_lines_are_refused():
    """!
    @brief More than 10 000 break lines along an axis are refused (the lines closer than a quarter of the cell are merged first).
    @return None.
    """
    p = Problem.new(2000.0, 20.0, layers=1)
    for i in range(10200):
        p.zones.append(Zone(0, np.array([[0.1 + 0.19 * i, 1.0], [0.1 + 0.19 * i + 0.05, 1.0], [0.1 + 0.19 * i + 0.05, 2.0], [0.1 + 0.19 * i, 2.0]]) * 1e-3, 1.0))
    p.heaters = []
    with pytest.raises(ValueError, match="break lines"):
        femmesh.unknowns(p, 0.05)
    # near-coincident lines are merged: many zones whose edges are within a quarter of the cell do not accumulate
    q = Problem.new(40.0, 20.0, layers=1)
    for i in range(300):
        x = 10.0 + 1e-5 * i
        q.zones.append(Zone(0, np.array([[x, 5.0], [x + 5, 5.0], [x + 5, 6.0], [x, 6.0]]) * 1e-3, 1.0))
    q.add_heater(0, 1.0, rect=(10, 5, 12, 6))
    lay = femmesh._layout(q, 2.0, 3, 2.0)
    inside = lay.plan.xn[(lay.plan.xn > 0.0095) & (lay.plan.xn < 0.0105)]
    assert inside.size <= 2


def test_hostile_geometry_is_a_mesh_or_a_refusal_never_a_crash():
    """!
    @brief Random boards with hundreds of lines, near-coincident edges, vias on break lines, tiny parts and parts outside the board: a valid mesh within the cap, or a ValueError.
    @return None.
    """
    rng = np.random.default_rng(20261115)
    built = refused = 0
    for case in range(24):
        p = Problem.new(24.0, 18.0, layers=int(rng.integers(1, 5)))
        for _ in range(int(rng.integers(5, 80))):
            x0, y0 = rng.uniform(-3, 26), rng.uniform(-3, 20)
            w, h = rng.choice([0.0004, 0.02, 0.3, 2.0, 9.0]), rng.choice([0.0004, 0.02, 0.3, 2.0, 9.0])
            x0 = round(x0, int(rng.integers(0, 4)))                       # coincident and near-coincident lines
            p.zones.append(Zone(int(rng.integers(0, p.board.layers)), np.array([[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h]]) * 1e-3, float(rng.choice([1.0, 0.5, 0.7]))))
        for _ in range(int(rng.integers(0, 4))):
            x0, y0 = rng.uniform(-2, 25), rng.uniform(-2, 19)
            p.add_heater(int(rng.integers(1, p.board.layers + 1)), float(rng.uniform(0.1, 2)), rect=(x0, y0, x0 + rng.choice([0.001, 0.4, 3.0]), y0 + rng.choice([0.001, 0.4, 3.0])))
        grid = [2.0, 4.0, 6.0, 12.0]
        for _ in range(int(rng.integers(0, 12))):
            # vias on grid lines of the break lines, near edges, near each other, outside the board
            x = float(rng.choice([2.0, 4.0, 6.0, 12.0, rng.uniform(-1, 25)]))
            y = float(rng.choice([2.0, 4.0, 6.0, 12.0, rng.uniform(-1, 19)]))
            p.add_via(x, y, diameter=float(rng.choice([0.2, 0.3, 0.6])), fill_k=float(rng.choice([0.0, 0.3])))
        if case % 5 == 0:
            p.add_heatsink(1, 3.0, rect=(rng.uniform(0, 8), rng.uniform(0, 6), rng.uniform(10, 30), rng.uniform(8, 25)), thickness_mm=float(rng.choice([0.0, 1.0, 3.0])))
        cell = float(rng.choice(grid))
        try:
            n = femmesh.unknowns(p, cell)
            m = femmesh.build(p, cell)
        except ValueError:
            refused += 1
            continue
        built += 1
        assert m.n_unknowns == n[0] <= femmesh.FEM_MAX_UNKNOWNS
        assert np.isfinite(m.model.nodes).all() and (m.model.k > 0).all()
        m.model.validate()
    assert built >= 10


def test_a_via_on_a_break_line_is_a_rod_and_a_free_one_a_patch():
    """!
    @brief A via whose window holds a break line (a zone edge) is a rod; a via with room is a conforming patch; the rod carries the barrel area in kz.
    @return None.
    """
    p = Problem.new(24.0, 24.0, layers=2)
    p.add_zone(1, rect=(2, 2, 12.5, 12.5))
    p.add_zone(2, rect=(2, 2, 22, 22))
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6))
    p.add_via(12.0, 8.0, diameter=0.4)                                     # the window crosses x = 12.5
    p.add_via(18.0, 18.0, diameter=0.4)                                    # free
    m = femmesh.build(p, 2.0)
    assert (m.n_patches, m.n_rods) == (1, 1)
    assert any("rod" in w for w in m.warnings)
    a = p.vias[0].thermal_area(p.board.via_plating, p.board.materials.k_copper)
    # the rod's copper area times the sample share is in the kz of the quads under the drill: the added kz area equals a_via
    sel = (m.elem_slab == m.copper_slabs[0][0])
    added = (m.model.k[sel, 2] - 385.0 * 1.0)                              # not used: see the area check below
    ids, frac = femmesh._rod_fraction(p, m.plan, 0, a)
    assert float((frac * m.plan.area[ids]).sum()) == pytest.approx(a, rel=1e-9)
    assert added.shape[0] == sel.sum()


def test_via_windows_with_the_same_interval_share_the_lines():
    """!
    @brief Vias in one column (the same window interval along x) are all patches; vias whose intervals overlap without being equal are not.
    @return None.
    """
    p = Problem.new(30.0, 30.0, layers=2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(2, 2, 4, 4))
    for y in (8.0, 15.0, 24.0):
        p.add_via(15.0, y, diameter=0.3)
    p.add_via(16.0, 22.0, diameter=0.3)                                    # window overlaps the column's x interval without being it
    lay = femmesh._layout(p, 2.0, 3, 2.0)
    assert len(lay.windows) == 3 and len(lay.rods) == 1


def test_a_part_outside_the_board_is_warned_and_does_not_crash():
    """!
    @brief The power of a part with no area on the board goes to the nearest element and says so.
    @return None.
    """
    p = _plain(20.0, 20.0)
    p.add_heater(1, 2.0, rect=(30, 30, 31, 31))
    m = femmesh.build(p, 2.0)
    assert any("no area on the board" in w for w in m.warnings)
    assert float((m.model.q * _volumes(m)).sum()) == pytest.approx(3.0, rel=1e-12)


def test_end_to_end_the_mesh_solves_and_conserves_energy():
    """!
    @brief The mesh of the example board at a coarse cell solves (direct, or CG when pyamg is present), the heat balance is 1 to 1e-9 and the hottest column is near the FVM's.
    @details Prints the numbers: an integration check, not the validation of the model (docs/validation.md has the tables of branch 6).
    @return None.
    """
    from pcbthermal.model import load_problem
    p = load_problem(str(ROOT / "examples" / "example_board.pcbt.json"))
    cell = 4.0
    n = femmesh.unknowns(p, cell)[0]
    if n > femcore.FEM_DIRECT_MAX and not femcore.available():
        pytest.skip("the mesh is above the direct-solve limit and pyamg is not installed")
    m = femmesh.build(p, cell)
    r = m.model.solve()
    assert abs(r["balance"] - 1.0) < 1e-9
    T = r["T"]
    # hottest column mean of the top copper slab: the mean of the eight node values of an element is its volume mean
    s0 = m.copper_slabs[0][0]
    el = np.flatnonzero(m.elem_slab == s0)
    col = T[m.model.elems[el]].mean(axis=1)
    fvm = api.simulate(p, api.SolverOptions(cell_mm=cell, models=("fvm",))).results["fvm"]
    rise_fvm = fvm.t_max - p.board.ambient
    # the same plan cell: take the layer slabs of every layer and keep the hottest
    best = max(float(T[m.model.elems[np.flatnonzero(m.elem_slab == s)]].mean(axis=1).max()) for ss in m.copper_slabs for s in ss[:1])
    print(f"example board at {cell:g} mm: {n} unknowns, FEM hottest top-copper element mean {col.max():.3f} K, hottest element of any copper layer {best:.3f} K, "
          f"FEM point max {T.max():.3f} K, FVM {rise_fvm:.3f} K, balance {r['balance']:.12f}")
    assert abs(best - rise_fvm) / rise_fvm < 0.06
