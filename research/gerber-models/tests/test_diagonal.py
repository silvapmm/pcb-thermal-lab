#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_diagonal.py
@brief The nine-point prototype (README 4.44): the cell tensor of uniform, axis-aligned and diagonal copper, the nine-point solver against the five-point one, and the effect on a 45-degree track.
"""

import numpy as np

import conduction as cd
import diagonal as dg
import scenarios as sc
import study_diagonal as sd
import study_track_width_angle as st


def test_cell_tensor_of_uniform_axis_aligned_and_diagonal_copper():
    """!
    @brief A uniform cell gives (S, S, 0); a horizontal strip gives kxx > kyy and no cross term wherever it lies in the cell; a diagonal line gives equal axial terms and a cross term of the right sign (opposite for the mirror image).
    @return None.
    """
    S = np.full((40, 40), cd.S_LAM)
    kx, ky, kxy = dg.cell_tensor(S, 10)
    assert abs(kx.mean() / cd.S_LAM - 1) < 1e-9 and abs(ky.mean() / cd.S_LAM - 1) < 1e-9 and np.abs(kxy).max() < 1e-9
    for row in (10, 14, 18):
        S = np.full((40, 40), cd.S_LAM)
        S[row:row + 2, :] = cd.S_CU
        kx, ky, kxy = dg.cell_tensor(S, 10)
        assert kx[1, 1] > 1.5 * ky[1, 1] and abs(kxy[1, 1]) < 1e-9 * cd.S_LAM
    S = np.full((40, 40), cd.S_LAM)
    for i in range(40):
        for w in range(-2, 3):
            if 0 <= i + w < 40:
                S[i, i + w] = cd.S_CU
    kx, ky, kxy = dg.cell_tensor(S, 10)
    assert abs(kx[1, 1] - ky[1, 1]) < 1e-9 * cd.S_LAM and kxy[1, 1] > 0.2 * cd.S_LAM
    _, _, kxy2 = dg.cell_tensor(S[:, ::-1].copy(), 10)
    assert kxy2[1, 2] < -0.2 * cd.S_LAM


def test_nine_point_solver_without_diagonals_is_the_five_point_one():
    """!
    @brief solve9 with zero diagonal faces gives the five-point solution of scenarios.solve_general.
    @return None.
    """
    rng = np.random.default_rng(3)
    S = cd.S_LAM * (1.0 + 5.0 * (rng.random((24, 24)) > 0.7))
    gx, gy = cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :])
    power, fixed, _ = sc.box_scenario(S.shape, 1.0, 6.0, border_mm=1.0)
    a = sc.solve_general(gx, gy, 1.0, power, 10.0, fixed)
    b = dg.solve9(*dg.faces5_as9(gx, gy), 1.0, power, 10.0, fixed)
    assert np.abs(a - b).max() < 1e-9


def test_diagonal_faces_recover_a_45_degree_track():
    """!
    @brief A 0.3 mm track at 45 degrees: the flow-based faces reproduce less than 60 % of its cooling, the hybrid with all the missing diagonal conduction more than 85 %, and at 0 degrees the hybrid does not change the flow-based result by more than 3 points.
    @return None.
    """
    St0 = np.full((int(st.SIZE / st.PIX_TRUTH),) * 2, cd.S_LAM)
    p_t, f_t, _ = sc.box_scenario(St0.shape, st.PIX_TRUTH, 6.0)
    ref_none = st.heater_mean(dg.pixel_reference9(St0, st.PIX_TRUTH, p_t, 10.0, f_t))
    S0 = np.full((int(st.SIZE / 0.1),) * 2, cd.S_LAM)
    p0, f0, h0 = sc.box_scenario(S0.shape, 0.1, 6.0)
    none = sd.coarse_runs(S0, 0.1, 10, p0, f0, h0)
    share = {}
    for th in (0, 45):
        layer = st.ng.Layer(st.track_text(0.3, th))
        _, ct = st.masks(layer, st.PIX_TRUTH)
        ref = st.heater_mean(dg.pixel_reference9(st.sheet(ct), st.PIX_TRUTH, p_t, 10.0, f_t))
        _, c01 = st.masks(layer, 0.1)
        runs = sd.coarse_runs(st.sheet(c01), 0.1, 10, p0, f0, h0)
        for m in ("flow-based faces", "flow + diagonal"):
            share[(m, th)] = 100 * (1 - runs[m] / none[m]) / (1 - ref / ref_none)
    assert share[("flow-based faces", 45)] < 60.0 and share[("flow + diagonal", 45)] > 85.0
    assert abs(share[("flow + diagonal", 0)] - share[("flow-based faces", 0)]) < 3.0
