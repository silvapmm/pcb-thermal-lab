#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gci.py
@brief Grid convergence index of Celik, Ghia, Roache and Freitas (J. Fluids Eng. 130, 2008, 078001), equations 3 to 7, for three grids.
@details Written from the text of the paper (the ASME open copy of the editorial note, pages 4 to 6) and checked against its Table 1 (the three columns).
"""

import math


def gci(phi1, phi2, phi3, r21, r32, fs=1.25):
    """!
    @brief Apparent order, extrapolated value and fine-grid convergence index of three solutions.
    @param phi1 Solution on the finest grid.
    @param phi2 Solution on the medium grid.
    @param phi3 Solution on the coarsest grid.
    @param r21 Refinement ratio h2/h1.
    @param r32 Refinement ratio h3/h2.
    @param fs Safety factor (1.25 for three grids).
    @return Dict with p, phi_ext21, e_a21 (approximate relative error), e_ext21 (extrapolated relative error) and gci_fine21 (all relative errors as fractions).
    """
    e32, e21 = phi3 - phi2, phi2 - phi1
    s = 1.0 if e32 / e21 > 0 else -1.0                           # equation 3c: the sign flags oscillatory convergence
    p = abs(math.log(abs(e32 / e21))) / math.log(r21)            # first term of 3a, the initial guess of the fixed-point iteration
    for _ in range(500):                                         # equations 3a and 3b by fixed-point iteration
        q = math.log((r21 ** p - s) / (r32 ** p - s))
        p_new = abs(math.log(abs(e32 / e21)) + q) / math.log(r21)
        if abs(p_new - p) < 1e-12:
            p = p_new
            break
        p = p_new
    phi_ext = (r21 ** p * phi1 - phi2) / (r21 ** p - 1.0)         # equation 4
    ea = abs((phi1 - phi2) / phi1)                                # equation 5
    eext = abs((phi_ext - phi1) / phi_ext)                        # equation 6
    return {"p": p, "phi_ext21": phi_ext, "e_a21": ea, "e_ext21": eext, "gci_fine21": fs * ea / (r21 ** p - 1.0)}   # equation 7
