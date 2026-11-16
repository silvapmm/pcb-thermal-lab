#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sheets.py
@brief Single-slab sheets (a copper pattern in one 35 um slab) as finite-element models for the closed-form checks of study 3: parallel and series stripes, a checkerboard.
@details The sheet is one layer of hexahedra over a plan mesh. A quad whose centroid is in the pattern has the copper conductivity, the others the in-plane laminate
         conductivity, with the same slab thickness for both (so the sheets are `k t` of each material and the closed forms are exact). The faces x = 0 and x = L are held at 1 K and 0 K by stiff films; every other lateral face and both faces are insulated.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import fem                                                              # noqa: E402
import mesh2d                                                           # noqa: E402


def conductance(xn, yn, in_pattern, k1=385.0, k2=0.9, t=35e-6):
    """!
    @brief Thermal conductance between the faces x = 0 and x = L of a patterned sheet.
    @param xn Plan nodes in x, m (from 0).
    @param yn Plan nodes in y, m.
    @param in_pattern Callable(centroids (Q, 2)) -> bool, True where the sheet has conductivity `k1`.
    @param k1 Conductivity inside the pattern, W/mK.
    @param k2 Conductivity outside, W/mK.
    @param t Sheet thickness, m.
    @return float W/K (heat reaching the face x = L for 1 K between the faces).
    """
    plan = mesh2d.tensor(xn, yn)
    nodes = np.column_stack([np.tile(plan.xy, (2, 1)), np.repeat([0.0, t], plan.xy.shape[0])])
    Np = plan.xy.shape[0]
    elems = np.concatenate([plan.quads, plan.quads + Np], axis=1)
    m = fem.Model(nodes, elems)
    c = plan.centroids()
    k = np.where(in_pattern(c), k1, k2)
    m.k[:, 0] = k
    m.k[:, 1] = k
    m.k[:, 2] = k
    edges, owner = plan.boundary_edges()
    mid = plan.xy[edges].mean(axis=1)
    left = edges[np.abs(mid[:, 0] - xn[0]) < 1e-12]
    right = edges[np.abs(mid[:, 0] - xn[-1]) < 1e-12]
    fl = np.column_stack([left[:, 0], left[:, 1], left[:, 1] + Np, left[:, 0] + Np])
    fr = np.column_stack([right[:, 0], right[:, 1], right[:, 1] + Np, right[:, 0] + Np])
    h = 1e10                                                            # stiff films: T = 1 K on the face x = 0 and 0 K on x = L (the error P / (h A) is below 1e-6 of a kelvin)
    m.add_faces(fl, h=h, t_amb=1.0)
    m.add_faces(fr, h=h, t_amb=0.0)
    r = m.solve(direct_max=30000)
    tot, area = m.face_integral(r["T"], fr)
    return h * tot                                                      # heat reaching the cold face, W, for a 1 K difference
