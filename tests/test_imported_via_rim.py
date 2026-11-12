#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_imported_via_rim.py
@brief Tests of the rim test of the vias on imported copper (`viawell.RimMasks`, the ray test on the masks) with synthetic masks.
@details Run: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_imported_via_rim.py
"""

import numpy as np
import pytest

from pcbthermal import api, checks, copper, viawell
from pcbthermal.model import Problem

PIX_MM = 0.05          # pixel of the synthetic masks in mm
SIZE_MM = 10.0         # board side in mm
VIA = (5.0, 5.0)       # via centre in mm
DRILL = 0.3            # drill diameter in mm


def _disc_mask(kind):
    """!
    @brief Coverage mask of a 10 mm board around a via at its centre: a solid plane, a pad island in an antipad, or four spokes.
    @param kind "solid", "anti" (pad radius 0.25 mm, bare to 0.55 mm), "relief" (pad plus four 0.25 mm spokes), "empty" (no copper at all) or "pad" (only the 0.25 mm pad).
    @return uint8 array (rows from the top, columns), 255 where copper.
    """
    n = int(round(SIZE_MM / PIX_MM))
    c = (np.arange(n) + 0.5) * PIX_MM
    x, y = np.meshgrid(c, c)
    r = np.hypot(x - VIA[0], y - VIA[1])
    if kind == "solid":
        m = np.ones((n, n), bool)
    elif kind == "empty":
        m = np.zeros((n, n), bool)
    elif kind == "pad":
        m = r <= 0.25
    elif kind == "anti":
        m = (r <= 0.25) | (r >= 0.55)
    elif kind == "relief":
        spokes = (np.abs(x - VIA[0]) <= 0.125) | (np.abs(y - VIA[1]) <= 0.125)
        m = (r <= 0.25) | (r >= 0.55) | spokes
    else:
        raise ValueError(kind)
    return m.astype(np.uint8) * 255


def _problem(kinds, vias=True):
    """!
    @brief A 10 mm imported board with one via and a 3 mm part on layer 1.
    @param kinds Mask kind of every layer.
    @param vias False: no via.
    @return Problem.
    """
    p = Problem.new(SIZE_MM, SIZE_MM, layers=len(kinds), thickness_mm=1.6, copper_um=35.0, name="rim")
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", 10.0, 10.0, None
    p.imported = copper.imported_from_rasters([_disc_mask(k) for k in kinds], PIX_MM)
    if vias:
        p.add_via(VIA[0], VIA[1], diameter=DRILL)
    p.add_heater(1, 1.0, rect=(3.5, 3.5, 6.5, 6.5))
    return p


def _shares(p):
    """!
    @brief Rim shares of the first via of a problem as `viawell.build` reads them.
    @param p Problem.
    @return list of floats per layer.
    """
    masks = viawell.rim_masks(p)
    zi = viawell._zone_index(p, p.board.layers, masks)
    return viawell.rim_copper_shares(p, p.vias[0], p.board.layers, zi, masks)


def test_solid_plane_is_full_contact_and_a_pad_island_is_none():
    """!
    @brief A plane touching the barrel reads 1 on every ray; a pad island inside an antipad reads 0 (the drill circle alone would read 1 on both).
    @return None.
    """
    assert _shares(_problem(["solid", "solid"])) == [1.0, 1.0]
    assert _shares(_problem(["solid", "anti"])) == [1.0, 0.0]


def test_thermal_relief_reads_a_partial_share():
    """!
    @brief Four spokes through the clearance connect a part of the rim (between 0 and 1, about the share of the spokes).
    @return None.
    """
    s = _shares(_problem(["solid", "relief"]))[1]
    assert 0.1 < s < 0.7


def test_an_isolated_pad_and_a_missing_pad_are_uncoupled():
    """!
    @brief A layer whose copper is only the pad, or with no copper at the via, gives share 0 (the Allegro style set whose pads were removed); the heater of the layer still counts.
    @return None.
    """
    assert _shares(_problem(["solid", "pad"]))[1] == 0.0
    sh = _shares(_problem(["solid", "empty"]))
    assert sh[1] == 0.0
    p = _problem(["empty", "solid"])
    assert _shares(p)[0] == 1.0                                      # the part (layer 1) is over the via: contact as for a drawn board


def test_the_zones_of_an_imported_layer_are_ignored():
    """!
    @brief A zone drawn over an imported layer does not give the rim copper (the mask replaces it).
    @return None.
    """
    p = _problem(["solid", "anti"])
    p.add_zone(2, rect=(0, 0, 10, 10))
    assert _shares(p)[1] == 0.0


def test_a_drawn_board_has_no_masks_and_keeps_its_rule():
    """!
    @brief A problem without imported copper has no mask reader, and the shares are the zone rule's.
    @return None.
    """
    p = Problem.new(10.0, 10.0, 2, 1.6, 35.0)
    p.add_zone(1, rect=(0, 0, 10, 10))
    p.add_via(5.0, 5.0, 0.3)
    assert viawell.rim_masks(p) is None
    assert _shares(p) == [1.0, 0.0]


def test_hostile_masks_do_not_crash_the_rim_test():
    """!
    @brief An all-zero mask and a via outside the mask extent are read without an error.
    @return None.
    """
    p = _problem(["empty", "empty"])
    assert _shares(p)[1] == 0.0
    p.vias[0].x = -1.0e-3                                            # outside the board: clipped indices, no exception
    assert all(0.0 <= f <= 1.0 for f in _shares(p))


def test_the_antipad_removes_the_ghost_path_in_the_solution():
    """!
    @brief With the ray rule a via through an antipad joins the layer less: the part reads hotter than with the old full contact, and equals the solid case with no vias on that layer pair.
    @return None.
    """
    anti = _problem(["solid", "anti"])
    solid = _problem(["solid", "solid"])
    t_anti = api.simulate(anti, api.SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max
    t_solid = api.simulate(solid, api.SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max
    assert t_anti > t_solid                                          # the plane under the antipad no longer carries the barrel's heat away
    # and it is at most the board without any via
    novia = _problem(["solid", "anti"], vias=False)
    t_none = api.simulate(novia, api.SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max
    assert t_anti <= t_none + 1e-9


def test_full_contact_boards_do_not_move(monkeypatch):
    """!
    @brief Where the pad is on every layer and the plane touches the barrel (shares all 1), the field equals the old behaviour (every share 1), bit for bit.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _problem(["solid", "solid"])
    a = api.simulate(p, api.SolverOptions(models=("fvm", "fdm"), cell_mm=0.5))
    orig = viawell.rim_copper_shares
    monkeypatch.setattr(viawell, "rim_copper_shares", lambda problem, v, n, zi, masks=None: [1.0] * n)
    b = api.simulate(p, api.SolverOptions(models=("fvm", "fdm"), cell_mm=0.5))
    monkeypatch.setattr(viawell, "rim_copper_shares", orig)
    for m in ("fvm", "fdm"):
        assert a.results[m].t_max == b.results[m].t_max


def test_the_uncoupled_via_warning_follows_the_masks():
    """!
    @brief `checks.uncoupled_vias` lists the layer where the via sits in an antipad (it used to treat imported copper as full contact).
    @return None.
    """
    assert checks.uncoupled_vias(_problem(["solid", "solid"])) == []
    assert checks.uncoupled_vias(_problem(["solid", "anti"])) == [(0, [1])]


def test_conservation_with_the_masked_wells():
    """!
    @brief The heat balance of the solved field closes to rounding with a rim share below 1 (thermal relief) and with the antipad (share 0).
    @return None.
    """
    for kinds in (["solid", "relief"], ["solid", "anti"]):
        r = api.simulate(_problem(kinds), api.SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"]
        assert abs(r.balance_error) < 1e-9
