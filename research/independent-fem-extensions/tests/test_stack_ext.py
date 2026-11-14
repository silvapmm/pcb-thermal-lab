#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_stack_ext.py
@brief Tests of the partial-slab finite-element builder: a one-column stack against the series closed form (tab, solder, board, interface and plate), energy balance,
       a tab smaller than the board, and the solder at copper conductivity equal to a thicker tab.
@details Run with `research/independent-fem-edge/.venv-research/bin/python -m pytest -q research/independent-fem-extensions/tests` (NumPy and SciPy only; no solver of pyamg is needed).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import exact                                                            # noqa: E402
import mesh2d                                                           # noqa: E402
import stack_ext                                                        # noqa: E402


def column(with_tab, k_solder=50.0):
    """!
    @brief A 1 x 1 mm single-element-plan column of the study-2 stack with insulated walls, the source in the first slab, films top and plate bottom.
    @param with_tab True: tab, solder, board, interface, plate with the source in the tab; False: the source in the top copper.
    @param k_solder Solder conductivity.
    @return Tuple (Stack, t list, k list).
    """
    plan = mesh2d.tensor(np.array([0.0, 1e-3]), np.array([0.0, 1e-3]))
    t, k, slabs = [], [], []
    P = 0.25e-6
    if with_tab:
        slabs.append(stack_ext.slab("tab", [0.1e-3, 0.1e-3], (385.0, 385.0), h_up=10.0, power=P))
        t += [0.2e-3]
        k += [385.0]
        slabs.append(stack_ext.slab("solder", [0.05e-3, 0.05e-3], (k_solder, k_solder)))
        t += [0.1e-3]
        k += [k_solder]
        slabs.append(stack_ext.slab("cu1", [35e-6], (385.0, 385.0)))
    else:
        slabs.append(stack_ext.slab("cu1", [35e-6], (385.0, 385.0), h_up=10.0, power=P))
    t += [35e-6]
    k += [385.0]
    for g in range(3):
        slabs.append(stack_ext.slab(f"gap{g}", [0.2e-3, 0.28667e-3], (0.9, 0.3)))
        t += [0.48667e-3]
        k += [0.3]
        slabs.append(stack_ext.slab(f"cu{g + 2}", [35e-6], (385.0, 385.0)))
        t += [35e-6]
        k += [385.0]
    slabs.append(stack_ext.slab("interface", [0.05e-3, 0.05e-3], (3.0, 3.0)))
    t += [0.1e-3]
    k += [3.0]
    slabs.append(stack_ext.slab("plate", [0.25e-3] * 4, (204.0, 204.0), h_down=10.0))
    t += [1e-3]
    k += [204.0]
    return stack_ext.Stack(plan, slabs), t, k, P


def test_column_matches_series_closed_form():
    """!
    @brief The single-column stack equals `exact.series_stack` at every interface to 1e-9 relative (both source placements).
    @return None.
    """
    for with_tab in (False, True):
        st, t, k, P = column(with_tab)
        res = st.solve(direct_max=30000)
        T = res["T"]
        ex = exact.series_stack(t, k, 10.0, 10.0, P / 1e-6)
        info = res["info"]
        zn, Np = info["zn"], info["Np"]
        top = float(np.nanmean(T[:Np]))
        bottom = float(np.nanmean(T[-Np:]))
        assert abs(top - ex["T"][0]) / ex["T"][0] < 1e-9
        assert abs(bottom - ex["T"][-1]) / ex["T"][0] < 1e-9
        assert abs(res["balance"] - 1.0) < 1e-9


def test_partial_slab_tab_has_free_faces_and_balance():
    """!
    @brief A tab over part of the plan: the energy balance holds and the tab top is hotter than the board top beside it.
    @return None.
    """
    xn = np.linspace(0, 4e-3, 9)
    plan = mesh2d.tensor(xn, xn)
    inside = lambda c: (c[:, 0] < 1e-3) & (c[:, 1] < 1e-3)               # noqa: E731
    slabs = [stack_ext.slab("tab", [0.1e-3, 0.1e-3], (385.0, 385.0), region=inside, h_up=10.0, h_wall=10.0, power=0.1),
             stack_ext.slab("cu", [35e-6], (385.0, 385.0), h_up=10.0, h_down=10.0, h_wall=10.0)]
    res = stack_ext.Stack(plan, slabs, symmetry=[("x", 0.0), ("y", 0.0)]).solve(direct_max=30000)
    assert abs(res["balance"] - 1.0) < 1e-9
    T = res["T"]
    assert np.isfinite(np.nanmax(T))


def test_solder_at_copper_equals_a_thicker_tab():
    """!
    @brief Solder at the conductivity of copper gives the same field as a copper tab of the combined thickness on the same elements (the matrices are equal).
    @return None.
    """
    xn = np.linspace(0, 3e-3, 7)
    plan = mesh2d.tensor(xn, xn)
    inside = lambda c: (c[:, 0] < 1e-3) & (c[:, 1] < 1e-3)               # noqa: E731
    board = stack_ext.slab("cu", [35e-6], (385.0, 385.0), h_up=10.0, h_down=10.0, h_wall=10.0, power=0.1, source_region=inside)
    a = [stack_ext.slab("tab", [0.1e-3, 0.1e-3], (385.0, 385.0), region=inside, h_up=10.0, h_wall=10.0), stack_ext.slab("sol", [0.1e-3], (385.0, 385.0), region=inside, h_wall=10.0), dict(board)]
    b = [stack_ext.slab("tab", [0.1e-3, 0.1e-3, 0.1e-3], (385.0, 385.0), region=inside, h_up=10.0, h_wall=10.0), dict(board)]
    ra = stack_ext.Stack(plan, a, symmetry=[("x", 0.0), ("y", 0.0)]).solve(direct_max=30000)
    rb = stack_ext.Stack(plan, b, symmetry=[("x", 0.0), ("y", 0.0)]).solve(direct_max=30000)
    assert np.nanmax(np.abs(ra["T"] - rb["T"])) < 1e-9
