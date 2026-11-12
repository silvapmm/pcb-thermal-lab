#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_imported_edge_film_centroid.py
@brief The edge film in series on the IMPORTED layers of a board with an outline, with the distance measured from the centroid of the board part of each cut cell.
@details Evidence: research/imported-copper-edge-film (README, INTEGRATION.md) and docs/validation.md 39. Drawn layers keep the distance from the cell centre (their centroid film is a
         separate decision, docs/versions.md 'Planned'). Run: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_imported_edge_film_centroid.py
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, copper, fvm
from pcbthermal.geometry import cover_centroids, exact_coverage, signed_distance_to_outline

OUTLINE = [[0.4, 0.2], [11.8, 0.6], [11.6, 11.7], [0.3, 11.5]]          # A turned quadrilateral on a 12 mm board (mm)


def board(imported, h_side=200.0, n_px=240, outline=OUTLINE):
    """!
    @brief A 12 mm two-layer board with an outline, full copper on both layers (imported masks or drawn zones) and a 2 mm heater of 1 W at the centre.
    @param imported True for imported masks (0.05 mm pixels), False for drawn zones.
    @param h_side Edge coefficient in W/m2K.
    @param n_px Pixels per side of the masks.
    @param outline Outline vertices in mm.
    @return Problem.
    """
    p = Problem.new(12, 12, 2, h_side=h_side)
    p.add_heater(1, 1.0, rect=(5, 5, 7, 7), name="U")
    p.set_outline(outline)
    if imported:
        full = np.full((n_px, n_px), 255, np.uint8)
        p.imported = copper.imported_from_rasters([full, full], 12.0 / n_px, "faces")
    else:
        p.add_zone(1, rect=(0, 0, 12, 12))
        p.add_zone(2, rect=(0, 0, 12, 12))
    return p


def test_the_centroid_of_a_cut_cell_is_inside_its_board_part_and_the_strips_equal_one_pass():
    # A triangle cuts the cells it crosses; the centroid of a whole cell is its centre, and the strip-wise refinement equals the one-call refinement of the whole grid
    poly = np.array([[0.7e-3, 0.4e-3], [9.1e-3, 1.3e-3], [3.3e-3, 8.8e-3]])
    nx = ny = 10
    dx = 1e-3
    cut = np.ones((ny, nx), bool)
    cx, cy, share = cover_centroids(poly, nx, ny, dx, dx, cut, n=8, strip=3)
    cx1, cy1, share1 = cover_centroids(poly, nx, ny, dx, dx, cut, n=8, strip=64)
    assert np.allclose(cx, cx1, atol=1e-15) and np.allclose(cy, cy1, atol=1e-15) and np.allclose(share, share1, atol=1e-12)
    # the share is the exact cover to the sub-grid and the centroid lies inside the cell
    cover = exact_coverage(poly, nx, ny, dx, dx)
    assert np.allclose(share, cover, atol=1e-9)
    ii, jj = np.mgrid[0:ny, 0:nx]
    inside = share > 0
    assert (cx[inside] >= jj[inside] * dx - 1e-12).all() and (cx[inside] <= (jj[inside] + 1) * dx + 1e-12).all()
    assert (cy[inside] >= ii[inside] * dx - 1e-12).all() and (cy[inside] <= (ii[inside] + 1) * dx + 1e-12).all()
    whole = share == 1.0
    assert whole.any() and np.allclose(cx[whole], (jj[whole] + 0.5) * dx) and np.allclose(cy[whole], (ii[whole] + 0.5) * dx)
    # an unselected cell keeps its centre and a zero share
    none = np.zeros((ny, nx), bool)
    _, _, s0 = cover_centroids(poly, nx, ny, dx, dx, none)
    assert not s0.any()


def test_the_film_of_an_imported_cut_cell_uses_the_centroid_distance_and_a_drawn_one_the_centre():
    # Independent rebuild of g = H L / max(1 + H d / S, 0.25) from the arrays of the network
    for imported in (True, False):
        p = board(imported)
        nx = ny = 24
        net = fvm.Network(p, nx, ny)
        g0 = net.g_side.copy()                                           # (after the film)
        # edge conductance before the film: the program's own construction with the series term off
        raw = fvm.Network(p, nx, ny, cut_cells=False).g_side
        L = net._edge_lengths()
        H = np.zeros_like(raw)
        np.divide(raw, L[None], out=H, where=L[None] > 0)
        cells = np.argwhere(L > 0)
        r, c = cells[:, 0], cells[:, 1]
        d_centre = signed_distance_to_outline(p.board.outline, (c + 0.5) * net.dx, (r + 0.5) * net.dy)
        cx, cy, share = cover_centroids(p.board.outline, nx, ny, net.dx, net.dy, L > 0)
        d_cent = np.maximum(signed_distance_to_outline(p.board.outline, cx[r, c], cy[r, c]), 0.0)
        sp_ = net._physical_sheet()
        for layer in range(p.board.layers):
            d = d_cent if imported else d_centre
            with np.errstate(divide="ignore", invalid="ignore"):
                fac = np.where(sp_[layer, r, c] > 0, 1.0 + H[layer, r, c] * d / sp_[layer, r, c], 1.0)
            fac = np.where(H[layer, r, c] > 0, np.maximum(fac, fvm.EDGE_FILM_FLOOR), 1.0)
            want = np.where(H[layer, r, c] > 0, H[layer, r, c] * L[r, c] / fac, raw[layer, r, c])
            assert g0[layer, r, c] == pytest.approx(want, rel=1e-12)
    # the centroid distance is never negative and differs from the centre's somewhere (a cut cell whose centre is off the board)
    assert (d_cent >= 0).all() and not np.allclose(d_cent, np.maximum(d_centre, 0.0))


def test_a_whole_cell_film_is_unchanged_and_the_centroid_never_stiffens_the_film():
    # Cells whole to the outline have the centroid at the centre; for a cut cell with the centre off the board the centre gave a NEGATIVE d (a stiffer film), the centroid gives d >= 0
    p = board(True)
    net = fvm.Network(p, 24, 24)
    raw = fvm.Network(p, 24, 24, cut_cells=False).g_side
    assert (net.g_side <= raw * (1.0 + 1e-12) / fvm.EDGE_FILM_FLOOR + 1e-300).all()      # at most 4 times stiffer (the floor)
    # with d >= 0 and a floor of 0.25 the imported film never exceeds the film alone: g <= H L
    assert (net.g_side <= raw * (1.0 + 1e-12)).all()


@pytest.mark.parametrize("h_side", [10.0, 200.0, 2000.0, 1e4, 1e5])
def test_a_constant_field_is_exact_with_the_centroid_film(h_side):
    p = board(True, h_side=h_side)
    p.board.ambient = 63.0
    p.heaters.clear()
    net = fvm.Network(p, 24, 24)
    rows = np.asarray(net.K.sum(axis=1)).ravel()
    assert rows == pytest.approx(net.g_amb.ravel(), rel=1e-9, abs=1e-9 * net.g_amb.max())
    assert fvm.solve_steady(p, cell_mm=0.5).t_max == pytest.approx(63.0, abs=1e-9)


def test_conservation_symmetry_and_the_maximum_principle():
    p = board(True)
    r = fvm.solve_steady(p, cell_mm=0.5)
    assert abs(r.balance_error) < 1e-12
    net = fvm.Network(p, 24, 24)
    K = net.K.tocsr()
    assert abs(K - K.T).max() < 1e-12 * abs(K).max()
    off = K.copy()
    off.setdiag(0)
    off.eliminate_zeros()
    assert off.max() <= 0.0                                                # no positive off-diagonal entry: the maximum principle (no vias)


def inset_board(h_side=200.0, inset_mm=1.2, n_px=240):
    """!
    @brief The turned 12 mm board with imported full copper held `inset_mm` inside the outline (the case of research/imported-copper-edge-film: the edge is a band of bare laminate).
    @param h_side Edge coefficient in W/m2K.
    @param inset_mm Distance of the copper from the outline in mm.
    @param n_px Pixels per side.
    @return Problem.
    """
    p = board(False, h_side=h_side)
    p.zones.clear()
    c = (np.arange(n_px) + 0.5) * 12e-3 / n_px
    X, Y = np.meshgrid(c, c)
    d = signed_distance_to_outline(p.board.outline, X.ravel(), Y.ravel()).reshape(n_px, n_px)
    m = np.where(d >= inset_mm * 1e-3, 255, 0).astype(np.uint8)[::-1]                # rows of a mask run from the top
    p.imported = copper.imported_from_rasters([m, m], 12.0 / n_px, "faces")
    return p


def mean_rise(p, cell):
    """!
    @brief Mean rise of the heater cells of the first heater (K).
    @param p Problem.
    @param cell Cell in mm.
    @return float.
    """
    n = int(round(12.0 / cell))
    net = fvm.Network(p, n, n)
    res = fvm.solve_steady(p, cell_mm=cell)
    T = res.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - res.ambient)).sum() / w.sum())


def test_the_centroid_film_raises_the_cool_edge_bias_of_imported_copper_held_inside_the_outline(monkeypatch):
    # Copper 1.2 mm inside the wall, 200 W/m2K, 1 mm: the film on the node read 107.85 K (the research: 1.6 to 3 % cool against a 3D truth); the centroid film 110.75 K, the 2 % of
    # the layered idealisation (n = 4 sub-gaps, below the 3D laminate) put back. Values of this board, pinned as a regression of the change.
    new = mean_rise(inset_board(), 1.0)
    monkeypatch.setattr(fvm.Network, "_cut_edge_film", lambda self, g0: g0)        # the film on the node of the earlier treatment
    old = mean_rise(inset_board(), 1.0)
    assert new == pytest.approx(110.749, abs=0.01) and old == pytest.approx(107.851, abs=0.01)
    assert new > old * 1.0 and (new - old) / old > 0.02
    # at 10 W/m2K the film hardly matters (the research: 0.05 points)
    a = mean_rise(inset_board(h_side=10.0), 1.0)
    monkeypatch.undo()
    b = mean_rise(inset_board(h_side=10.0), 1.0)
    assert abs(a / b - 1.0) < 0.005


def test_a_drawn_board_is_bit_identical_to_the_centre_distance_film(monkeypatch):
    # Scope: only imported layers get the centroid. A drawn board must not call the centroid at all
    called = []
    real = fvm.cover_centroids
    monkeypatch.setattr(fvm, "cover_centroids", lambda *a, **k: called.append(1) or real(*a, **k))
    fvm.solve_steady(board(False), cell_mm=1.0)
    assert not called
    fvm.solve_steady(board(True), cell_mm=1.0)
    assert called


def test_a_rectangle_with_imported_copper_is_unchanged():
    # No outline: the film of the border cells (half a cell) is the same as before for drawn and imported layers
    p = Problem.new(10, 10, 2, h_side=200.0)
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6), name="U")
    stripes = np.zeros((40, 40), np.uint8)
    stripes[::6] = 1
    p.imported = copper.imported_from_rasters([stripes, np.ones((40, 40), np.uint8)], 0.25, "faces")
    net = fvm.Network(p, 20, 20)
    assert net.cut_edge and not net.cut_links
    assert fvm.solve_steady(p, cell_mm=0.5).balance_error == pytest.approx(0.0, abs=1e-12)


def test_the_film_on_a_big_outline_board_costs_a_fraction_of_a_second():
    import time
    p = Problem.new(200, 150, 2, h_side=50.0)
    p.set_outline([[5, 0], [195, 10], [200, 140], [100, 150], [0, 120]])
    p.imported = copper.imported_from_rasters([np.ones((150, 200), np.uint8)] * 2, 1.0, "faces")
    net = fvm.Network(p, 200, 150, assemble=False)
    t = time.time()
    net._cut_edge_film(net.g_side)
    assert time.time() - t < 2.0
    assert math.isfinite(float(net.g_side.sum()))


def test_a_laminate_node_takes_the_centroid_only_next_to_an_imported_layer():
    # A four-layer board with the outer layers imported and the two inner layers drawn (review of fix/imported-copper-edge-film-centroid): the laminate nodes of the rule in
    # the gaps 1-2 and 3-4 lie next to an imported layer and take the centroid distance; those of the gap 2-3 lie between two drawn layers and keep the cell-centre distance
    p = Problem.new(12, 12, 4, h_side=200.0)
    p.add_heater(1, 1.0, rect=(5, 5, 7, 7), name="U")
    p.set_outline(OUTLINE)
    n_px = 240
    c = (np.arange(n_px) + 0.5) * 12e-3 / n_px
    X, Y = np.meshgrid(c, c)
    d = signed_distance_to_outline(p.board.outline, X.ravel(), Y.ravel()).reshape(n_px, n_px)
    m = np.where(d >= 1.2e-3, 255, 0).astype(np.uint8)[::-1]                    # copper held 1.2 mm inside, so every gap has laminate nodes along the edge
    p.imported = copper.imported_from_rasters([m, m, m, m], 12.0 / n_px, "faces")
    p.imported.layers = [e for e in p.imported.layers if e["index"] in (0, 3)]
    inner = OUTLINE
    p.add_zone(2, polygon=inner)
    p.add_zone(3, polygon=inner)
    nx = ny = 24
    net = fvm.Network(p, nx, ny)
    assert len(net.laminate_neighbours) == net.nl - 4 and set(net.laminate_neighbours) == {(0, 1), (1, 2), (2, 3)}
    raw = fvm.Network(p, nx, ny, cut_cells=False).g_side
    L = net._edge_lengths()
    cells = np.argwhere(L > 0)
    r, cc = cells[:, 0], cells[:, 1]
    d_centre = signed_distance_to_outline(p.board.outline, (cc + 0.5) * net.dx, (r + 0.5) * net.dy)
    cx, cy, _ = cover_centroids(p.board.outline, nx, ny, net.dx, net.dy, L > 0)
    d_cent = np.maximum(signed_distance_to_outline(p.board.outline, cx[r, cc], cy[r, cc]), 0.0)
    sp_ = net._physical_sheet()
    seen = set()
    for j, sides in enumerate(net.laminate_neighbours):
        k = 4 + j
        H = np.zeros(len(r))
        np.divide(raw[k, r, cc], L[r, cc], out=H, where=L[r, cc] > 0)
        dist = d_cent if sides != (1, 2) else d_centre
        with np.errstate(divide="ignore", invalid="ignore"):
            fac = np.where(sp_[k, r, cc] > 0, 1.0 + H * dist / sp_[k, r, cc], 1.0)
        fac = np.where(H > 0, np.maximum(fac, fvm.EDGE_FILM_FLOOR), 1.0)
        want = np.where(H > 0, H * L[r, cc] / fac, raw[k, r, cc])
        assert net.g_side[k, r, cc] == pytest.approx(want, rel=1e-12)
        if (H > 0).any():
            seen.add(sides)
    assert seen == {(0, 1), (1, 2), (2, 3)}
    # the two distances differ on these cells, so the test tells the rules apart
    assert not np.allclose(d_cent, np.maximum(d_centre, 0.0))
