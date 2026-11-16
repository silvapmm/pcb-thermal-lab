#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fem_exact.py
@brief Closed forms the finite-element core (`pcbthermal/femcore.py`) is checked against: the 1D series stack with a source in the first slab, the 1D slab with a
       uniform source and Robin ends, and the radial hollow cylinder between two films. Imports nothing of pcbthermal.
@details The series stack is the form of `research/independent-fem-edge/lib/exact.py` (the same derivation, copied so that the test does not depend on the
         research folder). SI units.
"""

import numpy as np


def series_stack(t, k, h_top, h_bottom, q_area):
    """!
    @brief 1D stack with a uniform volumetric source in the first slab and films on both faces (ambient 0).
    @param t Slab thicknesses from the top in m.
    @param k Slab conductivities in W/mK.
    @param h_top Top film in W/m2K.
    @param h_bottom Bottom film in W/m2K.
    @param q_area Heat generated in the first slab per unit area in W/m2.
    @return dict with z (interface depths in m), T (temperature at every interface in K), q_up and q_down (W/m2).
    """
    t, k = np.asarray(t, float), np.asarray(k, float)
    r_below = float((t[1:] / k[1:]).sum())
    g = q_area / t[0]
    # q_u / h_top + (q_u t0 - g t0^2 / 2) / k0 = (q - q_u) (r_below + 1 / h_bottom)
    rb = r_below + 1.0 / h_bottom
    q_u = (q_area * rb + g * t[0] ** 2 / (2 * k[0])) / (1.0 / h_top + t[0] / k[0] + rb)
    q_d = q_area - q_u
    z = np.concatenate([[0.0], np.cumsum(t)])
    T = np.empty(z.size)
    T[0] = q_u / h_top
    T[1] = T[0] + (q_u * t[0] - g * t[0] ** 2 / 2) / k[0]
    for i in range(1, t.size):
        T[i + 1] = T[i] - q_d * t[i] / k[i]
    return {"z": z, "T": T, "q_up": q_u, "q_down": q_d}


def slab_with_source(x, length, k, q, h):
    """!
    @brief Temperature of a slab with a uniform source q and the same film h on both ends (ambient 0), insulated elsewhere.
    @param x Positions measured from the centre in m.
    @param length Slab length in m.
    @param k Conductivity in W/mK.
    @param q Volumetric source in W/m3.
    @param h Film coefficient of both ends in W/m2K.
    @return numpy.ndarray of T in K.
    """
    x = np.asarray(x, float)
    return q / (2.0 * k) * (length ** 2 / 4.0 - x ** 2) + q * length / (2.0 * h)


def hollow_cylinder(r_in, r_out, k, h_in, h_out, t_in, t_out=0.0):
    """!
    @brief Heat per unit length through a hollow cylinder between an inner film at t_in and an outer film at t_out (no source).
    @param r_in Inner radius in m.
    @param r_out Outer radius in m.
    @param k Conductivity in W/mK.
    @param h_in Inner film in W/m2K.
    @param h_out Outer film in W/m2K.
    @param t_in Inner ambient in K.
    @param t_out Outer ambient in K.
    @return Tuple (heat per metre of axial length in W/m, T at the inner wall in K, T at the outer wall in K).
    """
    r_tot = 1.0 / (2 * np.pi * r_in * h_in) + np.log(r_out / r_in) / (2 * np.pi * k) + 1.0 / (2 * np.pi * r_out * h_out)
    q = (t_in - t_out) / r_tot
    return q, t_in - q / (2 * np.pi * r_in * h_in), t_out + q / (2 * np.pi * r_out * h_out)
