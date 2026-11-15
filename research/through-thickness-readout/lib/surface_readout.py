#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file surface_readout.py
@brief Option A prototype: the temperature of a face of a thick layer from the node (the column mean) and the heat fluxes that enter through its two faces.
@details A layer of thickness t and conductivity k whose temperature varies slowly in the plane satisfies k T_zz = -k laplace(T) = -(laplace of the column mean) k. Integrating
         the heat balance of the column gives k t laplace(T_m) = -(q_top + q_bot), with q_top and q_bot the net heat flux ENTERING the layer through its top and bottom faces.
         With z downwards, T_z(0) = -q_top / k and T_z(t) = +q_bot / k, so T is a parabola:  T(z) = T_0 - q_top z / k + (q_top + q_bot) z^2 / (2 k t).
         Its mean over the thickness is T_m = T_0 - q_top t / (2 k) + (q_top + q_bot) t / (6 k), hence
             T_top    - T_m =  t (2 q_top - q_bot) / (6 k),
             T_bottom - T_m =  t (2 q_bot - q_top) / (6 k).
         A column fed at the top and cooled at the bottom (q_bot = -q_top = -q) gives the familiar q t / (2 k); heat that spreads sideways inside the layer (q_bot -> 0) gives q t / (3 k),
         two thirds of the column bound. The parabola is exact when the lateral variation is slow against t; under a small source it is an estimate (research README 3).
"""

import numpy as np


def offsets(t, k, q_top, q_bot):
    """!
    @brief Surface-minus-column-mean temperature of the two faces of a layer (parabolic profile).
    @param t Layer thickness in m.
    @param k Through-thickness conductivity of the layer in W/mK.
    @param q_top Net heat flux entering through the top face, W/m2 (positive in; scalar or array).
    @param q_bot Net heat flux entering through the bottom face, W/m2 (a face that loses heat has a negative value).
    @return Tuple (d_top, d_bottom) in K, arrays or floats shaped like the fluxes.
    """
    q_top, q_bot = np.asarray(q_top, dtype=float), np.asarray(q_bot, dtype=float)
    return t * (2.0 * q_top - q_bot) / (6.0 * k), t * (2.0 * q_bot - q_top) / (6.0 * k)


def column_bound(t, k, q):
    """!
    @brief The bound q t / (2 k) that the program's thick-plate warning uses (the column fed at the top and cooled at the bottom).
    @param t Layer thickness in m.
    @param k Conductivity in W/mK.
    @param q Flux through the layer in W/m2.
    @return Temperature difference in K.
    """
    return np.abs(q) * t / (2.0 * k)


def bottom_flux(theta_node, h, t, k):
    """!
    @brief Net flux entering through a bottom face that has the film h, from the node temperature (the column mean) in K above the ambient: the film passes the half layer.
    @param theta_node Node temperature above the ambient in K.
    @param h Film coefficient in W/m2K.
    @param t Layer thickness in m.
    @param k Conductivity in W/mK.
    @return Flux in W/m2 (negative: the face loses heat).
    """
    return -np.asarray(theta_node, dtype=float) / (1.0 / h + t / (2.0 * k))
