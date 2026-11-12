#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_groups_lone_via.py
@brief A lone via far from a via array is not joined to it by the grouping of the Lumped and Analytic models (research/small-model-defects, INTEGRATION.md 1).

@details The single linkage joined two vias when their distance was at most twice the LARGER of their nearest-neighbour distances, so the wide ball of a far via reached the
         cluster: the via joined the group, its large distance entered the mean spacing of the group (the Wigner-Seitz cell of the cluster well) and the Lumped read the part
         0.65 to 1.26 K too hot with the FVM unchanged. The rule is now the SMALLER distance (each via reaches the other) and a via left alone has an infinite distance.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate, viaconstriction
from pcbthermal.model import Materials

PITCH = 1.0e-3


def lattice(n, pitch=PITCH, centre=(0.02, 0.02)):
    """!
    @brief The positions of an n x n array.
    @param n Vias per side.
    @param pitch Pitch in m.
    @param centre (x, y) centre of the array in m.
    @return numpy.ndarray (n * n, 2) in m.
    """
    h = (n - 1) / 2.0
    return np.array([(centre[0] + (i - h) * pitch, centre[1] + (j - h) * pitch) for i in range(n) for j in range(n)])


def groups_of(points):
    """!
    @brief Nearest-neighbour distances and groups of a set of points as the program computes them.
    @param points Array (n, 2) in m.
    @return tuple (d_nn, group).
    """
    d = viaconstriction.nearest_neighbour(points)
    return d, viaconstriction.via_groups(points, d)


def test_a_lone_far_via_is_not_joined_to_the_array():
    pts = np.vstack([lattice(3), [[0.032, 0.02]]])
    _, g = groups_of(pts)
    assert len(set(g[:9])) == 1                                     # the array is one group
    assert g[9] != g[0]                                             # the far via is its own group


def test_a_pair_and_a_lone_via_make_two_groups():
    pts = np.array([[0.0195, 0.02], [0.0205, 0.02], [0.030, 0.02]])
    _, g = groups_of(pts)
    assert g[0] == g[1] and g[2] != g[0]


def test_a_group_of_two_is_kept():
    pts = np.array([[0.0195, 0.02], [0.0205, 0.02]])
    _, g = groups_of(pts)
    assert g[0] == g[1]


def test_regular_arrays_and_a_via_two_pitches_off_stay_one_group():
    # The reach of the array (twice its pitch) still takes in a via at two pitches: only the far one is cut off
    pts = np.vstack([lattice(3), [[0.02 + 1.0 * PITCH + 2.0 * PITCH, 0.02]]])
    _, g = groups_of(pts)
    assert len(set(g)) == 1
    pts = np.vstack([lattice(5, 1.2e-3), [[0.02 + 2.4e-3 + 2.4e-3 + 1e-4, 0.02]]])
    _, g = groups_of(pts)
    assert g[-1] != g[0]                                            # a little beyond two pitches: not joined


def test_the_distance_of_a_via_left_alone_is_infinite_in_the_via_set():
    p = board([(32.0, 20.0)])
    vs = viaconstriction.ViaSet(p)
    assert np.isinf(vs.d_nn[9]) and np.all(np.isfinite(vs.d_nn[:9]))
    assert np.allclose(vs.d_nn[:9], PITCH)
    assert viaconstriction.median_nn(vs) == pytest.approx(PITCH)    # the lone via no longer enters the median spacing


def board(extra_vias):
    """!
    @brief A 40 x 40 mm four-layer board with a 10 mm part on the top layer, a 3 x 3 array at 1 mm pitch under it and optional extra vias.
    @param extra_vias List of (x, y) in mm.
    @return Problem.
    """
    p = Problem.new(40.0, 40.0, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, 40, 40))
    p.add_heater(1, 3.0, rect=(15, 15, 25, 25))
    for x, y in lattice(3) * 1e3:
        p.add_via(x, y, 0.3)
    for x, y in extra_vias:
        p.add_via(x, y, 0.3)
    return p


def rise(p, model, cell=1.0):
    """!
    @brief Maximum temperature rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float rise over the ambient in K.
    """
    return float(simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient)


@pytest.mark.parametrize("cell", [1.0, 0.5])
def test_a_far_via_no_longer_heats_the_lumped_part(cell):
    base = rise(board([]), "lumped", cell)
    # The far via cools the board a little (it adds a conductor); before the fix the Lumped read it as a dilution of the cluster and the part got hotter
    assert rise(board([(32.0, 20.0)]), "lumped", cell) <= base + 0.05
    assert rise(board([(35.0, 22.0), (6.0, 30.0)]), "lumped", cell) <= base + 0.05


def test_the_fvm_does_not_see_the_far_via_either():
    base = rise(board([]), "fvm", 0.5)
    assert abs(rise(board([(32.0, 20.0)]), "fvm", 0.5) - base) < 0.1
