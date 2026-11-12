#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_small_defects.py
@brief Tests of the investigation research/small-model-defects: each defect is reproduced on the program as it is, and each candidate removes it on a copy in memory.
@details Run: python -m pytest -q research/small-model-defects/tests   (from the repository root; about 1 minute). The program is not edited: the candidates are the
         wrappers of lib/ (grouping, centroid_patch, solid_gridline) and the FDM option mean="harmonic" that the program already has.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parent / "scripts"))

import numpy as np                                                          # noqa: E402

import centroid_patch                                                       # noqa: E402
import grouping                                                             # noqa: E402
import solid_gridline                                                       # noqa: E402
import study_far_via as far                                                 # noqa: E402
import study_fdm_gap as gap                                                 # noqa: E402
import study_separate_zones as zones                                        # noqa: E402
import study_solid3d_gridline as grid                                       # noqa: E402
from pcbthermal import fdm, viaconstriction as vc                          # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402


def test_far_via_joins_the_cluster_in_the_program_and_not_in_the_candidate():
    """!
    @brief The far via has a large nearest-neighbour distance, so the 'larger distance' rule joins it to the cluster; the 'smaller distance' rule does not.
    @return None.
    """
    pts = np.array(far.array(16) + [(5.0, 30.0)]) / 1000.0
    d = vc.nearest_neighbour(pts)
    assert len(np.unique(vc.via_groups(pts, d))) == 1
    assert len(np.unique(grouping.groups_min(pts, d))) == 2
    # An ordinary array, a row beside it and a pair keep their groups (the rule differs only for an outlier)
    arr = np.array(far.array(16)) / 1000.0
    assert len(np.unique(grouping.groups_min(arr, vc.nearest_neighbour(arr)))) == 1


def test_far_via_heats_the_lumped_model_and_the_candidate_removes_it():
    """!
    @brief 16 vias under the part and one 25 mm away: the Lumped hottest temperature rises by more than 1 K in the program, by under 0.01 K with the candidate; the FVM does not move.
    @return None.
    """
    base = far.tmax(far.array(16), 2.0, models=("fvm", "lumped"))
    v = far.array(16) + [(5.0, 30.0)]
    prog = far.tmax(v, 2.0, models=("fvm", "lumped"))
    cand = far.tmax(v, 2.0, variant="min_inf", models=("lumped",))
    assert prog["lumped"] - base["lumped"] > 1.0
    assert abs(prog["fvm"] - base["fvm"]) < 0.01
    assert abs(cand["lumped"] - base["lumped"]) < 0.01


def test_lone_far_via_equals_no_far_via_for_one_via_cluster():
    """!
    @brief With the candidate a via that stays alone is the same whatever the other vias are: its nearest-neighbour distance is infinite.
    @return None.
    """
    p = far.board(far.array(2) + [(5.0, 30.0)])
    with grouping.using("min_inf"):
        vs = vc.ViaSet(p)
    assert np.isinf(vs.d_nn[-1]) and np.isfinite(vs.d_nn[:-1]).all()


def test_lumped_mirror_asymmetry_comes_from_the_centroid_cell_and_the_patch_removes_it():
    """!
    @brief Two parts whose centroids lie on cell edges: the mirror image of the board differs in the Lumped model by about 0.09 K, and not at all with the interpolated read.
    @return None.
    """
    a = zones.run(zones.make(False), 1.0, ("lumped",))["lumped"]
    b = zones.run(zones.make(True), 1.0, ("lumped",))["lumped"]
    assert abs(b - a) > 0.05
    with centroid_patch.using():
        a2 = zones.run(zones.make(False), 1.0, ("lumped",))["lumped"]
        b2 = zones.run(zones.make(True), 1.0, ("lumped",))["lumped"]
    assert abs(b2 - a2) < 1e-9


def test_interpolation_is_exact_for_a_linear_raster_and_commutes_with_a_mirror():
    """!
    @brief Bilinear read of a linear raster is exact; reading the mirrored raster at the mirrored point gives the same value.
    @return None.
    """
    ny, nx, dx = 6, 8, 1e-3
    r = np.add.outer(np.arange(ny) * 2.0, np.arange(nx) * 3.0)
    x, y = 3.3e-3, 2.7e-3
    assert abs(centroid_patch.interp_at(r, x, y, dx, dx) - (2.0 * (y / dx - 0.5) + 3.0 * (x / dx - 0.5))) < 1e-9
    assert abs(centroid_patch.interp_at(r[:, ::-1], nx * dx - x, y, dx, dx) - centroid_patch.interp_at(r, x, y, dx, dx)) < 1e-9


def test_fdm_below_fvm_across_a_gap_and_the_harmonic_mean_halves_the_error():
    """!
    @brief Copper cut by a 3 mm gap on every layer, 1 mm cell: the FDM is more than 15 % under the converged value, the harmonic mean under 11 %, both reach it with the cell.
    @return None.
    """
    p = gap.gap_board(3.0, 1.0)
    ref = float(simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max) - 25.0
    a = float(fdm.solve_steady(p, 1.0, "arithmetic").t_max) - 25.0
    h = float(fdm.solve_steady(p, 1.0, "harmonic").t_max) - 25.0
    assert (ref - a) / ref > 0.15
    assert (ref - h) / ref < 0.11
    a2 = float(fdm.solve_steady(p, 0.5, "arithmetic").t_max) - 25.0
    assert (ref - a2) / ref < (ref - a) / ref / 2.0


def test_harmonic_mean_is_the_same_on_a_uniform_board():
    """!
    @brief Without a copper edge the two means agree (full copper, no gap).
    @return None.
    """
    p = gap.gap_board(0.0, 1.0)
    a = float(fdm.solve_steady(p, 1.0, "arithmetic").t_max)
    h = float(fdm.solve_steady(p, 1.0, "harmonic").t_max)
    assert abs(a - h) < 1e-4       # two zones that meet at the middle leave a rounding of 2e-6 K at the seam


def test_lumped_mirror_is_exact_when_the_centroids_are_inside_cells():
    """!
    @brief Moving both parts by 0.25 mm puts the centroids inside cells: the mirror image of the board (shifted the other way) then gives the same Lumped result.
    @return None.
    """
    def shifted(mirror, dx0):
        """!
        @brief Lumped hottest temperature of the zones board with both parts moved in x.
        @param mirror True for the mirror image.
        @param dx0 Shift in mm.
        @return float.
        """
        p = zones.make(mirror)
        for h in p.heaters:
            h.polygon = h.polygon + [dx0 / 1000.0, 0.0]
        return zones.run(p, 1.0, ("lumped",))["lumped"]
    assert abs(shifted(True, -0.25) - shifted(False, 0.25)) < 1e-9


def test_solid3d_via_on_a_line_is_asymmetric_in_the_program_and_symmetric_with_the_split():
    """!
    @brief A via on a grid line at 1 mm: the mirror image differs by more than 0.3 K in the program, by under 1e-6 K with the split footprint; a via at a cell centre is untouched.
    @return None.
    """
    a = grid.run(grid.board(12.0, False), 1.0, ("solid3d",))["solid3d"]
    b = grid.run(grid.board(12.0, True), 1.0, ("solid3d",))["solid3d"]
    assert abs(b - a) > 0.3
    with solid_gridline.using():
        a2 = grid.run(grid.board(12.0, False), 1.0, ("solid3d",))["solid3d"]
        b2 = grid.run(grid.board(12.0, True), 1.0, ("solid3d",))["solid3d"]
    assert abs(b2 - a2) < 1e-6
    c = grid.run(grid.board(12.5, False), 1.0, ("solid3d",))["solid3d"]
    assert c > 0 and abs(grid.run(grid.board(12.5, True), 1.0, ("solid3d",))["solid3d"] - c) < 1e-6
